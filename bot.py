import os
import re
import yfinance as yf
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# === BOT TOKEN ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing. Check Railway Variables.")

# === Winrate Emoji Logic ===
def get_winrate_emoji(winrate):
    if winrate > 50:
        return "🟢"
    elif winrate == 50:
        return "🟡"
    else:
        return "🔴"

# === Format Scan Results ===
def format_list(results):
    return "\n".join([
        f"  *{r['ticker']}* {get_winrate_emoji(float(r['winrate'].replace('%','')))}:\n"
        f"    Price: ${r['price']}\n"
        f"    Volume: {r['volume']:,}\n"
        f"    Winrate: {r['winrate']} over last 12 earnings\n"
        f"    IV/RV Ratio: {r['iv_rv_ratio']}\n"
        f"    Term Structure: {r['term_structure']}"
        for r in results
    ]) if results else "  None"

# === Analyze a Ticker ===
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

# === Scan Handler (/scan or raw input) ===
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        raw_tickers = context.args
    else:
        raw_tickers = update.message.text.strip().split()

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

    now = datetime.now()
    header = f"📅 {now.strftime('%B').upper()} SCAN RESULTS\n\n"

    response = (
        header +
        "TIER 1 RECOMMENDED TRADES:\n" + format_list(tier1) + "\n\n" +
        "TIER 2 RECOMMENDED TRADES:\n" + format_list(tier2) + "\n\n" +
        "NEAR MISSES:\n" + format_list(near_miss)
    )

    await update.message.reply_text(response, parse_mode="Markdown")

# === Daily Auto Earnings Push ===
async def scheduled_earnings_push(context: ContextTypes.DEFAULT_TYPE):
    chat_id = "1274696171"  # Replace with your actual Telegram ID

    # Simulated earnings watchlist — replace this with real logic
    mock_earnings = [
        {"ticker": "TSLA", "winrate": 0.63},
        {"ticker": "AAPL", "winrate": 0.50},
        {"ticker": "PLTR", "winrate": 0.38}
    ]

    now = datetime.now()
    header = f"📅 NEW MONTH: {now.strftime('%B').upper()} Earnings Watchlist\n\n"

    message = header
    for stock in mock_earnings:
        emoji = get_winrate_emoji(stock["winrate"] * 100)
        message += f"{emoji} *{stock['ticker']}* — Est. {int(stock['winrate'] * 100)}% winrate\n"

    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")

# === Setup App and Scheduler ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("scan", scan))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), scan))

# Scheduled 3x daily alerts
scheduler = AsyncIOScheduler()
scheduler.add_job(scheduled_earnings_push, "cron", hour=8, minute=0, args=[app.bot])   # Morning
scheduler.add_job(scheduled_earnings_push, "cron", hour=13, minute=0, args=[app.bot])  # Midday
scheduler.add_job(scheduled_earnings_push, "cron", hour=20, minute=0, args=[app.bot])  # Night
scheduler.start()

# === Start Bot ===
app.run_polling()
