"""Smallest check that fails if the quiz logic breaks: python test_bot.py"""
import os, tempfile
os.environ["DATA_DIR"] = os.environ.get("DATA_DIR", "data")
import bot

assert len(bot.QUESTIONS) >= 40
q = next(q for q in bot.QUESTIONS.values() if len(q["answer"]) > 1)   # a Select TWO question
assert all(q["answer"] <= set(q["letters"]) for q in bot.QUESTIONS.values())
assert all(len(bot.question_text(q)) < 4096 for q in bot.QUESTIONS.values())
kb = bot.keyboard(q, {"D"})
assert kb.inline_keyboard[3][0].text.startswith("☑ D · ") and kb.inline_keyboard[5][0].text == "✅ Submit"
single = next(q for q in bot.QUESTIONS.values() if len(q["answer"]) == 1)
assert len(bot.keyboard(single).inline_keyboard) == len(single["letters"])  # single answer: no Submit row

state = {"ok": {}, "bad": {}}
seen = {bot.pick_question(state)["id"] for _ in range(50)}
assert len(seen) > 10
state["ok"] = {i: 1 for i in bot.QUESTIONS}
state["bad"] = {"TF-0010": 2}
assert bot.pick_question(state)["id"] == "TF-0010"          # wrong ones come back first
assert "PROGRESS" in bot.stats_text(state)
bot.STATE_PATH = bot.Path(tempfile.mkdtemp()) / "state.json"
bot.save_state(state); assert bot.load_state() == state

# diagrams renderer: official AWS icons, and the import guard
src = '''from diagrams import Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.integration import SQS
with Diagram("t", filename="out", show=False, direction="LR"):
    Lambda("fn") >> Edge(label="x") >> SQS("queue")
'''
assert bot.diagrams_png(src).startswith(b"\x89PNG")
try:
    bot.diagrams_png("import os\n" + src)
    raise AssertionError("os import must be refused")
except ValueError:
    pass
print("ok")

# auto-quiz window
from datetime import datetime
assert bot.quiz_due(datetime(2026, 1, 1, 9, 0), {}) and bot.quiz_due(datetime(2026, 1, 1, 22, 59), {})
assert not bot.quiz_due(datetime(2026, 1, 1, 8, 59), {}) and not bot.quiz_due(datetime(2026, 1, 1, 23, 0), {})
assert not bot.quiz_due(datetime(2026, 1, 1, 12, 0), {"pending": "TF-0001"})
print("ok schedule")

# study cards: notes load, no repeats until all are studied, related ids exist in the bank
if bot.NOTES:
    assert len(bot.NOTES) > 300 and all(n["title"] for n in bot.NOTES.values())
    st_ = {"studied": [i for i in bot.NOTES if i != "N-0170"]}
    assert bot.pick_note(st_)["id"] == "N-0170"
    assert bot.pick_note({"studied": list(bot.NOTES)})["id"] in bot.NOTES      # wraps around
    print("ok study")

# weekly report metrics: 3 first-try answers this week, 2 right; equal-weight score; verdicts
from datetime import datetime as _dt
now = _dt(2026, 10, 18, 22, 0)
ids = ["TF-0001", "TF-0006", "TF-0010"]
st = {"ok": {}, "bad": {}, "log": [{"t": "2026-10-17T10:00", "id": ids[0], "ok": True, "first": True},
                                   {"t": "2026-10-17T11:00", "id": ids[1], "ok": True, "first": True},
                                   {"t": "2026-10-18T09:00", "id": ids[2], "ok": False, "first": True},
                                   {"t": "2026-09-01T09:00", "id": ids[2], "ok": True, "first": False}]}
m = bot.metrics(st, now)
assert m["week_n"] == 3 and m["week_ok"] == 2 and m["first_n"] == 3 and m["first_ok"] == 2
assert 0 <= m["score"] <= 1000 and bot.verdict(m).startswith("⚪")
txt = bot.report_text(m, now)
assert "WEEKLY REPORT" in txt and "Predicted score" in txt and "READINESS" in txt and "750" in txt
many = [i for k, i in enumerate(bot.QUESTIONS) if k % 3]   # two of every three ids: spans all banks, >= 60 answers
big = {**st, "log": [{"t": "2026-10-18T09:00", "id": i, "ok": True, "first": True} for i in many]}
big["ok"] = {i: 1 for i in many}
assert bot.verdict(bot.metrics(big, now)).startswith("🟢")
print("ok report")
