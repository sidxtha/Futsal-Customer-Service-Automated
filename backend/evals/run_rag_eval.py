"""Needs: kb ingested (python -m app.ingest) and rag.sql applied.
Run from the project root:  python -m evals.run_rag_eval
'answer' cases should be answered; 'escalate' cases (not in the KB) must NOT be answered.
READ the printed replies for answer cases: a reply can be 'answered' and still be wrong."""
import json, os, time, warnings, logging
from dotenv import load_dotenv
load_dotenv()
warnings.filterwarnings("ignore")
logging.getLogger("google_genai").setLevel(logging.ERROR)

from supabase import create_client
from app.answerer import answer_from_kb, MIN_SIMILARITY

db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
cases = json.load(open("evals/cases_rag.json", encoding="utf-8"))
print(f"MIN_SIMILARITY = {MIN_SIMILARITY}\n")

ok = 0
bad_answers = 0  # answered when it should have escalated: the dangerous kind
for i, case in enumerate(cases, 1):
    try:
        r = answer_from_kb(db, case["message"], "English")
    except Exception as e:
        print(f"ERR {i:2}. {str(e)[:100]}")
        continue
    got = "answer" if r.answered else "escalate"
    good = got == case["expect"]
    ok += good
    if got == "answer" and case["expect"] == "escalate":
        bad_answers += 1
    top = r.hits[0]["similarity"] if r.hits else None
    print(f"{'OK ' if good else 'XX '}{i:2}. {case['message'][:48]!r}  expect={case['expect']} got={got}  top_sim={top}")
    if r.answered:
        print(f"        reply: {r.reply}")
    elif not good or True:
        print(f"        ({r.reason})")
    time.sleep(0.5)

print(f"\nCorrect: {ok}/{len(cases)}   Wrongly answered (should have escalated): {bad_answers}")