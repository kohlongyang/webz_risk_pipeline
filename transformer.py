import uuid
from datetime import datetime, timezone
from dateutil import parser as dateutil_parser
from scorer import compute_score


def _format_iso(dt: datetime) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + ".000Z"


def _parse_dt(s: str):
    if not s:
        return None
    try:
        dt = dateutil_parser.parse(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def _locations(article: dict) -> list:
    entities = article.get("entities") or {}
    return [x["name"] for x in (entities.get("locations") or []) if x.get("name")]


def _organizations(article: dict) -> list:
    entities = article.get("entities") or {}
    return [x["name"] for x in (entities.get("organizations") or []) if x.get("name")]


def _member_secondary(article: dict) -> list:
    locs = _locations(article)
    return locs if locs else _organizations(article)


def _event_secondary(group: list) -> list:
    seen = set()
    result = []
    for a in group:
        for loc in _locations(a):
            if loc not in seen:
                result.append(loc)
                seen.add(loc)
    if result:
        return result
    for a in group:
        for org in _organizations(a):
            if org not in seen:
                result.append(org)
                seen.add(org)
    return result


def build_member(article: dict, alert_id: str) -> dict:
    thread = article.get("thread") or {}
    return {
        "id": article.get("uuid", ""),
        "summary": article.get("summary") or "",
        "score": compute_score(
            article.get("performance_score") or 0,
            thread.get("domain_rank") or 1,
        ),
        "firstAppear": _format_iso(_parse_dt(article.get("published") or "")),
        "lastAppear": _format_iso(_parse_dt(article.get("crawled") or "")),
        "permalink": article.get("url") or "",
        "alertId": alert_id,
        "eventType": "t0",
        "primary_triggers": article.get("topics") or [],
        "secondary_triggers": _member_secondary(article),
        "tags": [],
    }


def build_event(group: list, run_timestamp: datetime) -> dict:
    event_id = str(uuid.uuid4())
    alert_id = event_id

    members = [build_member(a, alert_id) for a in group]
    best_member = max(members, key=lambda m: m["score"])

    published_times = [t for t in (_parse_dt(a.get("published") or "") for a in group) if t]
    crawled_times = [t for t in (_parse_dt(a.get("crawled") or "") for a in group) if t]

    first_appear = min(published_times) if published_times else run_timestamp
    last_appear = max(crawled_times) if crawled_times else run_timestamp

    seen = set()
    primary_triggers = []
    for a in group:
        for t in (a.get("topics") or []):
            if t not in seen:
                primary_triggers.append(t)
                seen.add(t)

    return {
        "_id": event_id,
        "_source": {
            "summary": best_member["summary"],
            "eventId": event_id,
            "lastAppear": _format_iso(last_appear),
            "firstAppear": _format_iso(first_appear),
            "created_at": _format_iso(run_timestamp),
            "alertId": alert_id,
            "eventType": "t1",
            "primary_triggers": primary_triggers,
            "secondary_triggers": _event_secondary(group),
            "members_id": [a.get("uuid", "") for a in group],
            "tags": [],
            "t0tags": [],
            "members": members,
        },
    }
