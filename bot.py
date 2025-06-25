import os
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import yfinance as yf

# === Bot Token from Railway ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing. Check Railway Variables.")

# === Core Scanner Logic ===
def analyze_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("currentPrice", 0)
        volume = info.get("volume", 0)

        # Placeholder scoring logic
        winrate = 0.5
        iv_rv_ratio = 1.43
        term_structure = -0.012

        if winrate >= 0.5 and iv_rv_ratio > 1.2:
            tier = "TIER 1"
        elif winrate >= 0.4:
            tier = "TIER 2"
        else:
            tier = "NEAR MISS"

        return {
            "ticker": ticker,
            "price": price,
            "volume": volume,
            "winrate": f"{winrate * 100:.1f}%",
            "iv_rv_ratio": iv_rv_ratio,
            "term_structure": term_structure,
            "tier": tier
        }

    except Exception as e:
        return None

# === Unified Scan Handler ===
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Accept tickers like AAPL, $tsla, msft, etc.
    raw_input = update.message.text
    tickers = re.findall(r"\$?[a-zA-Z]{1,5}", raw_input)
    tickers = [t.replace("$", "").upper() for t in tickers]

    tier1, tier2, near_miss = [], [], []

    for ticker in tickers:
        result = analyze_ticker(ticker)
        if result:
            if result["tier"] == "TIER 1":
                tier1.append(result)
            elif result["tier"] == "TIER 2":
