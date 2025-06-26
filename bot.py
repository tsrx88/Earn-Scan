import asyncio
import os
import yfinance as yf
from datetime import datetime, timedelta
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# === ENV VARIABLES ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === Auto-Detect Chat ID if not provided ===
async def get_chat_id():
    global CHAT_ID
    if not CHAT_ID:
        bot = Bot(BOT_TOKEN)
        updates = await bot.get_updates()
        if updates:
            CHAT_ID = updates[-1].message.chat.id
            print(f"🆔 Auto-detected CHAT_ID: {CHAT_ID}")
        else:
            raise Exception("No messages found. Please message your bot first.")
    else:
        print(f"📌 Using CHAT_ID from env: {CHAT_ID}")

# === Analysis Functions ===
def calculate_real_winrate(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        earnings = ticker.earnings_dates
        if earnings is None or earnings.empty:
            return 0.0

        win_count, checked = 0, 0

        for index, row in earnings.head(12).iterrows():
            earnings_date = row.name.date()
            history = ticker.history(start=earnings_date - timedelta(days=3), end=earnings_date + timedelta(days=3))

            if len(history) < 3:
                continue

            before = history[history.index.date < earnings_date]
            after = history[history.index.date > earnings_date]

            if not before.empty and not after.empty:
                before_close = before.iloc[-1]['Close']
                after_close = after.iloc[0]['Close']
                if after_close > before_close:
                    win_count += 1
                checked += 1

        return round((win_count / checked) * 100, 1) if checked else 0.0
    except Exception as e:
        print(f"Error calculating winrate for {ticker_symbol}: {e}")
        return 0.0

def get_next_earnings_date(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        earnings = ticker.earnings_dates
        now = datetime.now().date()
        upcoming = earnings[earnings.index.date >= now]
        return upcoming.index[0].date() if not upcoming.empty else None
    except Exception as e:
        print(f"Error getting next earnings date for {ticker_symbol}: {e}")
        return None

def analyze_ticker(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    price = info.get("currentPrice", 0)
    volume = info.get("volume", 0)
    winrate = calculate_real_winrate(ticker)
    earnings_date = get_next_earnings_date(ticker)

    iv_rv_ratio = 1.43  # placeholder
    term_structure = -0.012  # placeholder

    if winrate >= 50 and iv_rv_ratio > 1.2:
        tier = "TIER 1"
    elif winrate >= 40:
        tier = "TIER 2"
    else:
        tier = "NEAR MISS"

    return {
        "ticker": ticker.upper(),
        "price": price,
        "volume": volume,
        "winrate": f"{winrate:.1f}%",
        "next_earnings": earnings_date.strftime('%b %d') if earnings_date else "N/A",
        "iv_rv_ratio": iv_rv_ratio,
        "term_structure": term_structure,
        "tier": tier,
        "emoji": "🟢" if winrate > 50 else "🟡" if winrate == 50 else "🔴"
    }

def format_result(r):
    return (
        f"<b>{r['ticker']}</b> {r['emoji']}\n"
        f"  📈 Price: ${r['price']:.2f}\n"
        f"  📊 Volume: {r['volume']:,}\n"
        f"  🧠 Winrate: {r['winrate']} (last 12 earnings)\n"
        f"  ⏱️ Next Earnings: {r['next_earnings']}\n"
        f"  📉 IV/RV: {r['iv_rv_ratio']}  |  Term: {r['term_structure']}"
    )

# === Scheduled Task ===
async def scheduled_scan(app):
    tickers = ["TSLA", "AAPL"]  # Customize these tickers
    results = [analyze_ticker(t) for t in tickers]
    message = "\n\n".join([format_result(r) for r in results])
    await app.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML")
    print(f"📅 Scheduled scan completed at {datetime.now()}")

# === Command Handler ===
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tickers = context.args
    if not tickers:
        await update.message.reply_text("Usage: /scan TSLA AAPL")
        return
    results = [analyze_ticker(t.strip('$')) for t in tickers]
    message = "\n\n".join([format_result(r) for r in results])
    await update.message.reply_text(message, parse_mode="HTML")

# === Free-form Text Handler ===
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper().replace("$", "")
    if len(text) <= 5 and text.isalnum():
        result = analyze_ticker(text)
        message = format_result(result)
        await update.message.reply_text(message, parse_mode="HTML")

# === Main Setup ===
async def main():
    await get_chat_id()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_handler))
    print("✅ Bot is live and listening...")
    
    # Set up scheduler with BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_scan, 'interval', minutes=5, args=[app])  # Test with 5 minutes
    scheduler.start()

    # Run polling and handle shutdown
    await app.initialize()
    try:
        await app.run_polling(allowed_updates=Update.ALL_TYPES)  # Let polling manage the loop
    except Exception as e:
        print(f"Polling error: {e}")
        await app.shutdown()  # Ensure shutdown on error
    finally:
        await app.shutdown()
        scheduler.shutdown()
        print("🛑 Bot shutdown completed.")

if __name__ == "__main__":
    # Use asyncio.run() to start the bot
    asyncio.run(main())
