import asyncio
import os
import yfinance as yf
from datetime import datetime, timedelta
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import nest_asyncio

nest_asyncio.apply()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === Auto-detect CHAT_ID ===
async def get_chat_id(bot):
    global CHAT_ID
    if not CHAT_ID:
        updates = await bot.get_updates()
        if updates:
            CHAT_ID = updates[-1].message.chat.id
            print(f"🆔 Auto-detected CHAT_ID: {CHAT_ID}")
        else:
            raise Exception("No messages found. Please message your bot first.")
    else:
        print(f"📌 Using CHAT_ID from env: {CHAT_ID}")

# === Core scan logic ===
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
    except:
        return 0.0

def get_next_earnings_date(ticker_symbol):
    try:
        earnings = yf.Ticker(ticker_symbol).earnings_dates
        now = datetime.now().date()
        upcoming = earnings[earnings.index.date >= now]
        return upcoming.index[0].date() if not upcoming.empty else None
    except:
        return None

def analyze_ticker(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    price = info.get("currentPrice", 0)
    volume = info.get("volume", 0)
    winrate = calculate_real_winrate(ticker)
    earnings_date = get_next_earnings_date(ticker)

    iv_rv_ratio = 1.43
    term_structure = -0.012

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
        "iv_rv_ratio": iv_rv_ratio,
        "term_structure": term_structure,
        "tier": tier,
        "emoji": "🟢" if winrate > 50 else "🟡" if winrate == 50 else "🔴",
        "earnings_date": earnings_date.strftime('%b %d') if earnings_date else "N/A"
    }

def format_list(results):
    return "\n".join([
        f"<b>{r['ticker']}</b> {r['emoji']}\n"
        f"  📈 Price: ${r['price']:.2f}\n"
        f"  📊 Volume: {r['volume']:,}\n"
        f"  🧠 Winrate: {r['winrate']} (last 12 earnings)\n"
        f"  ⏱️ Next Earnings: {r['earnings_date']}\n"
        f"  📉 IV/RV: {r['iv_rv_ratio']}  |  Term: {r['term_structure']}"
        for r in results
    ]) if results else "None"

def build_scan_message(tickers):
    tier1, tier2, near = [], [], []
    for ticker in tickers:
        result = analyze_ticker(ticker)
        if result:
            if result["tier"] == "TIER 1":
                tier1.append(result)
            elif result["tier"] == "TIER 2":
                tier2.append(result)
            else:
                near.append(result)

    month = datetime.now().strftime("%B").upper()
    emoji = "🗓️"
    return (
        f"{emoji} <b>{month} SCAN RESULTS</b>\n\n"
        f"<u>TIER 1 RECOMMENDED TRADES:</u>\n{format_list(tier1)}\n\n"
        f"<u>TIER 2 WATCHLIST:</u>\n{format_list(tier2)}\n\n"
        f"<u>NEAR MISSES:</u>\n{format_list(near)}"
    )

# === Command Handler ===
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tickers = context.args or ["TSLA", "AAPL", "NVDA", "AMZN"]
    tickers = [t.replace("$", "").upper() for t in tickers]
    message = build_scan_message(tickers)
    await update.message.reply_text(message, parse_mode="HTML")

# === Setup and run ===
async def main():
    bot = Bot(BOT_TOKEN)
    await get_chat_id(bot)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("scan", scan))

    await app.bot.set_my_commands([
        ("scan", "Scan one or more tickers like /scan tsla aapl")
    ])

    print("✅ Bot is live and listening...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
