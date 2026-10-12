# Project bot entry point

This folder contains game and economy command modules and an entry point that
registers them with the bot services in the repository root.

## Configure and run

1. Install the dependencies from the repository root:

   ```powershell
   pip install -r project\requirements.txt
   ```

2. Copy `.env.example` to `.env` in this folder and set `DISCORD_BOT_TOKEN`.
   Never commit `.env` or share your bot token.
3. From the repository root, start the bot:

   ```powershell
   python project\main.py
   ```

The command modules use shared bot, database, and command helpers from the
repository root. The included economy commands are cash, bank, daily,
leaderboard, lottery, and profile.
