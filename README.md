# webz_risk_pipeline

A single-run Python pipeline that fetches risk-related news from the [Webz.io](https://webz.io) API, groups articles into events by shared topics and time proximity, and writes structured JSON output.

---

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Setup](#setup)
- [Configuration](#configuration)
- [Running the Pipeline](#running-the-pipeline)
- [Output Schema](#output-schema)
- [How It Works](#how-it-works)
  - [Fetching](#fetching)
  - [Grouping](#grouping)
  - [Scoring](#scoring)
  - [Transforming](#transforming)
- [Running Tests](#running-tests)
- [Error Handling](#error-handling)

---

## Overview

The pipeline performs five steps on every run:

1. Loads an API token from `.env`
2. Fetches all paginated results from Webz.io matching a risk-focused Boolean query
3. Groups articles into events — articles that share at least one topic and whose crawl timestamps fall within a 6-hour window are merged into the same event
4. Transforms each event group into a structured JSON object
5. Writes the result to `output/risk_events.json` and prints a run summary

---

## Project Structure

```
webz_risk_pipeline/
├── main.py           # Entry point
├── fetcher.py        # Webz API calls and pagination
├── grouper.py        # Article grouping logic
├── transformer.py    # Article → member/event object mapping
├── scorer.py         # Relevance score computation
├── config.py         # Constants (query, time window, paths)
├── requirements.txt  # Third-party dependencies
├── .env.example      # Token template — copy to .env and fill in
├── test_grouper.py   # Unit tests for the grouper
└── output/
    └── risk_events.json   # Generated on each run
```

---

## Requirements

- Python 3.9+
- A [Webz.io](https://webz.io) API token

Third-party packages (all in `requirements.txt`):

| Package | Use |
|---|---|
| `requests` | HTTP calls to Webz.io |
| `python-dotenv` | Loads `WEBZ_API_TOKEN` from `.env` |
| `python-dateutil` | Robust ISO 8601 datetime parsing |

---

## Setup

**1. Clone / download the project and enter the directory:**

```bash
cd webz_risk_pipeline
```

**2. Install dependencies:**

```bash
pip install -r requirements.txt
```

**3. Create your `.env` file:**

```bash
cp .env.example .env
```

Open `.env` and set your token:

```
WEBZ_API_TOKEN=your_actual_token_here
```

The token is the only required configuration. It is never stored in any source file.

---

## Configuration

All tunable constants live in `config.py`:

| Constant | Default | Description |
|---|---|---|
| `TIME_WINDOW_HOURS` | `6` | Maximum crawled-time spread for articles to be grouped into one event |
| `DEFAULT_LOOKBACK_DAYS` | `3` | How far back (in days) to fetch articles from Webz.io |
| `SIZE` | `100` | Articles per API page (Webz.io maximum) |
| `OUTPUT_PATH` | `output/risk_events.json` | Where the result JSON is written |
| `WEBZ_BASE_URL` | `https://api.webz.io/filterWebContent` | Webz.io endpoint |
| `RISK_QUERY` | *(see below)* | Boolean query sent to Webz.io |

The default risk query targets financial, geopolitical, and operational risk keywords on news sites in English:

```
(risk OR "financial risk" OR "credit risk" OR "market risk" OR "operational risk"
 OR "liquidity risk" OR "regulatory risk" OR "geopolitical risk" OR "systemic risk"
 OR "bank failure" OR "default" OR "contagion" OR "volatility" OR "stress test"
 OR "capital adequacy" OR "sanctions" OR "fraud" OR "cyber attack" OR "data breach"
 OR "supply chain disruption" OR "natural disaster" OR "pandemic" OR "recession")
site_type:news language:english
```

Edit `RISK_QUERY` in `config.py` to narrow or broaden coverage.

---

## Running the Pipeline

```bash
python main.py
```

Example console output:

```
2025-01-01 12:00:01 INFO Starting Webz.io risk news pipeline...
2025-01-01 12:00:02 INFO Fetched 100 articles (running total: 100), moreResultsAvailable: 1
2025-01-01 12:00:03 INFO Fetched 87 articles (running total: 187), moreResultsAvailable: 0
2025-01-01 12:00:03 INFO Grouping 183 articles into events...

--- Pipeline Summary ---
  Total articles fetched : 187
  Total events created   : 54
  Output path            : /path/to/webz_risk_pipeline/output/risk_events.json
  API requests remaining : 961
```

The output file is overwritten on each run.

---

## Output Schema

`output/risk_events.json`:

```json
{
  "total": 2,
  "events": [
    {
      "_id": "<uuid4>",
      "_source": {
        "summary": "Summary of the highest-scoring article in the group.",
        "eventId": "<uuid4>",
        "firstAppear": "2025-01-01T00:41:00.000Z",
        "lastAppear": "2025-01-01T06:55:00.000Z",
        "created_at": "2025-01-01T12:00:03.000Z",
        "alertId": "<uuid4>",
        "eventType": "t1",
        "primary_triggers": ["Finance->risk", "Economy->recession"],
        "secondary_triggers": ["United States", "Federal Reserve"],
        "members_id": ["<article_uuid>", "<article_uuid>"],
        "tags": [],
        "t0tags": [],
        "members": [
          {
            "id": "<article_uuid>",
            "summary": "Article summary text.",
            "score": 42,
            "firstAppear": "2025-01-01T00:41:00.000Z",
            "lastAppear": "2025-01-01T06:55:00.000Z",
            "permalink": "https://news-source.com/article",
            "alertId": "<uuid4>",
            "eventType": "t0",
            "primary_triggers": ["Finance->risk"],
            "secondary_triggers": ["United States"],
            "tags": []
          }
        ]
      }
    }
  ],
  "success": true
}
```

### Field Reference

**Event (`_source`)**

| Field | Description |
|---|---|
| `_id` / `eventId` / `alertId` | Same UUID4 generated per event |
| `summary` | Summary text of the highest-scoring member article |
| `firstAppear` | Earliest `published` timestamp across all members |
| `lastAppear` | Latest `crawled` timestamp across all members |
| `created_at` | Pipeline run timestamp (UTC) |
| `eventType` | Always `"t1"` |
| `primary_triggers` | Deduplicated union of all member topics |
| `secondary_triggers` | Union of all member location names; falls back to organization names if no locations exist |
| `members_id` | List of member article UUIDs |
| `members` | Full member objects (see below) |

**Member**

| Field | Description |
|---|---|
| `id` | Webz.io article UUID |
| `summary` | Article summary |
| `score` | Integer 0–100 (see Scoring) |
| `firstAppear` | Article `published` timestamp |
| `lastAppear` | Article `crawled` timestamp |
| `permalink` | Article URL |
| `alertId` | Same UUID4 as parent event |
| `eventType` | Always `"t0"` |
| `primary_triggers` | Article topics from Webz.io |
| `secondary_triggers` | Location names; falls back to organization names if empty |

All timestamps are UTC ISO 8601 in `YYYY-MM-DDTHH:MM:SS.000Z` format.

---

## How It Works

### Fetching

`fetcher.py` calls `GET https://api.webz.io/filterWebContent` with the configured query and a `ts` parameter set to 3 days ago (Unix ms). It follows the `next` URL in each response until `moreResultsAvailable == 0`, accumulating all articles into a flat list.

### Grouping

`grouper.py` implements a **greedy sliding-window** algorithm:

1. Sort all articles by `crawled` timestamp ascending.
2. For each article, scan existing groups in order. The article joins the first group that satisfies **both** conditions:
   - The group's window start is within `TIME_WINDOW_HOURS` (6 h) of the article's crawled time.
   - The article shares at least one topic with the group's accumulated topic set.
3. When an article joins a group, its topics are merged into the group's topic set — this enables **chain grouping**: article C can match a group via a topic introduced by article B, even if C shares no topic with the original article A that started the group.
4. If no existing group matches, a new group is created anchored at the article's crawled time.

Articles with no topics always form singleton groups.

### Scoring

`scorer.py` computes a relevance score (0–100) from two signals:

```
virality  = performance_score × 10
authority = max(0, 10 − log10(domain_rank)) × 5
score     = min(round(virality + authority), 100)
```

- **Virality** rewards articles with high social/engagement performance scores from Webz.io.
- **Authority** rewards articles from high-authority domains (low domain rank number = higher authority).

### Transforming

`transformer.py` maps Webz.io article fields to the target schema. The highest-scoring member's summary is promoted to the event-level summary. All timestamps are normalised to UTC and formatted as `.000Z`.

---

## Running Tests

```bash
python test_grouper.py
```

The test suite covers 20 cases across five classes:

| Class | What it tests |
|---|---|
| `TestGroupArticlesBasic` | Shared topic within / outside window, no shared topic |
| `TestGroupArticlesBoundary` | Exact 6-hour boundary, just past boundary, window anchor |
| `TestGroupArticlesTopics` | Empty topics, `None` topics, chain grouping, chain cut by time |
| `TestGroupArticlesMultipleGroups` | Two independent topic streams, three time-separated batches |
| `TestGroupArticlesSorting` | Unsorted and reverse-order input |
| `TestGroupArticlesMissingFields` | Missing `crawled`, missing both timestamps |

Expected output:

```
Ran 20 tests in 0.010s

OK
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| HTTP 429 rate limit | Exponential backoff — waits 2 s, 4 s, 8 s; raises after 3 retries |
| Other HTTP errors | Same retry logic; raises `requests.HTTPError` on final failure |
| `requestsLeft` < 10 | Logs a warning and continues |
| Article with no `summary` | Skipped before grouping; logged as a count |
| Missing `topics`, `entities`, `performance_score`, `domain_rank` | Defaulted to empty list / `0` / `1` respectively |
| Missing `crawled` timestamp | Falls back to `published`; falls back to `datetime.min` if both absent |
