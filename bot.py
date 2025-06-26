import os
import time
import threading
from telegram import Update, Bot, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import yfinance as yf
from datetime import datetime, timedelta

# === Load bot token from Railway Variables ===
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing. Check Railway Variables.")

bot = Bot(BOT_TOKEN)

# === Real winrate calculation ===
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
        return round((win_count / checked), 2) if checked else 0.0
    except:
        return 0.0

# === Example formula logic ===
def analyze_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("currentPrice", 0)
        volume = info.get("volume", 0)

        winrate = calculate_real_winrate(ticker)
        iv_rv_ratio = 1.43
        term_structure = -0.012

        if winrate >= 0.5 and iv_rv_ratio > 1.2:
            tier = "TIER 1"
        elif winrate >= 0.4:
            tier = "TIER 2"
        else:
            tier = "NEAR MISS"

        if winrate >= 0.9:
            emoji = "🟢🟢🟢"
        elif winrate >= 0.75:
            emoji = "🟢🟢"
        elif winrate > 0.5:
            emoji = "🟢"
        elif winrate == 0.5:
            emoji = "🟡"
        else:
            emoji = "🔴"

        return {
            "ticker": ticker,
            "price": price,
            "volume": volume,
            "winrate": f"{winrate * 100:.1f}%",
            "iv_rv_ratio": iv_rv_ratio,
            "term_structure": term_structure,
            "tier": tier,
            "emoji": emoji
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
            f"  {r['ticker']} {r['emoji']}\n"
            f"    💰 Price: ${r['price']}\n"
            f"    📊 Volume: {r['volume']:,}\n"
            f"    🧠 Winrate: {r['winrate']}  (12Q) \n"
            f"    📉 IV/RV Ratio: {r['iv_rv_ratio']}\n"
            f"    ⏳ Term Structure: {r['term_structure']}"
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

# === /trending command ===
async def trending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top8 = ["TSLA", "AAPL", "NVDA", "AMD", "META", "AMZN", "MSFT", "NFLX"]
    response = format_scan_results(top8)
    await update.message.reply_text("🔥 <b>Trending Monthly 12Q Scan:</b>\n\n" + response, parse_mode="HTML")

# === Menu /start command ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🔍 Scan", "🔥 Trending"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Welcome to 12Q. Choose an option:", reply_markup=reply_markup)

# === Message handler for plain ticker input and button presses ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if "trending" in text:
        await trending(update, context)
    elif "scan" in text:
        await update.message.reply_text("Use /scan followed by ticker(s), like /scan tsla nvda")
    else:
        tickers = [word.replace("$", "").upper() for word in text.split() if word.isalpha() or word.startswith("$")]
        if tickers:
            response = format_scan_results(tickers)
            await update.message.reply_text(response)

# === Background thread for scheduled alerts ===
def schedule_worker():
    tickers = ["TSLA", "AAPL", "NVDA"]  # ← You can customize
    while True:
        now = datetime.now()
        target_times = [(8, 0), (13, 0), (20, 0)]  # 8AM, 1PM, 8PM
        if (now.hour, now.minute) in target_times:
            message = format_scan_results(tickers)
            try:
                bot.send_message(chat_id=os.getenv("CHAT_ID"), text=message)
            except Exception as e:
                print(f"Failed to send scheduled message: {e}")
            time.sleep(60)  # prevent double-send within the same minute
        time.sleep(30)

# === Initialize the bot ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))
app.add_handler(CommandHandler("trending", trending))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# Start thread
threading.Thread(target=schedule_worker, daemon=True).start()

# Start bot
app.run_polling()
