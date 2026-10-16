"""Build data/study_notes.csv for the Terraform bot from the flashcard files in sources/online/ (research agent, 2026-10-16):
bradmccoydev/terraform-associate-flashcards (MIT, "# question" headings with the answer below, code blocks kept as labels)
and allister-grange Anki cards (GPL-3.0, one "Question? Answer" line each, cloze {{c1::x}} unwrapped). One note per card,
section = the 003 objective of the file (mapped to the 004 names where they match). Usage: python build_notes.py"""
import csv, glob, math, os, re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ON = HERE / "sources" / "online"
BANK = HERE / "data" / "questions.csv"
OUT = HERE / "data" / "study_notes.csv"
SECTION = {"obj1": "1. IaC with Terraform", "obj2": "1. IaC with Terraform", "obj3": "2. Fundamentals", "obj4": "7. Maintain",
           "obj5": "5. Modules", "obj6": "3. Core workflow", "obj7": "6. State", "obj8": "4. Configuration", "obj9": "8. HCP Terraform"}
STOP = set("the and for with your you are can use using from into that this what how of to in on a an is be or by it its do does which when where".split())
notes, seen = [], set()


def tokens(s):
    return [t for t in re.findall(r"[a-z0-9][a-z0-9_.\-]+", s.lower()) if t not in STOP and len(t) > 1]


def push(section, title, body, labels, source):
    key = re.sub(r"\W+", " ", title.lower()).strip()[:100]
    if key in seen or len(title) < 8 or not (body.strip() or labels):
        return
    seen.add(key)
    notes.append({"section": section, "title": title[:160], "pages": source, "bullets": body.strip()[:2000], "labels": "\n---\n".join(labels)[:2000]})


# bradmccoydev: "# question" / answer prose + ```code``` blocks until the next heading
for f in sorted(ON.glob("github_bradmccoydev_MIT_obj*_*.md")):
    obj = re.search(r"_(obj\d)_", f.name).group(1)
    t = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"^# (.+?)\n(.*?)(?=^# |\Z)", t, re.M | re.S):
        title, body = m.groups()
        labels = [b.strip() for b in re.findall(r"```(?:\w+)?\n(.*?)```", body, re.S) if b.strip()]
        text = re.sub(r"```.*?```", " ", body, flags=re.S)
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"[*`]+", "", text)
        text = "\n".join(l.strip() for l in text.splitlines() if l.strip())
        push(SECTION.get(obj, "4. Configuration"), title.strip(), text, labels, f"bradmccoydev flashcards {obj} (MIT)")

# allister-grange Anki: "Question? Answer" on one line; cloze "{{c1::x}}" -> x; multi-line clozes follow a question line
for f in sorted(ON.glob("github_allister-grange_GPL-3.0_003_obj*-anki-cards.md")):
    obj = re.search(r"_(obj\d)-", f.name).group(1)
    t = f.read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"\{\{c\d+::(.*?)\}\}", r"\1", t)
    lines = [l.strip() for l in t.splitlines()]
    i = 0
    while i < len(lines):
        l = lines[i]
        if not l or l.startswith("#"):
            i += 1; continue
        if "?" in l:
            q, _, a = l.partition("?")
            q = q.strip() + "?"
            a = a.strip()
            j = i + 1
            while not a and j < len(lines) and lines[j] and "?" not in lines[j]:
                a += ("\n" if a else "") + lines[j]; j += 1
            while j < len(lines) and lines[j] and "?" not in lines[j] and not lines[j].startswith("#"):
                a += "\n" + lines[j]; j += 1
            push(SECTION.get(obj, "4. Configuration"), q, a, [], f"allister-grange Anki cards {obj} (GPL-3.0)")
            i = j
        else:
            i += 1

# related bank questions: IDF-weighted overlap of the title (x3) + body tokens with question text
bank = list(csv.DictReader(BANK.open(encoding="utf-8"))) if BANK.exists() else []
qtok = {q["id"]: set(tokens(q["question"] + " " + q["options"])) for q in bank}
df = Counter(t for ts in qtok.values() for t in ts)
idf = lambda t: math.log((len(bank) + 1) / (df.get(t, 0) + 1))
for n in notes:
    tt, bt = set(tokens(n["title"])), set(tokens(n["bullets"]))
    scored = sorted(((sum(idf(t) * (3 if t in tt else 1) for t in (tt | bt) & ts), qid) for qid, ts in qtok.items()), reverse=True)
    n["related"] = ",".join(qid for s, qid in scored[:3] if s >= 5)

OUT.parent.mkdir(exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["id", "section", "title", "pages", "bullets", "labels", "related"])
    w.writeheader()
    for k, n in enumerate(notes, 1):
        w.writerow({"id": f"N-{k:04d}", **n})
print(Counter(n["section"] for n in notes))
print("notes:", len(notes), "with code:", sum(bool(n["labels"]) for n in notes), "with related:", sum(bool(n["related"]) for n in notes), "->", OUT)
