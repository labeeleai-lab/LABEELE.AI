"""
training/seed_data/upload_bulk_knowledge.py

Uploads bulk_training_examples.json into DUKE's actual Knowledge system
(pgvector-backed retrieval that real answers are generated from), one
knowledge source per Q&A pair so each answer stays intact as its own
retrieval unit instead of being arbitrarily chunked mid-thought.

"duke"-tagged examples (cross-domain synthesis questions) are uploaded as
DUKE-global knowledge (persona_id=None) rather than tagged to a specific
specialist, since that's what the retrieval system treats as globally
available across every persona and to DUKE's own cross-agent mode.

Usage:
    python upload_bulk_knowledge.py --email you@example.com --password '...'
"""
import argparse
import json
import sys
import time
from pathlib import Path

import requests

SITE_URL = "https://www.labeele.ai"
DATA_FILE = Path(__file__).parent / "bulk_training_examples.json"


def login(session: requests.Session, email: str, password: str) -> None:
    res = session.post(
        f"{SITE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    if not res.ok:
        print(f"Login failed ({res.status_code}): {res.text}", file=sys.stderr)
        sys.exit(1)
    user = res.json().get("user", {})
    if not user.get("is_admin"):
        print(f"Logged in as {user.get('email')}, but that account is not an admin.", file=sys.stderr)
        sys.exit(1)
    print(f"Logged in as {user['email']} (admin confirmed)\n")


def upload_one(session: requests.Session, persona_id, source_name: str, text: str) -> dict:
    res = session.post(
        f"{SITE_URL}/api/admin/duke/admin/knowledge/upload",
        json={
            "persona_id": persona_id,
            "source_name": source_name,
            "content_type": "text",
            "text": text,
        },
        timeout=60,
    )
    if not res.ok:
        return {"error": f"{res.status_code}: {res.text}"}
    return res.json()


def main():
    parser = argparse.ArgumentParser(description="Bulk-upload DUKE knowledge entries")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    examples = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    print(f"Loaded {len(examples)} Q&A pairs from {DATA_FILE.name}\n")

    session = requests.Session()
    login(session, args.email, args.password)

    counts = {}
    failures = []
    total_chunks = 0
    per_persona_index = {}

    for entry in examples:
        raw_persona = entry["persona_id"]
        # "duke" examples are cross-domain synthesis - file them as DUKE-global
        # knowledge (available to every persona + DUKE's own cross-agent mode)
        # rather than under a persona_id nothing else actually queries by.
        persona_id = None if raw_persona == "duke" else raw_persona
        label = "global (duke)" if persona_id is None else persona_id

        idx = per_persona_index.get(label, 0) + 1
        per_persona_index[label] = idx
        source_name = f"seed-{label}-{idx:02d}"

        text = f"Question: {entry['instruction']}\n\nAnswer: {entry['output']}"

        result = upload_one(session, persona_id, source_name, text)
        if "error" in result:
            print(f"  FAILED  [{label}] {source_name}: {result['error']}")
            failures.append((source_name, result["error"]))
        else:
            chunks = result.get("chunks_created", 0)
            total_chunks += chunks
            counts[label] = counts.get(label, 0) + 1
            print(f"  ok      [{label}] {source_name} -> {chunks} chunk(s)")

        time.sleep(0.3)  # be gentle on the single-CPU backend

    print("\n--- Summary ---")
    for label, n in counts.items():
        print(f"  {label}: {n} sources uploaded")
    print(f"Total knowledge sources uploaded: {sum(counts.values())} / {len(examples)}")
    print(f"Total chunks created: {total_chunks}")
    if failures:
        print(f"\n{len(failures)} failures:")
        for name, err in failures:
            print(f"  - {name}: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
