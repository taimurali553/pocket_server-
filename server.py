ls -l
"""
Pocket Option Claude MCP starter.
Read-only market tools only. This does NOT log into Pocket Option or place trades.
Deploy behind HTTPS, then add its /mcp endpoint in Claude.
"""
import os
import json
import urllib.request
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Pocket Option AI Pro", stateless_http=True)
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"

def fetch_chart(symbol: str):
    # Public market data where available; Yahoo symbols are not Pocket Option OTC prices.
    url = YAHOO_CHART.format(symbol=symbol.replace("/", "-"))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))

@mcp.tool()
def market_snapshot(symbol: str = "EURUSD=X") -> dict:
    """Get latest available public market quote and recent candles. This may differ from Pocket Option/OTC prices."""
    try:
        data = fetch_chart(symbol)
        result = data["chart"]["result"][0]
        meta = result.get("meta", {})
        timestamps = result.get("timestamp", [])
        quote = result["indicators"]["quote"][0]
        candles = []
        for i, ts in enumerate(timestamps[-20:]):
            j = len(timestamps) - len(timestamps[-20:]) + i
            candles.append({
                "time_utc": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
                "open": quote.get("open", [])[j] if quote.get("open") else None,
                "high": quote.get("high", [])[j] if quote.get("high") else None,
                "low": quote.get("low", [])[j] if quote.get("low") else None,
                "close": quote.get("close", [])[j] if quote.get("close") else None,
                "volume": quote.get("volume", [])[j] if quote.get("volume") else None,
            })
        return {
            "symbol_requested": symbol,
            "display_name": meta.get("longName") or meta.get("shortName"),
            "currency": meta.get("currency"),
            "latest_price": meta.get("regularMarketPrice"),
            "market_time": meta.get("regularMarketTime"),
            "data_source": "Yahoo Finance chart endpoint",
            "warning": "Not Pocket Option's official feed; OTC prices and broker quotes can differ. Data availability is not guaranteed.",
            "candles": candles,
        }
    except Exception as e:
        return {"error": "Could not retrieve public market data.", "details": str(e),
                "hint": "Try a supported Yahoo Finance symbol such as EURUSD=X, GBPUSD=X, or AAPL."}

@mcp.tool()
def explain_signal(symbol: str = "EURUSD=X") -> dict:
    """Return public market data for Claude to analyze; this tool itself does not issue guaranteed buy/sell advice."""
    snapshot = market_snapshot(symbol)
    if "error" in snapshot:
        return snapshot
    return {
        "market_snapshot": snapshot,
        "analysis_instruction": "Analyze the returned candles, identify trend/support/resistance and uncertainty. If evidence is weak, say WAIT. Do not claim certainty or guaranteed profit. This is not financial advice."
    }

@mcp.tool()
def account_capabilities() -> dict:
    """Explain which Pocket Option account actions are not configured in this starter."""
    return {
        "balance": "Unavailable: no verified authorized Pocket Option account API configured.",
        "trade_history": "Unavailable: no verified authorized Pocket Option account API configured.",
        "place_trade": "Disabled: no verified authorized trading API configured.",
        "next_step": "Only connect official, authorized APIs. Never provide your password, OTP, session cookie, or recovery codes to this server."
    }

if __name__ == "__main__":
    # Remote MCP over Streamable HTTP. Production hosting must provide HTTPS.
    mcp.run(transport="streamable-http")
