# rob command game (updated: 6 hour cooldown, steal 5-15% of cash, same-server requirement, not from bank)
"""Robbery game command."""

import random
import time
from typing import TYPE_CHECKING, Any

import discord

from commands import _legacy_command

if TYPE_CHECKING:
    bot: Any
    savage_cash_emoji: str
    get_user_data: Any
    load_users: Any
    save_users: Any


# rob command
# Rob cooldowns now part of users data in SQLite

def load_rob_cooldowns():
    """Load rob cooldowns from SQLite users data"""
    users_data = load_users()
    return users_data.get("rob_cooldowns", {})

def save_rob_cooldowns(data):
    """Save rob cooldowns to SQLite users data"""
    users_data = load_users()
    users_data["rob_cooldowns"] = data
    save_users(users_data)

def _format_seconds(sec: int) -> str:
    days, rem = divmod(sec, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or (days and (minutes or seconds)):
        parts.append(f"{hours}h")
    if minutes or (hours and seconds):
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)

@_legacy_command
async def rob(ctx, member: discord.Member = None):
    """Rob another user! Steals a random 5-15% of target's cash. 6 hour cooldown after any attempt.
    Both users must be in the same server where the command is used. Cannot steal from bank.
    If the target has an active shield (shield or goldshield) no one can rob them until it expires.
    """
    # Command must be used in a guild
    if ctx.guild is None:
        embed = discord.Embed(
            description="This command can only be used in a server channel.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return

    if member is None:
        embed = discord.Embed(
            description="Usage: `!rob @user`",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return

    # Basic checks
    if member.bot:
        embed = discord.Embed(
            description="You can't rob bots.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return
    if member == ctx.author:
        embed = discord.Embed(
            description="You can't rob yourself.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return

    # Ensure target is a member of the same guild where command is used
    if getattr(member, "guild", None) is None or member.guild.id != ctx.guild.id:
        embed = discord.Embed(
            description="You can only rob users who are in this server.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return

    # Load data
    users_data = load_users()
    user = get_user_data(users_data, ctx.author.id, ctx.guild.id)
    target = get_user_data(users_data, member.id, ctx.guild.id)

    # Cooldown system: 6 hours (21600 seconds) after any attempt (success or fail)
    COOLDOWN = 6 * 3600
    rob_cooldowns = load_rob_cooldowns()
    now = int(time.time())
    expiry = int(rob_cooldowns.get(str(ctx.author.id), 0))
    if now < expiry:
        left = expiry - now
        embed = discord.Embed(
            description=f"⏳ You must wait { _format_seconds(left) } before attempting to rob again.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return

    # Every valid robbery attempt starts the cooldown, including protected targets.
    rob_cooldowns[str(ctx.author.id)] = now + COOLDOWN
    save_rob_cooldowns(rob_cooldowns)

    # Check protection shields on the target (they block rob attempts while active)
    timers = target.get("bottle_timers", {}) or {}
    # Shield ids expected: "gold_shield" and "s_shield"
    for shield_id, shield_name in (("gold_shield", "Gold Shield"), ("s_shield", "Shield")):
        try:
            expires = int(timers.get(str(shield_id), 0))
        except Exception:
            expires = 0
        if expires > now:
            left = expires - now
            embed = discord.Embed(
                description=(
                    f"🛡️ {member.display_name} is protected by **{shield_name}** for { _format_seconds(left) }.\n"
                    f"You cannot rob them while it's active."
                ),
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            return

    # Can't steal from bank; work only with 'cash'
    target_cash = int(target.get('economy', {}).get('cash', 0))
    if target_cash <= 0:
        # Still apply cooldown for wasting an attempt
        rob_cooldowns[str(ctx.author.id)] = now + COOLDOWN
        save_rob_cooldowns(rob_cooldowns)
        embed = discord.Embed(
            description=f"🎮 {member.display_name} has no cash to steal. You still have a cooldown of 6 hours.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return

    # Emojis
    bounty_emoji = savage_cash_emoji
    rob_emoji = "🎮"

    # Success chance (keep some skill/luck factor) - use 40% success as before
    success = random.random() < 0.4

    # Compute steal amount: random percent between 5% and 15% of target's cash (integer, at least 1)
    perc = random.uniform(0.05, 0.15)
    amount = max(1, int(target_cash * perc))
    # Ensure we don't exceed target_cash
    amount = min(amount, target_cash)

    # Apply result and set cooldown (always 6 hours)
    if success and amount > 0:
        # Transfer only cash (not bank)
        user_economy = user.setdefault("economy", {})
        target_economy = target.setdefault("economy", {})
        user_economy["cash"] = user_economy.get("cash", 0) + amount
        target_economy["cash"] = target_economy.get("cash", 0) - amount
        save_users(users_data)
        embed = discord.Embed(
            description=f"{rob_emoji} {ctx.author.mention} successfully robbed {bounty_emoji} {amount} from {member.mention}! (6h cooldown)",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        try:
            await member.send(
                f"You were robbed by {ctx.author.name} for {bounty_emoji} {amount:,} "
                f"in **{ctx.guild.name}**."
            )
        except discord.Forbidden:
            pass
    else:
        # Failed attempt - no transfer, but cooldown already applied
        embed = discord.Embed(
            description=f"{rob_emoji} {ctx.author.mention} tried to rob {member.mention} and *Failed*! | 6h cooldown",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
