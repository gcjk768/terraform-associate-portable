"""Build the Terraform Associate (004) question bank from files downloaded into sources/online/ (research agent, 2026-10-16)
plus authored banks in banks/*.md. Usage: python -I build_csv.py  ->  data/questions.csv (bot schema).
Sources: HashiCorp official samples (6), PatrickWiloak scenarios (25, CC BY 4.0), sailor.sh (25), Whizlabs blog (50),
examcert.app blog (12, answer inferred from the explanation), certland.net sample (5). Objective guessed by keywords."""
import csv, glob, html, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ON = os.path.join(HERE, "sources", "online")
OUT = os.path.join(HERE, "data", "questions.csv")
LET = "ABCDEFGH"
rows, seen = [], set()
OBJ = [("1. IaC with Terraform", r"infrastructure as code|iac|idempot|declarative|multi-cloud|agnostic|version control"),
       ("2. Fundamentals", r"provider|plugin|registry|lock file|required_providers|terraform block|version constraint"),
       ("3. Core workflow", r"terraform init|terraform plan|terraform apply|terraform destroy|terraform fmt|terraform validate|core workflow|-out|-auto-approve"),
       ("4. Configuration", r"variable|output|local|data source|data \"|function|type|map|list|object|count|for_each|depends_on|lifecycle|precondition|validation|sensitive|provisioner|dynamic"),
       ("5. Modules", r"module"),
       ("6. State", r"state|backend|workspace|lock|drift|refresh"),
       ("7. Maintain", r"import|terraform state|tf_log|taint|replace|debug|logging"),
       ("8. HCP Terraform", r"hcp terraform|terraform cloud|sentinel|opa|policy|run task|remote run|organization|vcs|team|agent")]


def objective(text):
    t = text.lower(); best, score = "4. Configuration", 0
    for name, pat in OBJ:
        n = len(re.findall(pat, t))
        if n > score:
            best, score = name, n
    return best


def clean(s):
    return re.sub(r"[ \t]+", " ", html.unescape(s.replace("**", "").replace("_", "_"))).strip()


def add(question, opts, answer, expl, source, domain=None):
    key = re.sub(r"\W+", " ", question[:120].lower()).strip()
    answer = answer.replace(" ", "")
    if key in seen or len(question) < 15 or not answer or not all(opts.get(L) for L in answer.split(",")):
        return
    seen.add(key)
    rows.append({"id": f"TF-{len(rows) + 1:04d}", "domain": domain or objective(question + " " + " ".join(opts.values())),
                 "question": question.strip(), "options": "\n".join(f"{L}. {opts[L]}" for L in LET if opts.get(L)),
                 "correct": answer, "explanation": f"{expl.strip() or '(no explanation in source)'}\n(source: {source})"})


# 1. HashiCorp official samples (Jina): "**stem**" / "⬜ option" lines / "✅ Correct: text" (one or several lines)
f = os.path.join(ON, "hashicorp_official_sample-questions-004_jina.md")
if os.path.exists(f):
    t = open(f, encoding="utf-8").read()
    for m in re.finditer(r"^\*\*(.+?)\*\*\n\n((?:⬜.*\n?)+)\n?((?:✅.*\n?)+)", t, re.M):
        stem, optblock, corr = m.groups()
        opts = {LET[k]: clean(x) for k, x in enumerate(re.findall(r"⬜\s*(.*)", optblock))}
        correct_texts = [clean(x) for x in re.findall(r"✅ Correct:\s*(.*)", corr)]
        ans = ",".join(L for L, x in opts.items() if any(x == c or (c and c in x) for c in correct_texts))
        if opts and ans and "intended to trick" not in stem:
            add(clean(stem), opts, ans, "Official HashiCorp sample question; the answer is given without an explanation.", "HashiCorp official sample questions (004)")

# 2. PatrickWiloak (CC BY 4.0): "### Question N" / "**Scenario:** ..." / "A. ..." / <details> "**Correct: C**" "**Why:** ..."
f = os.path.join(ON, "github_PatrickWiloak_CC-BY-4.0_terraform-associate-003_25-scenario-questions.md")
if os.path.exists(f):
    t = open(f, encoding="utf-8").read()
    for m in re.finditer(r"^### Question (\d+)\n(.*?)(?=^### Question \d+|\Z)", t, re.M | re.S):
        body = m.group(2)
        qpart, _, apart = body.partition("<details>")
        opts = {L: clean(x) for L, x in re.findall(r"^([A-H])\. (.*)$", qpart, re.M)}
        am = re.search(r"\*\*Correct: ([A-H](?:,\s*[A-H])*)\*\*", apart)
        why = re.search(r"\*\*Why:\*\* (.*?)(?=\n\*\*Key Concept|\n</details>|\Z)", apart, re.S)
        stem = qpart.split("\nA. ", 1)[0].replace("**Scenario:**", "").strip()
        if opts and am:
            add(clean(stem), opts, am.group(1), clean(why.group(1)) if why else "", "PatrickWiloak scenario questions (GitHub, CC BY 4.0)")

# 3. sailor.sh (Jina): "### Qn" / stem / options on one line "A. x B. y C. z" / "**Answer: A, B.** explanation"
f = os.path.join(ON, "sailor-sh_blog_25-realistic-003-questions_jina.md")
if os.path.exists(f):
    t = open(f, encoding="utf-8").read()
    for m in re.finditer(r"^### Q(\d+)\n\n(.*?)\n\n(.*?)\n\n\*\*Answer:\s*([A-H](?:,\s*[A-H])*)\.?\*\*\s*(.*?)(?=\n\n### Q|\Z)", t, re.M | re.S):
        n, stem, optline, ans, expl = m.groups()
        parts = re.split(r"(?:^|\s)([A-H])\.\s", " " + optline)
        opts = {parts[i]: clean(parts[i + 1]) for i in range(1, len(parts) - 1, 2)}
        if "true or false" in stem.lower() and not opts:
            opts = {"A": "True", "B": "False"}
        if opts:
            add(clean(stem), opts, ans, clean(expl), "sailor.sh Terraform Associate practice questions")

