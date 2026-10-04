"""Run from the project root:
    python -m evals.run_eval                      # evals/cases.json
    python -m evals.run_eval evals/cases_new.json # any other case file

Each case needs: message, category, priority.
Optional: requires_human (bool) and extracted ({field: expected_value}).
"""
import json, sys, time, warnings, logging
from dotenv import load_dotenv
load_dotenv()
warnings.filterwarnings("ignore")
logging.getLogger("google_genai").setLevel(logging.ERROR)

from app.classifier import classify
from app.rules import apply_rules

path = sys.argv[1] if len(sys.argv) > 1 else "evals/cases.json"
cases = json.load(open(path, encoding="utf-8"))
print(f"Running {len(cases)} cases from {path}\n")

cat_ok = pri_ok = failed = 0
hum_ok = hum_n = ext_ok = ext_n = 0

for i, case in enumerate(cases, 1):
    try:
        result, _ = apply_rules(classify(case["message"]), case["message"])
    except Exception as e:
        failed += 1
        print(f"ERR {i:2}. {str(e)[:100]}")
        continue

    c = result.category == case["category"]
    p = result.priority == case["priority"]
    cat_ok += c
    pri_ok += p
    problems = []
    if not c: problems.append(f"category {result.category} (want {case['category']})")
    if not p: problems.append(f"priority {result.priority} (want {case['priority']})")

    if "requires_human" in case:
        hum_n += 1
        h = result.requires_human == case["requires_human"]
        hum_ok += h
        if not h: problems.append(f"human={result.requires_human} (want {case['requires_human']})")

    for field, want in case.get("extracted", {}).items():
        ext_n += 1
        got = getattr(result.extracted, field)
        if got == want:
            ext_ok += 1
        else:
            problems.append(f"extracted.{field}={got!r} (want {want!r})")

    flag = "OK " if not problems else "XX "
    print(f"{flag}{i:2}. {case['message'][:50]!r}")
    for pr in problems:
        print(f"        - {pr}")
    time.sleep(0.5)

n = len(cases) - failed
print(f"\nCategory: {cat_ok}/{n}   Priority: {pri_ok}/{n}", end="")
if hum_n: print(f"   requires_human: {hum_ok}/{hum_n}", end="")
if ext_n: print(f"   extraction: {ext_ok}/{ext_n}", end="")
print(f"   API errors: {failed}")