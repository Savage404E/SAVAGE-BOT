#slot command
"""Slot-machine game command."""

import asyncio
import random
import re
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

from commands import _legacy_command

if TYPE_CHECKING:
    WeightedRNG: Any
    bot: Any
    savage_cash_emoji: str
    get_user_data: Any
    load_users: Any
    save_users: Any


# slot command
def load_slot_cooldowns():
    users_data = load_users()
    return users_data.get("slot_cooldowns", {})

def save_slot_cooldowns(data):
    users_data = load_users()
    users_data["slot_cooldowns"] = data
    save_users(users_data)

@_legacy_command
@commands.cooldown(1, 6, commands.BucketType.user)
async def slot(ctx, amount: str = None):
    """Play the slot machine. Max bet 300k. 6 second cooldown."""
    if not amount:
        await ctx.send("Usage: `s slot <amount>` (1-300k, 300k max, or 'all')")
        return

    # Parse amount
    def _parse_amt(raw):
        s = str(raw).strip().lower()
        if s == "all":
            return min(balance, 300000)
        m = re.match(r"^(\d+)\s*([kK]?)$", s)
        if not m:
            return None
        base = int(m.group(1))
        if m.group(2):
            base *= 1000
        return min(base, 300000)

    amt = _parse_amt(amount)
    if amt is None or amt < 1:
        await ctx.send("Invalid amount! Use 1-300k, 300k max, or 'all'.")
        return

    users_data = load_users()
    user = get_user_data(users_data, ctx.author.id, ctx.guild.id if ctx.guild else None)
    balance = user.get("economy", {}).get("cash", 0)
    if amt > balance:
        await ctx.send("You don't have enough cash!")
        return

    # Deduct bet
    user["economy"]["cash"] -= amt
    save_users(users_data)

    # Emojis
    srv = bot.get_guild(1374726576742072371)
    slotplay = discord.utils.get(srv.emojis, name="slotplay") if srv else None
    slotplay = slotplay or "🎰"
    cash_emoji = savage_cash_emoji

    # Enhanced slot symbols with weighted probabilities
    symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎", "7️⃣"]
    base_weights = [30, 25, 20, 15, 6, 3, 1]  # higher index = rarer
    
    # Get user's recent slot performance
    recent_slots = user.get("recent_slots", [])
    if len(recent_slots) >= 5:
        recent_win_rate = sum(recent_slots[-5:]) / 5
    else:
        recent_win_rate = 0.3  # Default to 30% if not enough data
    
    # Adjust weights based on recent performance
    adjusted_weights = WeightedRNG.adaptive_weighted_choice(base_weights, recent_win_rate)
    reels = [random.choices(symbols, weights=adjusted_weights, k=3) for _ in range(3)]

    # Build animated frames
    frames = []
    for i in range(3):
        line = [reels[j][i] for j in range(3)]
        frame = (
            f"════╗ **SLOT** | SAVAGE BET: {amt:,}\n"
            f"    ╔════════════════════╗\n"
            f"    ║ {line[0]} {line[1]} {line[2]} ║\n"
            f"    ╚════════════════════╝\n"
            f"════╝  Spinning..."
        )
        frames.append(frame)

    msg = await ctx.send(frames[0])
    for f in frames[1:]:
        await asyncio.sleep(1)
        await msg.edit(content=f)

    # Final result
    final = [reels[j][2] for j in range(3)]
    same = all(x == final[0] for x in final)
    multiplier = 0
    if same:
        sym = final[0]
        if sym == "7️⃣":
            multiplier = 10
        elif sym == "💎":
            multiplier = 5
        elif sym == "🔔":
            multiplier = 3
        else:
            multiplier = 2
    win = int(amt * multiplier)

    # Update balance and track results
    user["economy"]["cash"] += win
    
    # Track slot performance
    won = win > 0
    user.setdefault("recent_slots", []).append(1 if won else 0)
    
    # Keep only last 10 slot results
    if len(user["recent_slots"]) > 10:
        user["recent_slots"] = user["recent_slots"][-10:]
    
    save_users(users_data)

    result_text = f"Won: {cash_emoji} {win:,}" if win else "Lost"
    # Build plain text result
    result_lines = [
        f"════╗ **SLOT** | SAVAGE BET: {amt:,}",
        f"    ╔════════════════════╗",
        f"    ║ {final[0]} {final[1]} {final[2]} ║",
        f"    ╚════════════════════╝",
        f"════╝  {result_text}"
    ]
    await msg.edit(content="\n".join(result_lines))

@slot.error
async def slot_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Wait {error.retry_after:.0f}s before spinning again!")
