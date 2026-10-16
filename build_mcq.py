"""Write one exam-style multiple-choice question per flashcard (data/study_notes.csv) with Claude Code (claude -p), so the
Terraform bank is big enough to drill. Resumable: cards already in sources/mcq/generated.jsonl are skipped.
Usage: python build_mcq.py [--model haiku] [--workers 2] [--limit N]. build_csv.py reads the jsonl."""
import csv, hashlib, json, os, shutil, subprocess, sys, tempfile, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "sources" / "mcq" / "generated.jsonl"
MODEL = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else os.environ.get("CLAUDE_MODEL", "haiku")
WORKERS = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 2
LIMIT = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 10_000
SYSTEM = """You write multiple-choice practice questions for the HashiCorp Terraform Associate (004) exam, Terraform 1.12.
Given one study flashcard (a question and its answer, sometimes with HCL or CLI examples), write ONE exam-style question
that tests the same fact in a realistic scenario (a team, a configuration, a command output). Exactly four options A to D:
one correct, three plausible wrong ones (wrong command, wrong block, wrong precedence, a tempting myth). The explanation
(under 110 words, plain text) says why the correct option is right, what each wrong option gets wrong, and quotes the exact
HCL or command to remember. Prefer 004 terminology (HCP Terraform, not Terraform Cloud). Return JSON only."""
SCHEMA = json.dumps({"type": "object", "required": ["question", "options", "correct", "explanation"], "additionalProperties": False,
                     "properties": {"question": {"type": "string"},
                                    "options": {"type": "object", "required": ["A", "B", "C", "D"], "additionalProperties": False,
                                                "properties": {k: {"type": "string"} for k in "ABCD"}},
                                    "correct": {"type": "string", "enum": list("ABCD")}, "explanation": {"type": "string"}}})


def key_of(text):
    return hashlib.md5(text[:300].encode()).hexdigest()[:12]


def ask(card):
    exe = shutil.which("claude")
    work = Path(tempfile.gettempdir()) / "tf-mcq-work"; work.mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "TELEGRAM_BOT_TOKEN"}; env["DISABLE_AUTOUPDATER"] = "1"
    cmd = [exe, "-p", "--output-format", "json", "--no-session-persistence", "--permission-mode", "dontAsk", "--model", MODEL,
           "--tools", "", "--max-turns", "4", "--append-system-prompt", SYSTEM, "--json-schema", SCHEMA]
    prompt = ("You are NOT asked to answer the flashcard. Your only job is to WRITE A QUIZ QUESTION from it.\n\n"
              f"FLASHCARD QUESTION: {card['title']}\nSECTION: {card['section']}\nFLASHCARD ANSWER:\n{card['bullets']}\n"
              + (f"EXAMPLES:\n{card['labels']}\n" if card["labels"] else "") +
              '\nReply with ONLY this JSON object: {"question": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."}, "correct": "A|B|C|D", "explanation": "..."}')
    p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=work, env=env, timeout=240)
    if p.returncode:
        raise RuntimeError(p.stderr[:200])
    data = json.loads(p.stdout)
    out = data.get("structured_output")
    if not isinstance(out, dict) or "options" not in out:
        text = str(data.get("result") or ""); out = json.loads(text[text.find("{"):text.rfind("}") + 1])
    opts = out.get("options") or {}
    if not (isinstance(opts, dict) and all(opts.get(k) for k in "ABCD") and out.get("correct") in list("ABCD") and out.get("question")):
        raise RuntimeError("invalid quiz JSON: " + json.dumps(out)[:120])
    return out, data.get("total_cost_usd")


cards = list(csv.DictReader(open(HERE / "data" / "study_notes.csv", encoding="utf-8")))
OUT.parent.mkdir(parents=True, exist_ok=True)
done = set()
if OUT.exists():
    for line in open(OUT, encoding="utf-8"):
        try:
            done.add(json.loads(line)["key"])
        except Exception:
            pass
todo = [c for c in cards if key_of(c["title"] + c["bullets"]) not in done][:LIMIT]
print(f"{len(cards)} cards, {len(done)} done, {len(todo)} to write with {MODEL} x{WORKERS}")
lock = threading.Lock(); cost = [0.0]; n = [0]


def worker(chunk):
    for c in chunk:
        try:
            out, cst = ask(c)
            rec = {"key": key_of(c["title"] + c["bullets"]), "note_id": c["id"], "domain": c["section"], **out}
            with lock:
                with OUT.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                cost[0] += cst or 0; n[0] += 1
                print(f"[{n[0]}/{len(todo)}] {c['id']} ${cost[0]:.2f}", flush=True)
        except Exception as exc:
            print("FAILED", c["id"], str(exc)[:120], flush=True)
            time.sleep(5)


threads = [threading.Thread(target=worker, args=(todo[i::WORKERS],)) for i in range(WORKERS)]
[t.start() for t in threads]; [t.join() for t in threads]
print(f"done: {n[0]} written, total ${cost[0]:.2f} -> {OUT}")
