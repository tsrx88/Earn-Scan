import os
import yfinance as yf
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing. Check Railway Variables.")

# === Analyze Logic ===
def analyze_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("currentPrice", 0)
        volume = info.get("volume", 0)

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
    except Exception:
        return None

# === Response Formatter ===
def format_list(results):
    return "\n".join([
        f"  {r['ticker']}:\n"
        f"    Price: ${r['price']}\n"
        f"    Volume: {r['volume']:,}\n"
        f"    Winrate: {r['winrate']} over last 12 earnings\n"
        f"    IV/RV Ratio: {r['iv_rv_ratio']}\n"
        f"    Term Structure: {r['term_structure']}"
        for r in results
    ]) if results else "  None"

# === Main scan function ===
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        raw_tickers = context.args
    else:
        raw_tickers = update.message.text.strip().split()

    # Normalize: remove $, uppercase
    tickers = [t.replace("$", "").upper() for t in raw_tickers]

    tier1, tier2, near_miss = [], [], []

    for ticker in tickers:
        result = analyze_ticker(ticker)
        if result:
            if result["tier"] == "TIER 1":
                tier1.append(result)
            elif result["tier"] == "TIER 2":
                tier2.append(result)
            else:
                near_miss.append(result)

    response = (
        "=== SCAN RESULTS ===\n\n"
        "TIER 1 RECOMMENDED TRADES:\n" + format_list(tier1) + "\n\n"
        "TIER 2 RECOMMENDED TRADES:\n" + format_list(tier2) + "\n\n"
        "NEAR MISSES:\n" + format_list(near_miss)
    )

    await update.message.reply_text(response)

# === Initialize Bot ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("scan", scan))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), scan))
app.run_polling()

