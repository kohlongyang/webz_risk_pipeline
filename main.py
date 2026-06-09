import os
import json
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv

from fetcher import fetch_all_articles
from grouper import group_articles
from transformer import build_event
from config import OUTPUT_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    load_dotenv()
    token = os.getenv("WEBZ_API_TOKEN")
    if not token:
        raise ValueError("WEBZ_API_TOKEN is not set. Copy .env.example to .env and add your token.")

    logger.info("Starting Webz.io risk news pipeline...")
    articles, requests_left = fetch_all_articles(token)

    valid = [a for a in articles if a.get("summary")]
    skipped = len(articles) - len(valid)
    if skipped:
        logger.info("Skipped %d article(s) with missing summaries.", skipped)

    logger.info("Grouping %d articles into events...", len(valid))
    groups = group_articles(valid)

    run_ts = datetime.now(timezone.utc)
    events = [build_event(group, run_ts) for group in groups]

    out_dir = os.path.dirname(OUTPUT_PATH)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump({"total": len(events), "events": events, "success": True}, fh, indent=2, ensure_ascii=False)

    print("\n--- Pipeline Summary ---")
    print(f"  Total articles fetched : {len(articles)}")
    print(f"  Total events created   : {len(events)}")
    print(f"  Output path            : {os.path.abspath(OUTPUT_PATH)}")
    print(f"  API requests remaining : {requests_left}")


if __name__ == "__main__":
    main()
