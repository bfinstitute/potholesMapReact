"""
clear_bad_cache.py
------------------
Clears stale / wrong cached responses from both MongoDB and DiskCache.

Usage:
  # Wipe ALL caches (full reset):
  python clear_bad_cache.py --all

  # Only remove entries whose cached answer contains known bad phrases:
  python clear_bad_cache.py --bad-only

  # Preview what would be deleted without deleting (dry-run):
  python clear_bad_cache.py --bad-only --dry-run
"""

import sys
import os
import argparse

# Make sure app imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "app", ".env"))

# Phrases that indicate a stale / insufficient-data answer that should be purged
BAD_PHRASES = [
    "i do not have specific data",
    "i don't have specific data",
    "not available in the information provide",
    "no specific data for zip 78207",
    "synthesis http error",
    "synthesis request error",
    "synthesis error:",
    "i don't have that specific data",
    "unable to connect to the gemini",
    "unable to connect to the groq",
]


def matches_bad(text: str) -> bool:
    t = (text or "").lower()
    return any(p in t for p in BAD_PHRASES)


def clear_mongo(bad_only: bool, dry_run: bool):
    try:
        from mongodb_client import get_mongo_client
        client = get_mongo_client()
        if not client.enabled:
            print("[MongoDB] Not connected / not configured — skipping MongoDB cleanup.")
            return

        db = client._db

        if bad_only:
            # Scan response_cache for bad answers
            total = db.response_cache.count_documents({})
            bad_ids = []
            for doc in db.response_cache.find({}, {"_id": 1, "response": 1, "question": 1}):
                if matches_bad(doc.get("response", "")):
                    bad_ids.append(doc["_id"])
                    if dry_run:
                        print(f"  [DRY-RUN] Would delete: {doc.get('question', '')[:80]!r}")

            print(f"[MongoDB] response_cache: {total} total, {len(bad_ids)} bad entries found.")
            if not dry_run and bad_ids:
                result = db.response_cache.delete_many({"_id": {"$in": bad_ids}})
                print(f"[MongoDB] Deleted {result.deleted_count} bad response_cache entries.")

            # Also clear bad groq_responses monitoring entries
            bad_groq_ids = []
            for doc in db.groq_responses.find({}, {"_id": 1, "groq_response": 1, "question": 1}):
                if matches_bad(doc.get("groq_response", "")):
                    bad_groq_ids.append(doc["_id"])
            if not dry_run and bad_groq_ids:
                result = db.groq_responses.delete_many({"_id": {"$in": bad_groq_ids}})
                print(f"[MongoDB] Deleted {result.deleted_count} bad groq_responses entries.")
        else:
            # Full wipe
            if dry_run:
                rc = db.response_cache.count_documents({})
                gr = db.groq_responses.count_documents({})
                print(f"[DRY-RUN] Would delete ALL {rc} response_cache + {gr} groq_responses entries.")
            else:
                rc = db.response_cache.delete_many({})
                gr = db.groq_responses.delete_many({})
                print(f"[MongoDB] Cleared: {rc.deleted_count} response_cache, {gr.deleted_count} groq_responses.")

    except Exception as e:
        print(f"[MongoDB] Error: {e}")


def clear_disk(bad_only: bool, dry_run: bool):
    try:
        from disk_cache import reset_cache, cache_stats, _get_cache  # type: ignore

        stats = cache_stats()
        print(f"[DiskCache] {stats.get('entry_count', 0)} entries found.")

        if bad_only:
            dc = _get_cache()
            deleted = 0
            for key in list(dc.iterkeys()):
                val = dc.get(key)
                if isinstance(val, dict):
                    answer = val.get("response", "") or ""
                    structured = val.get("structured") or {}
                    if isinstance(structured, dict):
                        answer = answer or structured.get("answer", "")
                    if matches_bad(answer):
                        if dry_run:
                            print(f"  [DRY-RUN] Would delete disk key: {str(key)[:80]!r}")
                        else:
                            dc.delete(key)
                            deleted += 1
            if not dry_run:
                print(f"[DiskCache] Deleted {deleted} bad entries.")
        else:
            if dry_run:
                print("[DRY-RUN] Would wipe entire disk cache.")
            else:
                result = reset_cache()
                print(f"[DiskCache] {result}")
    except Exception as e:
        print(f"[DiskCache] Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Clear bad or all cached chatbot responses.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Wipe ALL caches entirely.")
    group.add_argument("--bad-only", action="store_true", help="Only remove entries with known-bad answer phrases.")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be deleted without deleting.")
    args = parser.parse_args()

    bad_only = args.bad_only
    dry_run = args.dry_run

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}{'Targeted bad-phrase' if bad_only else 'FULL'} cache cleanup\n")

    clear_mongo(bad_only=bad_only, dry_run=dry_run)
    clear_disk(bad_only=bad_only, dry_run=dry_run)

    print("\nDone.")


if __name__ == "__main__":
    main()
