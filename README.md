# Telegram Bot (aiogram 3.x)

Project skeleton for a production-ready Telegram bot using **aiogram 3.x** and **PostgreSQL**.

## Structure

- `bot/` - application package
  - `main.py` - bot entry point (polling)
  - `config.py` - config handling via environment variables
  - `db/` - database module (placeholders)
  - `parsers/` - parsers module (WB, Ozon, Детский Мир) placeholders
  - `filtering/` - filtering module placeholder
  - `scheduler/` - scheduler module placeholder
  - `posting/` - posting module placeholder
  - `utils/` - shared utilities

## Configuration

Create a `.env` file in the project root:

```env
BOT_TOKEN=123456:ABCDEF
POSTGRES_DSN=postgresql+asyncpg://user:password@localhost:5432/dbname
```

Environment variables used:

- `BOT_TOKEN`
- `POSTGRES_DSN`

## Run

```bash
pip install -r requirements.txt
python -m bot
```
