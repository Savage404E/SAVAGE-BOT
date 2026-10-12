"""Coin-flip game command."""

import asyncio
import random
import re
import time
from typing import TYPE_CHECKING, Any

import discord

from commands import _legacy_command

if TYPE_CHECKING:
    bot: Any
    configured_heads_emoji: str
    configured_tails_emoji: str
    configured_cash_emoji: str
    savage_cash_emoji: str
    get_user_data: Any
    load_users: Any
    save_user_data: Any
    save_users: Any


# coinflip/CF command
@_legacy_command
async def coinflip(ctx, *args):
    """
    cf or coinflip (amount or all) - auto select head. max bet is 250000.
    cf or coinflip (tail/t) (amount or all) - select tail
    cf or coinflip (head/h) (amount or all) - select head
    50% win chance, 50% loss. Users cannot win more than 5 times in a row.
    Uses server emoji and flipping animation. 5s cooldown.
    """
    max_bet = 250_000
    min_bet = 1

    # --- 5s cooldown per user ---
    if not hasattr(bot, "cf_cooldowns"):
        bot.cf_cooldowns = {}

    uid = str(ctx.author.id)
    now = int(time.time())
    if uid in bot.cf_cooldowns and now - bot.cf_cooldowns[uid] < 5:
        await ctx.send("⏳ You're on cooldown! Wait 5 seconds between flips.")
        return
    bot.cf_cooldowns[uid] = now

    # parse helper for streaks
    def load_cf_streaks():
        users_data = load_users()
        return users_data.get("cf_streaks", {})

    def save_cf_streaks(data):
        users_data = load_users()
        users_data["cf_streaks"] = data
        save_users(users_data)

    # Parse args
    choice = "head"
    amount = None
    if len(args) == 0:
        await ctx.send("Usage: `!cf <amount or all>` or `!cf <head/tail> <amount or all>`")
        return
    if len(args) == 1:
        if args[0].lower() in ["head", "h"]:
            choice = "head"
        elif args[0].lower() in ["tail", "t"]:
            choice = "tail"
        elif args[0].lower() == "all":
            amount = "all"
        else:
            amount = args[0]
    elif len(args) == 2:
        if args[0].lower() in ["head", "h"]:
            choice = "head"
        elif args[0].lower() in ["tail", "t"]:
            choice = "tail"
        else:
            await ctx.send("Invalid choice. Use head/h or tail/t.")
            return
        amount = args[1]

    # Validate amount
    users_data = load_users()
    user = get_user_data(users_data, ctx.author.id, ctx.guild.id)
    user_cash = user.get("economy", {}).get("cash", 0)
    if amount is None:
        await ctx.send("Usage: `!cf <amount or all>` or `!cf <head/tail> <amount>`")
        return
    # Parse numeric amount, supporting 'k' suffix for thousands
    def _parse_wager(raw):
        s = str(raw).strip().lower()
        if s == "all":
            return min(user_cash, max_bet)
        m = re.match(r"^(\d+)\s*([kK]?)$", s)
        if not m:
            return None
        base = int(m.group(1))
        suf = m.group(2)
        if suf:
            base *= 1000
        return base

    wager = _parse_wager(amount)
    if wager is None:
        await ctx.send("Invalid amount. Use a number like 10000 or 10k, or 'all'.")
        return
    if wager < min_bet:
        await ctx.send(f"Minimum bet is {min_bet}.")
        return
    if wager > user_cash:
        await ctx.send("You don't have enough cash to bet that amount.")
        return
    if wager > max_bet:
        wager = max_bet

    # Deduct bet
    user['economy']['cash'] -= wager
    save_users(users_data)

    heads_emoji = configured_heads_emoji or "🎮"
    tails_emoji = configured_tails_emoji or "🎮"
    cash_emoji = configured_cash_emoji or savage_cash_emoji

    # Animation
    anim_msg = await ctx.send(f"{tails_emoji} Flipping...")
    await asyncio.sleep(1)
    await anim_msg.edit(content=f"{heads_emoji} Flipping...")
    await asyncio.sleep(1)
    await anim_msg.edit(content=f"{tails_emoji} Flipping...")
    await asyncio.sleep(1)

    # Load streaks and enforce max 5 consecutive wins
    streaks = load_cf_streaks()
    uid_str = uid
    user_streak = int(streaks.get(uid_str, 0))

    # Determine win: 50% chance, but if user already won 5 in a row, force a loss
    can_win = user_streak < 5
    win = False
    if can_win:
        win = random.random() < 0.5
    else:
        win = False  # force loss when streak >= 5

    result_side = choice if win else ("tail" if choice == "head" else "head")
    result_emoji = heads_emoji if result_side == "head" else tails_emoji

    # Update streaks and balances
    if win and result_side == choice:
        # win: payout 2x (net gain = wager)
        winnings = wager * 2
        user['economy']['cash'] += winnings
        # increment streak
        streaks[uid_str] = user_streak + 1
        save_user_data(user, ctx.author.id, ctx.guild.id)
        save_cf_streaks(streaks)
        await anim_msg.edit(content=f"{result_emoji} It's {result_side}! {ctx.author.mention} won {cash_emoji} {int(winnings)}!")
    else:
        # loss: reset streak
        streaks[uid_str] = 0
        save_cf_streaks(streaks)
        await anim_msg.edit(content=f"{result_emoji} It's {result_side}! {ctx.author.mention} lost {cash_emoji} {wager}!")
