import datetime
import json
import os
import re
import sys
import unicodedata
import yfinance as yf
from google import genai
from google.genai import types

BANNER_DISCLAIMER = "EXPERIMENTAL - educational use only. Never use for real trading decisions."
DISCLAIMER = "Experimental only. Never use with real money."
MODEL = "gemini-2.5-flash"
HEADLINES_TARGET = 5
WIDTH = 72
INNER = WIDTH - 2

TICKER_MAP = {
    "NQ1!": "NQ=F",
    "ES1!": "ES=F",
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SPX": "^GSPC",
    "NDX": "^NDX",
    "DXY": "DX-Y.NYB",
    "GOLD": "GC=F",
    "OIL": "CL=F",
    "VIX": "^VIX",
}

USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _c(code, text):
    if not USE_COLOR:
        return text
    return f"\x1b[{code}m{text}\x1b[0m"


def bold(t): return _c("1", t)
def dim(t): return _c("2", t)
def cyan(t): return _c("36", t)
def green(t): return _c("32", t)
def red(t): return _c("31", t)
def yellow(t): return _c("33", t)
def gray(t): return _c("90", t)
def magenta(t): return _c("35", t)


def _char_width(ch):
    code = ord(ch)
    if code in (0xFE0F, 0xFE0E):
        return 0
    if unicodedata.combining(ch):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def vlen(s):
    stripped = ANSI_RE.sub("", s)
    width = 0
    i = 0
    n = len(stripped)
    while i < n:
        if i + 1 < n and ord(stripped[i + 1]) == 0xFE0F:
            width += 2
            i += 2
        else:
            width += _char_width(stripped[i])
            i += 1
    return width


def pad_to(text, width, align="<"):
    diff = width - vlen(text)
    if diff <= 0:
        return text
    if align == ">":
        return " " * diff + text
    return text + " " * diff


def wrap_text(text, width):
    words = (text or "").split()
    if not words:
        return [""]
    lines = []
    line = words[0]
    for w in words[1:]:
        if len(line) + 1 + len(w) <= width:
            line += " " + w
        else:
            lines.append(line)
            line = w
    lines.append(line)
    return lines


def card_top():
    print(f"╭{'─' * INNER}╮")


def card_bot():
    print(f"╰{'─' * INNER}╯")


def card_sep():
    print(f"├{'─' * INNER}┤")


def card_line(content=""):
    print(f"│{pad_to(content, INNER)}│")


def card_row(content=""):
    inner = INNER - 2
    print(f"│ {pad_to(content, inner)} │")


def card_split(left, right):
    inner = INNER - 2
    middle = inner - vlen(left) - vlen(right)
    if middle < 1:
        middle = 1
    print(f"│ {left}{' ' * middle}{right} │")


def banner():
    title = f"{bold(cyan('FinanceCLI'))}  {gray('·')}  AI Market Analyzer  {gray('·')}  {dim(MODEL)}"
    card_top()
    card_row(title)
    for line in wrap_text(BANNER_DISCLAIMER, INNER - 2):
        card_row(dim(line))
    card_bot()


def resolve_ticker(symbol):
    key = symbol.strip().upper()
    return TICKER_MAP.get(key, key)


def fetch_history(symbol, period="7d", interval="1d"):
    ticker = resolve_ticker(symbol)
    try:
        data = yf.Ticker(ticker).history(period=period, interval=interval)
    except Exception as e:
        return None, f"yfinance error: {e}"
    if data is None or data.empty:
        return None, "no price data returned"
    return data, None


def fetch_company_name(symbol):
    ticker = resolve_ticker(symbol)
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        info = {}
    return info.get("longName") or info.get("shortName") or symbol.upper()


def trend_arrow(pct):
    if pct > 0.1:
        return "📈"
    if pct < -0.1:
        return "📉"
    return "➡️"


def trend_color(pct):
    if pct > 0:
        return green
    if pct < 0:
        return red
    return gray


def sentiment_color(s):
    low = (s or "").lower()
    if "positive" in low:
        return green
    if "negative" in low:
        return red
    if "mixed" in low:
        return yellow
    if "neutral" in low:
        return gray
    return magenta


def rec_color(r):
    if r == "BUY":
        return green
    if r == "SELL":
        return red
    return yellow


def sparkline(values):
    if not values:
        return ""
    chars = "▁▂▃▄▅▆▇█"
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return chars[0] * len(values)
    out = []
    span = hi - lo
    last = len(chars) - 1
    for v in values:
        idx = int(((v - lo) / span) * last)
        out.append(chars[idx])
    return "".join(out)


def decide_recommendation(pct):
    if pct > 2.0:
        return "BUY"
    if pct < -2.0:
        return "SELL"
    return "HOLD"


def parse_analysis(text):
    if not text:
        return {"sentiment": "Unknown", "reasoning": "No response from model."}
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return {"sentiment": "Unknown", "reasoning": cleaned[:200]}
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"sentiment": "Unknown", "reasoning": cleaned[:200]}
    return {
        "sentiment": obj.get("sentiment") or "Unknown",
        "reasoning": obj.get("reasoning") or "No reasoning returned.",
    }