# 4. Whizlabs blog (Jina): "Q n. stem_**" / "A. x" lines (with trailing spaces) / "**Option B is correct**" or "**Option B:**" + explanation
f = os.path.join(ON, "whizlabs_blog_50-sample-questions_jina.md")
if os.path.exists(f):
    t = open(f, encoding="utf-8").read()
    blocks = re.split(r"(?:^#### )?\*{0,2}_?\*?Q ?(\d+)\.\s*", t, flags=re.M)[1:]
    for i in range(0, len(blocks) - 1, 2):
        body = blocks[i + 1]
        stem = re.sub(r"[_*]+", "", body.split("\n\nA.", 1)[0]).strip()
        optblock = body.split("\n\n", 1)[1] if "\n\n" in body else ""
        opts = {L: clean(x) for L, x in re.findall(r"^\s*([A-E])\.\s*(.*?)\s*$", optblock.split("**Option", 1)[0], re.M)}
        am = re.search(r"\*\*Option:?\s*([A-E])(?:\s*(?:,|and)\s*([A-E]))?[^*]*\*\*", body)
        expl = re.split(r"\*\*Option[^*]*\*\*", body, maxsplit=1)[-1] if am else ""
        if opts and am:
            ans = ",".join(x for x in am.groups() if x)
            add(clean(stem), opts, ans, clean(re.sub(r"\n\s*", " ", expl))[:1200], "Whizlabs blog sample questions")

# 5. examcert.app blog (Jina): "### Question N" / stem / "A. ..." lines (blank-separated) / explanation paragraph naming the answer in prose
f = os.path.join(ON, "examcert_blog_12-questions_jina.md")
if os.path.exists(f):
    t = open(f, encoding="utf-8").read()
    for m in re.finditer(r"^### Question (\d+)\n\n(.*?)\n\n((?:[A-D]\..*\n\n?)+)(.*?)(?=\n### Question|\Z)", t, re.M | re.S):
        n, stem, optblock, expl = m.groups()
        opts = {L: clean(x) for L, x in re.findall(r"^([A-D])\.\s*(.*)$", optblock, re.M)}
        el = clean(expl).lower()
        score = {L: sum(1 for w in set(re.findall(r"[a-z0-9_.\-]{5,}", x.lower())) if w in el) for L, x in opts.items()}
        best = max(score, key=score.get) if score else ""
        if opts and best and score[best]:
            add(clean(stem), opts, best, clean(expl), "examcert.app blog (answer inferred from the explanation)")

# 6. certland.net sample (Jina): "N. stem" / "A  text" lines, the correct one ends with "✓ Correct"
f = os.path.join(ON, "certland_004_5-sample-questions_jina.md")
if os.path.exists(f):
    t = open(f, encoding="utf-8").read()
    for m in re.finditer(r"^(\d+)\. (.+?)\n\n((?:[A-E]\s{2,}.*\n\n?)+)", t, re.M):
        stem, optblock = m.group(2), m.group(3)
        opts, ans = {}, []
        for L, x in re.findall(r"^([A-E])\s{2,}(.*)$", optblock, re.M):
            if "✓" in x:
                ans.append(L)
            opts[L] = clean(x.replace("✓ Correct", ""))
        if opts and ans:
            add(clean(stem), opts, ",".join(ans), "", "certland.net free sample")

# 6b. MCQs written by Claude from the flashcards (build_mcq.py): one JSON object per line, domain = the card's objective
import json
f = os.path.join(HERE, "sources", "mcq", "generated.jsonl")
if os.path.exists(f):
    for line in open(f, encoding="utf-8"):
        try:
            q = json.loads(line)
        except Exception:
            continue
        opts = {L: (q.get("options") or {}).get(L, "") for L in "ABCD"}
        if all(opts.values()) and q.get("correct") in list("ABCD") and q.get("question"):
            add(q["question"], opts, q["correct"], q.get("explanation", ""), "MCQ written by Claude from a flashcard", q.get("domain"))

# 7. Authored banks (AGENT format)
for f in sorted(glob.glob(os.path.join(HERE, "banks", "*.md"))):
    t = open(f, encoding="utf-8").read()
    hdr = dict(re.findall(r"^(source|url|version): (.*)$", t.split("\n## ", 1)[0], flags=re.M))
    qpart, apart = t.split("## Answers")
    key = {n: (x, why) for n, x, why in re.findall(r"^\| (\d+) \| ([A-F](?:,[A-F])*) \| (.*?) \|$", apart, flags=re.M)}
    for chunk in re.split(r"^(## .*)$", qpart, flags=re.M)[1:]:
        if chunk.startswith("## "):
            continue
        qs = re.split(r"^(\d+)\. ", chunk, flags=re.M)[1:]
        for k in range(0, len(qs), 2):
            n, body = qs[k], qs[k + 1]
            parts = re.split(r"^\s+([A-F])\. ", body, flags=re.M)
            opts = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
            if n in key:
                add(parts[0].strip(), opts, key[n][0], key[n][1], hdr.get("source", os.path.basename(f)))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["id", "domain", "question", "options", "correct", "explanation"])
    w.writeheader(); w.writerows(rows)
from collections import Counter
print(Counter(r["domain"] for r in rows))
print(Counter(r["explanation"].rsplit("(source: ", 1)[-1].rstrip(")") for r in rows))
print("rows:", len(rows), "multi:", sum("," in r["correct"] for r in rows), "->", OUT)
