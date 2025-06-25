import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import yfinance as yf

# === Bot Token ===
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing. Check Railway Variables.")

# === Scanner Logic ===
def analyze_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("currentPrice", 0)
        volume = info.get("volume", 0)

        # Placeholder logic (you can improve this later)
        winrate = 0.5  # Hardcoded for now
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

# === /scan command ===
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tickers = [t.upper() for t in context.args]
    tier1 = []