def fetch_analysis(symbol, current_price, pct, recommendation):
    prompt = (
        f"Use Google Search to find the {HEADLINES_TARGET} most relevant news headlines "
        f"about {symbol} from the last 24 hours.\n"
        f"Context: current price is ${current_price:.2f}, 7-day change {pct:+.2f}%, "
        f"rule-based recommendation is {recommendation}.\n"
        "Return ONLY a strict JSON object with these keys:\n"
        '  "sentiment": one of "Mostly Positive", "Mostly Negative", "Mixed", "Neutral"\n'
        '  "reasoning": one short sentence (max 30 words) explaining why the recommendation '
        'makes sense given the trend and the news. Plain text, no markdown.\n'
        "No prose outside the JSON. No code fences."
    )
    try:
        client = genai.Client()
        resp = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        return parse_analysis(resp.text), None
    except Exception as e:
        return None, f"gemini error: {e}"


def status(msg):
    if not USE_COLOR:
        return
    sys.stdout.write(f"\r\x1b[2K  {dim(msg)}")
    sys.stdout.flush()


def clear_status():
    if not USE_COLOR:
        return
    sys.stdout.write("\r\x1b[2K")
    sys.stdout.flush()


def label_row(label, value, label_width=20):
    label_padded = pad_to(label, label_width)
    card_row(f"{dim(label_padded)}  {value}")


def render_summary(symbol, name, price, pct, closes, sentiment, recommendation, reasoning):
    today = datetime.date.today().strftime("%b %d %Y")
    head_left = f"{bold(cyan(symbol.upper()))}  {gray('·')}  {name}"
    head_right = dim(today)

    arrow = trend_arrow(pct)
    pct_str = trend_color(pct)(f"{pct:+.1f}%")
    spark = trend_color(pct)(sparkline(closes))
    sent_dot = sentiment_color(sentiment)("●")
    rec_dot = rec_color(recommendation)("●")
    rec_label = bold(rec_color(recommendation)(recommendation))

    card_top()
    card_split(head_left, head_right)
    card_sep()
    label_row("Current Price", bold(f"${price:,.2f}"))
    label_row("7-Day Trend", f"{arrow}  {pct_str}   {spark}")
    label_row("News Sentiment", f"{sent_dot} {sentiment_color(sentiment)(sentiment)}")
    label_row("Headlines Analyzed", bold(str(HEADLINES_TARGET)))
    label_row("Recommendation", f"{rec_dot} {rec_label}   {dim('(Experimental)')}")
    card_row()
    card_row(dim("Reasoning"))
    for line in wrap_text(reasoning, INNER - 2):
        card_row(line)
    card_sep()
    card_row(f"{yellow('⚠')}  {dim(DISCLAIMER)}")
    card_bot()


def render_error(symbol, label, err):
    today = datetime.date.today().strftime("%b %d %Y")
    head_left = f"{bold(cyan(symbol.upper()))}"
    head_right = dim(today)
    card_top()
    card_split(head_left, head_right)
    card_sep()
    card_row(red(f"✗ {label} failed"))
    for line in wrap_text(err, INNER - 2):
        card_row(dim(line))
    card_sep()
    card_row(f"{yellow('⚠')}  {dim(DISCLAIMER)}")
    card_bot()


def analyze(symbol):
    status(f"Fetching price data for {symbol.upper()}…")
    data, err = fetch_history(symbol)
    if err:
        clear_status()
        render_error(symbol, "price fetch", err)
        return
    closes = [float(x) for x in data["Close"].tolist()]
    last = closes[-1]
    first = closes[0]
    pct = ((last - first) / first) * 100.0 if first else 0.0
    status(f"Resolving company info for {symbol.upper()}…")
    name = fetch_company_name(symbol)
    recommendation = decide_recommendation(pct)
    status(f"Analyzing live news for {symbol.upper()}…")
    analysis, err = fetch_analysis(symbol, last, pct, recommendation)
    clear_status()
    if err:
        render_summary(
            symbol, name, last, pct, closes,
            "Unavailable", recommendation, err,
        )
        return
    render_summary(
        symbol, name, last, pct, closes,
        analysis["sentiment"], recommendation, analysis["reasoning"],
    )


def prompt_loop():
    print()
    print(dim("Enter a ticker (e.g. NQ1!, ES1!, BTC) or 'quit'."))
    while True:
        try:
            sys.stdout.write(cyan("› ") if USE_COLOR else "> ")
            sys.stdout.flush()
            symbol = input().strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not symbol:
            continue
        if symbol.lower() in ("quit", "exit", "q"):
            return
        print()
        analyze(symbol)
        print()


def main():
    print()
    banner()
    prompt_loop()
    print(dim(BANNER_DISCLAIMER))


if __name__ == "__main__":
    main()
