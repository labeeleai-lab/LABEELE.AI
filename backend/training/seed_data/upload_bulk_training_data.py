"""
training/seed_data/upload_bulk_training_data.py

One-time (or repeatable) bulk-loader for bulk_training_examples.json - posts
a curated batch of expert-level instruction/output pairs to DUKE's training
data table via the site's own admin API, then optionally triggers a real
training run.

Usage:
    python upload_bulk_training_data.py --email you@example.com --password '...'
    python upload_bulk_training_data.py --email you@example.com --password '...' --retrain

Talks to the live site (SITE_URL below) through the same admin-proxied path
the JIREH Mode UI itself uses - logs in for a session cookie, then calls
/api/admin/duke/admin/training-data/upload (and optionally
/api/admin/duke/admin/retrain-agents) through that authenticated session.
Requires the account to already be an admin.
"""
import argparse
import json
import sys
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
    print(f"Logged in as {user['email']} (admin confirmed)")


def upload_examples(session: requests.Session, examples: list) -> dict:
    res = session.post(
        f"{SITE_URL}/api/admin/duke/admin/training-data/upload",
        json={"examples": examples},
        timeout=60,
    )
    if not res.ok:
        print(f"Upload failed ({res.status_code}): {res.text}", file=sys.stderr)
        sys.exit(1)
    return res.json()


def trigger_retrain(session: requests.Session) -> dict:
    res = session.post(
        f"{SITE_URL}/api/admin/duke/admin/retrain-agents",
        timeout=120,
    )
    if not res.ok:
        print(f"Retrain failed ({res.status_code}): {res.text}", file=sys.stderr)
        sys.exit(1)
    return res.json()


def main():
    parser = argparse.ArgumentParser(description="Bulk-upload DUKE training examples")
    parser.add_argument("--email", required=True, help="An admin account's email")
    parser.add_argument("--password", required=True, help="That account's password")
    parser.add_argument("--retrain", action="store_true", help="Trigger a training run after uploading")
    args = parser.parse_args()

    examples = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    print(f"Loaded {len(examples)} training examples from {DATA_FILE.name}")

    session = requests.Session()
    login(session, args.email, args.password)

    result = upload_examples(session, examples)
    print("\nUpload result:")
    print(json.dumps(result, indent=2))

    if args.retrain:
        print("\nTriggering training run...")
        train_result = trigger_retrain(session)
        print("\nTraining result:")
        print(json.dumps(train_result, indent=2))


if __name__ == "__main__":
    main()
