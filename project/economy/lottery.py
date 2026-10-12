# lottery
import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
import re

import discord

from commands import _legacy_command

if TYPE_CHECKING:
    bot: Any
    get_user_data: Any
    load_users: Any
    save_user_data: Any
    save_users: Any

# Lottery functions now use SQLite (part of users data)
LOTTERY_MAX = 300_000
LOTTERY_END_HOUR = 0  # 12AM IST (UTC+5:30)
LOTTERY_END_MINUTE = 0

def get_lottery_end_time():
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)  # IST
    end = now.replace(hour=LOTTERY_END_HOUR, minute=LOTTERY_END_MINUTE, second=0, microsecond=0)
    if now >= end:
        end += timedelta(days=1)
    return end

def format_time_left(dt):
    now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    left = int((dt - now).total_seconds())
    hours, rem = divmod(left, 3600)
    mins, secs = divmod(rem, 60)
    return f"{hours}h {mins}m {secs}s"

@_legacy_command
async def lottery(ctx, cash: int = None):
    """
    !lottery - See lottery status.
    !lottery <cash> - Add cash to the lottery (max 300k per user per day).
    """
    users_data = load_users()
    user = get_user_data(users_data, ctx.author.id, ctx.guild.id)
    lottery_data = users_data.get("lottery_data", {"players": {}, "history": []})
    end_time = get_lottery_end_time()
    time_left = format_time_left(end_time)
    submissions = lottery_data.get("submissions", {})
    jackpot = lottery_data.get("jackpot", 0)
    user_id = str(ctx.author.id)
    user_submission = submissions.get(user_id, 0)
    num_gamblers = len(submissions)
    last_winner_id = lottery_data.get("last_winner")
    last_winner_mention = None
    if last_winner_id:
        try:
            last_winner_user = await bot.fetch_user(int(last_winner_id))
            last_winner_mention = last_winner_user.mention
        except Exception:
            last_winner_mention = f"<@{last_winner_id}>"
    else:
        last_winner_mention = "None"

    # Show status
    if cash is None:
        embed = discord.Embed(
            title="🎰 SAVAGE Lottery Status!",
            description="Lottery ends every day at 12AM IST! Good Luck!!",
            color=discord.Color.gold()
        )
        embed.add_field(name="Last Won", value=f"{last_winner_mention} - who won the lottery before it", inline=False)
        embed.add_field(name="Your Total Submission", value=f"```{user_submission}```", inline=True)
        percent = (user_submission / jackpot * 100) if jackpot > 0 else 0
        embed.add_field(name="Winning Chance", value=f"```{percent:.12f}%```", inline=True)
        embed.add_field(name="Number of Gamblers", value=f"```{num_gamblers} users```", inline=True)
        embed.add_field(name="Current Jackpot", value=f"```{jackpot} cash```", inline=True)
        embed.add_field(name="Ends in", value=f"```{time_left}```", inline=True)
        embed.set_footer(text="*Percentage and jackpot may change over time•Today at " + datetime.now(timezone.utc).strftime("%I:%M %p"))
        await ctx.send(embed=embed)
        return

    # Add cash to lottery
    if cash < 1 or cash > LOTTERY_MAX:
        await ctx.send(f"Maximum lottery submission is {LOTTERY_MAX} cash per day!")
        return
    economy = user.setdefault("economy", {})
    if economy.get("cash", 0) < cash:
        await ctx.send("You don't have enough cash to submit!")
        return
    # Add submission
    submissions[user_id] = submissions.get(user_id, 0) + cash
    jackpot += cash
    economy["cash"] = economy.get("cash", 0) - cash
    save_user_data(user, ctx.author.id, ctx.guild.id)
    users_data["lottery_data"]["submissions"] = submissions
    users_data["lottery_data"]["jackpot"] = jackpot
    save_users(users_data)
    percent = (submissions[user_id] / jackpot * 100) if jackpot > 0 else 0
    embed = discord.Embed(
        title="🎰 SAVAGE's Lottery Submission",
        description="Lottery ends once a day! The maximum lottery submission is 300k cash!",
        color=discord.Color.purple()
    )
    embed.add_field(name="You added", value=f"```{cash} Cowoncy```", inline=True)
    embed.add_field(name="Your Total Submission", value=f"```{submissions[user_id]} cash```", inline=True)
    embed.add_field(name="Winning Chance", value=f"```{percent:.12f}%```", inline=True)
    embed.add_field(name="Current Jackpot", value=f"```{jackpot} cash```", inline=True)
    embed.add_field(name="Ends in", value=f"```{time_left}```", inline=True)
    embed.set_footer(text="*Percentage and jackpot may change over time•Today at " + datetime.now(timezone.utc).strftime("%I:%M %p"))
    await ctx.send(embed=embed)

# Optional: Add a background task to pick a winner at 12AM IST and reset lottery
async def lottery_winner_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        end_time = get_lottery_end_time()
        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        wait_seconds = (end_time - now).total_seconds()
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)
        users_data = load_users()
        lottery_data = users_data.get("lottery_data", {"players": {}, "history": []})
        submissions = lottery_data.get("submissions", {})
        jackpot = lottery_data.get("jackpot", 0)
        winner_id = None
        if submissions and jackpot > 0:
            winner_id = random.choices(list(submissions.keys()), weights=submissions.values())[0]
            # Give jackpot
            users_data = load_users()
            user = get_user_data(users_data, int(winner_id), 0)  # No guild ID for lottery
            economy = user.setdefault("economy", {})
            economy["cash"] = economy.get("cash", 0) + jackpot
            save_user_data(user, int(winner_id), 0)
            # Save last winner
            users_data["lottery_data"] = {"submissions": {}, "jackpot": 0, "last_end": end_time.isoformat(), "last_winner": winner_id}
            save_users(users_data)
        else:
            # No entries, just reset
            users_data["lottery_data"] = {"submissions": {}, "jackpot": 0, "last_end": end_time.isoformat(), "last_winner": lottery_data.get("last_winner")}
            save_users(users_data)
        await asyncio.sleep(5)  # Small delay before next check

async def setup_hook():
    if not hasattr(bot, "lottery_task_started"):
        bot.lottery_task_started = True
        bot.loop.create_task(lottery_winner_task())

bot.setup_hook = setup_hook