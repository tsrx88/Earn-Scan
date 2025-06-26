import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import yfinance as yf

# === Load bot token from Railway Variables ===
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing. Check Railway Variables.")

# === Example formula logic ===
def analyze_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("currentPrice", 0)
        volume = info.get("volume", 0)

        # Your logic (placeholder values):
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

# === Response formatter ===
def format_scan_results(ticker_list):
    tier1 = []
    tier2 = []
    near_miss = []

    for ticker in ticker_list:
        result = analyze_ticker(ticker)
        if result:
            if result["tier"] == "TIER 1":
                tier1.append(result)
            elif result["tier"] == "TIER 2":
                tier2.append(result)
            else:
                near_miss.append(result)

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

    response = (
        "=== SCAN RESULTS ===\n\n"
        "TIER 1 RECOMMENDED TRADES:\n" + format_list(tier1) + "\n\n"
        "TIER 2 RECOMMENDED TRADES:\n" + format_list(tier2) + "\n\n"
        "NEAR MISSES:\n" + format_list(near_miss)
    )

    return response

# === /scan command ===
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tickers = [t.upper() for t in context.args]
    response = format_scan_results(tickers)
    await update.message.reply_text(response)

# === Message handler for plain ticker input ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    tickers = [word.replace("$", "").upper() for word in text.split() if word.isalpha() or word.startswith("$")]
    if tickers:
        response = format_scan_results(tickers)
        await update.message.reply_text(response)

# === Initialize the bot ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("scan", scan))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
app.run_polling()
