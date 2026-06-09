TIME_WINDOW_HOURS = 6
WEBZ_BASE_URL = "https://api.webz.io/filterWebContent"
OUTPUT_PATH = "output/risk_events.json"
DEFAULT_LOOKBACK_DAYS = 3
SIZE = 100

RISK_QUERY = (
    '(risk OR "financial risk" OR "credit risk" OR "market risk" OR "operational risk"'
    ' OR "liquidity risk" OR "regulatory risk" OR "geopolitical risk" OR "systemic risk"'
    ' OR "bank failure" OR "default" OR "contagion" OR "volatility" OR "stress test"'
    ' OR "capital adequacy" OR "sanctions" OR "fraud" OR "cyber attack" OR "data breach"'
    ' OR "supply chain disruption" OR "natural disaster" OR "pandemic" OR "recession")'
    " site_type:news language:english"
)
