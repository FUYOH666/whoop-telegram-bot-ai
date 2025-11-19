# RAS Telegram Bot

English | [Русский](README.md)

<!--
Keywords: telegram bot, whoop integration, health tracking, personal assistant, NLP programming, subconscious programming, daily routine, productivity bot, fitness tracker, wellness bot, AI assistant, LLM integration, OpenRouter, DeepSeek, self-improvement, habit tracking, mindfulness bot
Description: Telegram bot for personal self-improvement with WHOOP integration. Uses LLM for subconscious programming through 6 daily slots. Personalized messages based on physical metrics.
Topics: telegram-bot, whoop-api, health-tracking, personal-assistant, nlp, productivity, fitness, wellness, ai-assistant, llm, openrouter, deepseek, self-improvement, habit-tracking, mindfulness, python, aiogram, apscheduler
-->

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success.svg)

**Personal day metronome: 6 mindful pings for self-improvement.**

Telegram bot with WHOOP integration and LLM for personalized subconscious programming through daily rituals and physical metrics.

## Quick Start

```bash
git clone https://github.com/FUYOH666/whoop-telegram-bot-ai.git
cd whoop-telegram-bot-ai
uv sync
cp .env.example .env
# Fill in your API keys
uv run python -m whoop_telegram_bot_ai.main
```

## Description

Whoop Telegram Bot AI is not just another reminder bot. It's a personal day metronome that helps maintain an ideal rhythm through 6 gentle touches and programs your subconscious for success and abundance.

**Philosophy:** Every message uses Neuro-Linguistic Programming (NLP) principles — positive affirmations in present tense, success visualization, abundance imagery, and big checks. These aren't just reminders, but a subconscious program for creating financial freedom.

**WHOOP Integration:** The bot integrates with WHOOP to get physical metrics (Recovery, Sleep, Strain, Workouts) and uses them in messages for more accurate subconscious programming. Physical state is considered in every slot, allowing for more personalized and relevant messages.

**6 Daily Slots:**

1. **S1 — Morning Body** (07:30) — wake up, breakfast, gym/beach
2. **S2 — "I Am" Foundation** (09:30) — 5–10 minutes of silence and practice
3. **S3 — Focus Quantum** (11:00) — 60–90 minutes of deep work on the main project
4. **S4 — Step to Money** (14:00) — one concrete step to the market
5. **S5 — Sunset & Presence** (17:30) — beach, sunset, contact with the world
6. **S6 — Evening Integration** (21:00) — honest day assessment

## 💡 Why This Project?

The WHOOP app is great, but I find it easier to interact with my own assistant integrated into a Telegram bot. The bot provides morning guidance, reminds me of my daily plan, and everything is adapted using LLM and synchronized with physical metrics for personalized recommendations.

**The Idea:** Create a maximally personalized tool for working with the subconscious, discipline, beliefs, and daily plans that correlate with physical body metrics. This helps avoid cognitive biases and unreliable information from social media.

## 👥 Who Is This For?

- **Clients:** Those who want a personal AI assistant for self-improvement with WHOOP integration
- **Like-minded Developers:** Developers working on similar projects who want to discuss ideas, share experience, or contribute
- **Researchers:** Those interested in subconscious programming through LLM and integration of physical metrics

## ⚠️ WHOOP Token Problem

**Current Situation:** WHOOP API requires token refresh approximately every hour, which is very inconvenient for users.

**Possible Solution:** Create a script that automatically logs into the WHOOP developer portal every hour, receives the code, and inserts it into Telegram for automatic token refresh.

