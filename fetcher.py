import time
import logging
import requests
from datetime import datetime, timezone, timedelta
from config import WEBZ_BASE_URL, DEFAULT_LOOKBACK_DAYS, SIZE, RISK_QUERY

logger = logging.getLogger(__name__)

_WEBZ_HOST = "https://api.webz.io"
_MAX_RETRIES = 3
_BASE_BACKOFF = 2  # seconds; wait = BASE_BACKOFF ** (attempt+1)


def _get_with_retry(url: str, params: dict = None) -> requests.Response:
    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                if attempt < _MAX_RETRIES:
                    wait = _BASE_BACKOFF ** (attempt + 1)
                    logger.warning("Rate limited (429). Retrying in %ds...", wait)
                    time.sleep(wait)
                    continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            if attempt < _MAX_RETRIES:
                wait = _BASE_BACKOFF ** (attempt + 1)
                logger.warning("Request error: %s. Retrying in %ds...", exc, wait)
                time.sleep(wait)
            else:
                raise


def fetch_all_articles(token: str):
    """Fetch all paginated articles. Returns (articles: list[dict], requests_left: int)."""
    lookback_ms = int(
        (datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS)).timestamp() * 1000
    )

    params = {
        "token": token,
        "q": RISK_QUERY,
        "format": "json",
        "sort": "crawled",
        "size": SIZE,
        "ts": lookback_ms,
        "highlight": "false",
        "includeSyndicated": "false",
    }

    articles = []
    requests_left = 0
    url = WEBZ_BASE_URL
    current_params = params

    while True:
        resp = _get_with_retry(url, current_params)
        data = resp.json()

        requests_left = data.get("requestsLeft", requests_left)
        if requests_left < 10:
            logger.warning("Low API requests remaining: %d", requests_left)

        posts = data.get("posts") or []
        articles.extend(posts)
        more = data.get("moreResultsAvailable", 0)
        logger.info(
            "Fetched %d articles (running total: %d), moreResultsAvailable: %d",
            len(posts),
            len(articles),
            more,
        )

        if more == 0:
            break

        next_path = data.get("next")
        if not next_path:
            break

        if next_path.startswith("http"):
            url = next_path
        elif next_path.startswith("/"):
            url = _WEBZ_HOST + next_path
        else:
            url = f"{_WEBZ_HOST}/{next_path}"

        current_params = None  # params are embedded in the next URL

    return articles, requests_left
