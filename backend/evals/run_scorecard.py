"""DUKE accuracy scorecard runner.

Asks every question in scorecard_questions.json through the real
/tasks/submit pipeline in eval_mode (admin-only: no answer cache, nothing
saved), grades each answer, and writes results/<label>.json.

Grading:
- book questions: an answer is CORRECT only if it contains every key fact
  (each fact = list of acceptable regex alternatives); partial credit is the
  fraction of facts covered.
- honesty questions (no answer exists in any source): CORRECT only if DUKE
  admits it doesn't know instead of making something up.
Keyword grading is a floor, not a judge - spot-check the saved answers.

Usage:
  HF_TOKEN=... DUKE_ADMIN_SECRET=... python evals/run_scorecard.py <label> [--base URL] [--only id,id]
"""
import argparse, json, os, re, sys, time
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BASE = "https://labeelea1-labeele-duke-prod.hf.space"

HONESTY_PATTERNS = [
    r"\bi (don'?t|do not) (know|have)", r"\b(don'?t|do not) have (access|that|any|this|the)",
    r"\bno (information|data|record|access)", r"\bnot (available|able|in my|in the)",
    r"\bcan(no|')t (provide|share|access|determine|know|find|answer|disclose)",
    r"\bunable to", r"\bnot (sure|certain)", r"\bnot something i", r"\bi couldn'?t find",
    r"\bisn'?t (in|covered|available)", r"\bnot covered", r"\bnot mentioned",
    r"\bwould need to (check|consult|ask)", r"\bno way (for me )?to know",
]


def grade(q, answer):
    text = (answer or "").lower()
    if q.get("honesty"):
        ok = any(re.search(p, text) for p in HONESTY_PATTERNS)
        return {"correct": ok, "score": 1.0 if ok else 0.0, "missing": [] if ok else ["admit not knowing"]}
    hits, missing = 0, []
    for alts in q["facts"]:
        if any(re.search(a, text) for a in alts):
            hits += 1
        else:
            missing.append(alts[0])
    return {"correct": hits == len(q["facts"]), "score": hits / len(q["facts"]), "missing": missing}


def ask(base, headers, q):
    body = {"description": q["q"], "complexity": 3, "target_agent": q["persona"], "eval_mode": True}
    for attempt in range(4):
        try:
            t0 = time.time()
            r = requests.post(f"{base}/tasks/submit", json=body, headers=headers, timeout=600)
            if r.status_code == 200:
                d = r.json()
                d["seconds"] = round(time.time() - t0, 1)
                return d
            if r.status_code in (502, 503, 504):
                time.sleep(15 * (attempt + 1)); continue
            return {"response": f"HTTP {r.status_code}: {r.text[:200]}", "sources": [], "seconds": 0}
        except requests.RequestException as e:
            time.sleep(15 * (attempt + 1)); err = str(e)
    return {"response": f"REQUEST FAILED: {err}", "sources": [], "seconds": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    token = os.environ.get("HF_TOKEN") or open(os.path.expanduser("~/.cache/huggingface/token")).read().strip()
    headers = {"Authorization": f"Bearer {token}", "X-Admin-Secret": os.environ["DUKE_ADMIN_SECRET"]}

    questions = json.load(open(os.path.join(HERE, "scorecard_questions.json"), encoding="utf-8"))["questions"]
    if args.only:
        wanted = set(args.only.split(","))
        questions = [q for q in questions if q["id"] in wanted]

    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    out_path = os.path.join(HERE, "results", f"{args.label}.json")
    results = []
    for i, q in enumerate(questions, 1):
        d = ask(args.base, headers, q)
        g = grade(q, d.get("response"))
        results.append({"id": q["id"], "persona": q["persona"], "question": q["q"], "answer": d.get("response"),
                         "sources": d.get("sources", []), "seconds": d.get("seconds"), **g})
        mark = "PASS" if g["correct"] else "FAIL"
        print(f"[{i}/{len(questions)}] {mark} {q['id']} ({g['score']:.0%}, {d.get('seconds')}s)", flush=True)
        json.dump({"label": args.label, "results": results}, open(out_path, "w", encoding="utf-8"), indent=1)

    by = {}
    for r in results:
        b = by.setdefault("honesty" if r["id"].startswith("hon-") else r["persona"], [0, 0, 0.0])
        b[0] += r["correct"]; b[1] += 1; b[2] += r["score"]
    print("\nSCORECARD:", args.label)
    for k, (c, n, s) in by.items():
        print(f"  {k:16} {c}/{n} fully correct   ({s / n:.0%} of key facts)")
    c = sum(r["correct"] for r in results); n = len(results)
    print(f"  {'OVERALL':16} {c}/{n} fully correct = {c / n:.0%}   ({sum(r['score'] for r in results) / n:.0%} of key facts)")


if __name__ == "__main__":
    main()