**Invitation to Discussion:** If you have ideas on how to solve this problem, or want to help with implementation — please contact us! Open an [Issue](https://github.com/FUYOH666/whoop-telegram-bot-ai/issues) or [Discussion](https://github.com/FUYOH666/whoop-telegram-bot-ai/discussions) to discuss.

**Note:** The project uses WHOOP API to get real-time data. The repository also contains a `my_whoop_data_2025_11_17/` folder with example exported data, but the main functionality works through the API.

## Features

- **Subconscious Programming (NLP):** All messages use NLP principles — affirmations in present tense, success visualization, abundance imagery
- **Personalization:** Messages adapt based on your slot completion statistics
- **WHOOP Integration:** Physical metrics integrated into all slots for maximum relevance:
  - **S1 (Morning Body):** Yesterday's Recovery — for assessing morning readiness and linking recovery to creating abundance
  - **S2 ("I Am" Foundation):** Yesterday's Sleep — for assessing recovery quality and mental clarity
  - **S3-S5 (Day Slots):** Today's Strain — for assessing current load and energy balance
  - **S6 (Evening Integration):** All day metrics — for comprehensive audit and reflection
- **Extended Messages:** Increased token limits (700 for S1-S5, 1500 for S6) for deeper subconscious programming
- **Real-time Stress Monitoring:** Automatic stress level checks every 30 minutes from 8:00 to 00:00 with smart notifications:
  - Strain checks every 30 minutes during active hours
  - Notifications when stress threshold is exceeded (configurable via `/whoop_threshold`)
  - Smart Recovery integration: more urgent notifications with low Recovery (< 50%), gentler ones with good Recovery (>= 70%)
  - Personalized LLM-generated stress reduction advice based on current state
  - Cooldown between notifications (2 hours default) to avoid spam
  - Notification history via `/whoop_alerts` command
- **Fallback:** If OpenRouter is unavailable, predefined messages from `config.yaml` are used
- **Statistics:** Track slot completion and ideal days via `/stats` command
- **Free Model:** Uses DeepSeek R1T2 Chimera (free) — completely free model with enhanced capabilities

## Installation

### Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) — package manager

### Steps

1. Clone the repository:
```bash
git clone https://github.com/FUYOH666/whoop-telegram-bot-ai.git
cd whoop-telegram-bot-ai
```

2. Install dependencies:
```bash
uv sync
```

3. Create `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

4. Fill in `.env` with your data:
- `TELEGRAM_BOT_TOKEN` — your Telegram bot token (required)
- `OPENROUTER_API_KEY` — OpenRouter API key (required)
- `TELEGRAM_USER_ID` — your Telegram user ID (optional, will be set automatically on first `/start`)
- `WHOOP_CLIENT_ID` — WHOOP Developer Platform Client ID (optional, for WHOOP integration)
- `WHOOP_CLIENT_SECRET` — WHOOP Developer Platform Client Secret (optional, for WHOOP integration)

5. **Configure OpenRouter Privacy** (important for free models):
   - Open https://openrouter.ai/settings/privacy
   - Enable "Enable free endpoints that may train on inputs"
   - Enable "Enable free endpoints that may publish prompts" (optional)
   - Save settings

6. Copy and configure if needed:
   ```bash
   cp config.yaml.example config.yaml
   ```
   Edit `config.yaml`:
   - Slot times (default: 07:30, 09:30, 11:00, 14:00, 17:30, 21:00)
   - Prompts for subconscious programming tailored to your goals
   - LLM parameters (temperature, max_tokens)

7. Run the bot:
```bash
uv run python -m whoop_telegram_bot_ai.main
```

8. Open Telegram and send `/start` command to activate the bot

**Important:** The bot will only send messages to the user who sent the `/start` command. If you specified `TELEGRAM_USER_ID` in `.env`, the scheduler will start immediately. Otherwise, user_id will be set automatically on first `/start`.

## Bot Commands

### Main Commands
- `/start` — greeting and start working
- `/stats` — slot completion statistics for 7 and 30 days
- `/health` — bot and all components status check

### WHOOP Commands
- `/whoop_connect` — connect WHOOP (get authorization URL)
- `/whoop_code <code>` — enter authorization code after WHOOP authorization
- `/whoop_now` — get current WHOOP metrics (Recovery, Sleep, Strain, Workouts)
- `/whoop_monitoring on/off` — enable/disable automatic stress monitoring
- `/whoop_threshold <value>` — set stress threshold for notifications (0-21, default 12.0)
- `/whoop_alerts` — history of recent high stress notifications

## Architecture

- **aiogram** — Telegram Bot API framework
- **APScheduler** — task scheduler for sending slots
- **OpenRouter + DeepSeek V3.1 (free)** — LLM integration for personalized messages with subconscious programming
- **SQLite** — response statistics storage
- **pydantic-settings** — configuration management

## WHOOP Integration

Whoop Telegram Bot AI supports WHOOP integration to get physical metrics (Recovery, Sleep, Strain, Workouts) and include them in the evening S6 slot.

### WHOOP Setup

1. **Create an app in WHOOP Developer Platform:**
   - Register at https://developer.whoop.com/
   - Create a new application
   - Get `Client ID` and `Client Secret`
   - Set Redirect URL (e.g., `https://your-domain.com/whoop-callback.html`)
   - Host Privacy Policy on your website (required for OAuth)

2. **Add credentials to `.env`:**
   ```bash
   WHOOP_CLIENT_ID=your_client_id_here
   WHOOP_CLIENT_SECRET=your_client_secret_here
   WHOOP_REDIRECT_URI=https://your-domain.com/whoop-callback.html
   ```
   Or configure `redirect_uri` in `config.yaml`.

3. **Host callback page on your website:**
   - Upload `whoop_callback.html` file to your website
   - Place it at the URL specified in `WHOOP_REDIRECT_URI` (e.g., `https://your-domain.com/whoop-callback.html`)
   - This is a simple HTML page that handles OAuth callback from WHOOP

4. **Ensure Redirect URL matches:**
   - Redirect URL in WHOOP Developer Platform must exactly match `WHOOP_REDIRECT_URI` in `.env` or `redirect_uri` in `config.yaml`
   - Verify that URLs are identical (including `https://` protocol and path)

5. **Connect WHOOP in the bot:**
   - Send `/whoop_connect` command to the bot
   - Follow the link and authorize in WHOOP
   - After authorization, you'll be redirected to your callback page
   - The page will show an authorization code - copy it
   - Send `/whoop_code <your_code>` command to the bot

**Note:** If the token expires and reconnection is needed, simply repeat step 5. The bot will automatically notify if reconnection is required.

### How It Works

- **Automatic Updates:** WHOOP data is updated daily at 22:00 (after S6 slot)
- **S6 Integration:** In the evening S6 slot, a block with physical metrics is displayed before the main message:
  ```
  📊 WHOOP Physical Metrics:
  Recovery: 85% | Sleep: 7.5h | Strain: 12.5 | Workouts: 2
  ```
- **In LLM Prompt:** WHOOP data is also included in the prompt for message generation, so LLM can consider physical state when assessing the day
- **Automatic Token Refresh:** Access tokens are automatically refreshed on expiration via refresh_token. The system checks tokens before each request and refreshes them 5 minutes before expiration
- **Long-lived Session:** With proper refresh_token setup, the session can work for months without reconnection
- **Rate Limit Handling:** Code automatically handles API limits (10000 requests/day, 100 requests/minute) with retry logic and exponential backoff

**Token Management:**
- Tokens are automatically checked and refreshed before each WHOOP API request
- If refresh_token is missing, the system tries to use the existing token (WHOOP may auto-renew tokens)
- If token expires and refresh_token is missing, the bot will automatically notify about the need to reconnect via `/whoop_connect`

**Stress Monitoring:**
- Automatic monitoring is enabled by default after WHOOP connection
- Strain checks every 30 minutes from 8:00 to 00:00
- Stress threshold is individually configurable via `/whoop_threshold` (default 12.0)
- Notifications consider Recovery for smarter recommendations
- Can be disabled via `/whoop_monitoring off` and re-enabled via `/whoop_monitoring on`

### WHOOP API Rate Limits

WHOOP API has the following limits:
- **10000 requests per day** — more than enough for daily data updates
- **100 requests per minute** — sufficient for all bot operations

**Usage in Whoop Telegram Bot AI:**
- **4 requests** are executed daily (Recovery, Sleep, Strain/Workouts, aggregation) at 22:00
- If token refresh is needed — **1 additional request**
- **Total: ~5 requests per day** — only **0.05% of daily limit**

Code automatically handles rate limit errors (429) with retry and waiting according to `Retry-After` header.

**Note:** WHOOP integration is optional. The bot works fine without it. If WHOOP is not configured or connected, S6 slot works as usual without physical metrics.

## Production Ready

The project is ready for production use:

- ✅ Automatic WHOOP token management (refresh before expiration)
- ✅ Error handling and retry logic for all external APIs
- ✅ Graceful shutdown on bot stop
- ✅ Structured JSON logging
- ✅ Health check endpoint (`/health`)
- ✅ Docker support for easy deployment
- ✅ Systemd service file for Linux servers

### Monitoring

- Structured JSON logs for easy parsing
- Health check command `/health` shows status of all components
- Error tracking with full context in logs

## Development

### Running Tests

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

### Type Checking

```bash
uv run pyright
```

## Deployment

See [DEPLOY.md](DEPLOY.md) for detailed deployment instructions (Docker, Systemd, hosting recommendations).

## Contributing

We welcome contributions! Please feel free to submit a Pull Request.

**Ideas for improvement:**
- Additional integrations (Apple Health, Google Fit, etc.)
- More customization options for prompts
- Support for multiple users
- Web dashboard for statistics
- Export data functionality
- And more!

If you have ideas or suggestions, please open an issue or start a discussion.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

Created with love for self-improvement and goal achievement.

## Acknowledgments

- Built with [aiogram](https://github.com/aiogram/aiogram) - modern Telegram Bot framework
- Uses [OpenRouter](https://openrouter.ai/) for LLM access
- Integrates with [WHOOP](https://www.whoop.com/) for health metrics
- Powered by [DeepSeek V3.1](https://www.deepseek.com/) - free and powerful LLM

---

**Note:** This bot is designed for personal use and self-improvement. It's not a medical device and should not be used as a substitute for professional medical advice.

