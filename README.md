# FinanceCLI

> ⚠️ **EXPERIMENTAL — educational use only. Never use with real money.**

A terminal-first AI market analyzer. Pulls a price snapshot from Yahoo Finance, grounds a Gemini 2.5 Flash agent on live news via Google Search, and prints a color-coded analysis card to your terminal. One file. No GUI. No web server. No databases. No nonsense.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Status](https://img.shields.io/badge/status-experimental-orange)
![Interface](https://img.shields.io/badge/interface-CLI%20only-black)
![Model](https://img.shields.io/badge/model-gemini--2.5--flash-4285F4)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Big Honest Disclaimer

This project is a **learning toy**. It is not investment advice. It will tell you `BUY`, `SELL`, or `HOLD` based on a 5-line 7-day percent-change rule and a Gemini-generated sentiment label.

That is **not** how real trading works. The model can hallucinate. The headlines can be stale. Yahoo Finance has a 15-minute delay on most quotes. The recommendation logic is a heuristic written for fun.

> **Do not put real money behind anything this prints.** If you find yourself thinking *"but the bot said BUY..."* — close the terminal and go for a walk.

---

## Table of contents

- [What it does](#what-it-does)
- [How it works](#how-it-works)
- [Stack](#stack)
- [Install](#install)
- [Configure](#configure)
- [Run](#run)
- [Supported tickers](#supported-tickers)
- [Project layout](#project-layout)
- [Customizing](#customizing)
- [Troubleshooting](#troubleshooting)
- [What this project is NOT](#what-this-project-is-not)
- [License](#license)

---

## What it does

Type a ticker, get a card.

```
╭──────────────────────────────────────────────────────────────────────╮
│ NVDA  ·  NVIDIA Corporation                              Apr 25 2026 │
├──────────────────────────────────────────────────────────────────────┤
│ Current Price         $208.27                                        │
│ 7-Day Trend           📈  +5.0%   ▁▂▂▃▅▆█                            │
│ News Sentiment        ● Mostly Positive                              │
│ Headlines Analyzed    5                                              │
│ Recommendation        ● BUY   (Experimental)                         │
│                                                                      │
│ Reasoning                                                            │
│ Strong AI demand and recent earnings beat support continued          │
│ short-term upside despite mounting macro headwinds.                  │
├──────────────────────────────────────────────────────────────────────┤
│ ⚠  Experimental only. Never use with real money.                     │
╰──────────────────────────────────────────────────────────────────────╯
```

In your real terminal that's color-coded:

- Green for up moves and `BUY`
- Red for down moves and `SELL`
- Yellow for `HOLD` and mixed sentiment
- Dim gray for labels, bold for values
- A live unicode sparkline (`▁▂▃▄▅▆▇█`) of the 7 most recent closes

Falls back to plain text automatically if your terminal isn't a TTY, or if you set `NO_COLOR=1`.

---

## How it works

1. **`yfinance`** pulls 7 daily closes for the requested ticker, plus company name from `Ticker.info`.
2. **Rule-based decision** classifies the trend:
   - `pct > +2%` → `BUY`
   - `pct < −2%` → `SELL`
   - otherwise → `HOLD`
3. **Gemini 2.5 Flash** with the **`google_search`** grounding tool fetches the 5 most relevant news headlines from the last 24 hours and returns a strict-JSON payload:
   ```json
   { "sentiment": "Mostly Positive", "reasoning": "…one short sentence…" }
   ```
4. The CLI renders everything as a single styled card and re-prints the experimental disclaimer.

No persistence. No history. No caching. Each query is fresh.

---

## Stack

| Layer        | Tool                                                                     |
| ------------ | ------------------------------------------------------------------------ |
| Language     | Python 3.11+                                                             |
| Prices       | [`yfinance`](https://github.com/ranaroussi/yfinance)                     |
| LLM          | [`google-genai`](https://github.com/googleapis/python-genai) — Gemini 2.5 Flash |
| Live news    | Built-in `google_search` grounding tool                                  |
| Styling      | Raw ANSI escape codes (no `rich`, no `click`, no third-party formatters) |
| Distribution | One Python file. That's it.                                              |

---

## Install

```bash
git clone https://github.com/<you>/FinanceCLI.git
cd FinanceCLI

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

`requirements.txt` is intentionally tiny:

```
yfinance>=0.2.40
google-genai>=0.3.0
```

---

## Configure

You need a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

The bot reads it from the `GEMINI_API_KEY` environment variable. **Never hardcode it.** Pasting your key into `bot.py` and pushing to GitHub will get it auto-revoked within minutes — and bots will burn your quota before that happens.

```bash
# Permanent (zsh on macOS — recommended)
echo 'export GEMINI_API_KEY=AIza...your-key' >> ~/.zshrc
source ~/.zshrc

# Per-terminal
export GEMINI_API_KEY=AIza...your-key

# One-off
GEMINI_API_KEY=AIza...your-key python bot.py
```

Sanity check the value is set in your shell:

```bash
echo "${GEMINI_API_KEY:0:6}...${GEMINI_API_KEY: -4}"
# AIzaSy...XyZ9
```

If that prints `...` or nothing, the key isn't set in this shell.

---

## Run

```bash
python bot.py
```

You'll see the banner and a prompt. Type a ticker:

```
› NVDA
› BTC
› ES1!
› quit
```

Exit with `quit`, `exit`, `q`, or `Ctrl+C`.

---

## Supported tickers

Anything Yahoo Finance accepts works as-is. A few common futures / crypto / index aliases are pre-mapped so you can type the friendlier symbol:

| You type | Resolves to | What it is              |
| -------- | ----------- | ----------------------- |
| `NQ1!`   | `NQ=F`      | Nasdaq-100 futures      |
| `ES1!`   | `ES=F`      | S&P 500 futures         |
| `BTC`    | `BTC-USD`   | Bitcoin                 |
| `ETH`    | `ETH-USD`   | Ethereum                |
| `SPX`    | `^GSPC`     | S&P 500 index           |
| `NDX`    | `^NDX`      | Nasdaq-100 index        |
| `DXY`    | `DX-Y.NYB`  | US Dollar Index         |
| `GOLD`   | `GC=F`      | Gold futures            |
| `OIL`    | `CL=F`      | WTI crude oil futures   |
| `VIX`    | `^VIX`      | CBOE Volatility Index   |

Plain stock tickers (`AAPL`, `NVDA`, `TSLA`, `META`, …) flow straight through.

---

## Project layout

```
FinanceCLI/
├── bot.py            # everything — single-file by design
├── requirements.txt  # two deps, that's it
└── README.md         # you're here
```

All logic lives in `bot.py`. Don't split it unless you have a reason — single-file is part of the project's identity.

---

## Customizing

The whole CLI is one file. Open `bot.py` and grep for what you want to change:

| Want to…                         | Look at                              |
| -------------------------------- | ------------------------------------ |
| Add a ticker shortcut            | `TICKER_MAP`                         |
| Change BUY/SELL thresholds       | `decide_recommendation()`            |
| Change the lookback window       | `period` arg of `fetch_history()`    |
| Use a different Gemini model     | `MODEL` constant                     |
| Resize the card                  | `WIDTH` constant                     |
| Tweak the palette                | `bold / dim / cyan / green / red / yellow / gray` helpers |
| Disable colors entirely          | `export NO_COLOR=1`                  |
| Change the prompt prefix         | `prompt_loop()` (`›` symbol)         |

---

## Troubleshooting

**`gemini error: API_KEY_INVALID`**
The key is missing, has a typo, or has been revoked. Run `echo "${GEMINI_API_KEY:0:6}..."` to confirm it's set in this shell. Get a fresh one at <https://aistudio.google.com/apikey>.

**`yfinance error: …` or `no price data returned`**
Yahoo occasionally rate-limits or returns empty payloads. Wait a minute and try again. Some illiquid or recently delisted tickers won't have 7 daily bars.

**Card borders look misaligned in my terminal**
Your font is missing emoji or block-character glyphs. Try JetBrains Mono, Fira Code, SF Mono, or any modern programming font with full unicode coverage.

**Colors print as raw escape codes (`\x1b[36m...`)**
Your terminal isn't an ANSI TTY (or output is being redirected). Set `NO_COLOR=1`, or pipe through `less -R` if you actually want the colors preserved.

**Recommendation always says HOLD**
The 7-day move is between −2% and +2%. That's the whole rule. Tweak `decide_recommendation()` if you want different thresholds.

---

## What this project is NOT

- ❌ Not a trading bot
- ❌ Not financial advice
- ❌ Not a backtester
- ❌ Not real-time (yfinance has a ~15-minute delay on most quotes)
- ❌ Not opinionated about whether you should buy NVDA
- ❌ Not a place to put real money

It is a fun teaching project for wiring an LLM with grounded tool use to a clean CLI.

---

## License

MIT. Build, fork, remix, share. Just **keep the experimental disclaimer in any output**.

---

> **One last reminder:** this is experimental. The model can be wrong. The headlines can be stale. The recommendation rule is five lines of Python. Never use FinanceCLI for real trading decisions.
