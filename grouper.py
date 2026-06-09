from datetime import datetime, timezone, timedelta
from dateutil import parser as dateutil_parser
from config import TIME_WINDOW_HOURS


def _parse_crawled(article: dict) -> datetime:
    raw = article.get("crawled") or article.get("published") or ""
    if not raw:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        dt = dateutil_parser.parse(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return datetime.min.replace(tzinfo=timezone.utc)


def group_articles(articles: list) -> list:
    """
    Group articles sharing at least one topic within a TIME_WINDOW_HOURS sliding window.

    Algorithm: sort by crawled ascending, then greedily assign each article to the
    first existing group that (a) shares a topic and (b) whose window_start is within
    TIME_WINDOW_HOURS of the article's crawled time.  Articles with no topics always
    form their own singleton group.
    """
    if not articles:
        return []

    time_window = timedelta(hours=TIME_WINDOW_HOURS)
    sorted_articles = sorted(articles, key=_parse_crawled)

    # Each entry: {"articles": [...], "topics": set(), "window_start": datetime}
    groups = []

    for article in sorted_articles:
        article_crawled = _parse_crawled(article)
        article_topics = set(article.get("topics") or [])

        assigned = False
        for group in groups:
            if article_crawled - group["window_start"] > time_window:
                continue
            if article_topics and article_topics & group["topics"]:
                group["articles"].append(article)
                group["topics"] |= article_topics
                assigned = True
                break

        if not assigned:
            groups.append({
                "articles": [article],
                "topics": article_topics.copy(),
                "window_start": article_crawled,
            })

    return [g["articles"] for g in groups]
