"""Horse-racing game command."""

import asyncio
import random
import re
import time
from typing import TYPE_CHECKING, Any

import discord

from commands import _legacy_command

if TYPE_CHECKING:
    WeightedRNG: Any
    bot: Any
    configured_red_flag_emoji: str
    savage_cash_emoji: str
    get_user_data: Any
    load_users: Any
    save_user_data: Any
    save_users: Any


# horse command
@_legacy_command
async def horse(ctx, amount: str = None, horse_number: int = None):
    """
    !horse <cash 1-300000> <horse_number 1-10>
    Play a horse racing game with 10 horses. If your horse wins, earn 2x your bet. If you lose, lose all your bet.
    50-50 win chance with server emojis. 10s cooldown per user.
    """
    max_bet = 300_000
    min_bet = 1
    num_horses = 10

    # --- 10s cooldown per user ---
    if not hasattr(bot, "horse_cooldowns"):
        bot.horse_cooldowns = {}
    user_id = ctx.author.id
    now = time.time()
    last = bot.horse_cooldowns.get(user_id, 0)
    cooldown = 10
    if now - last < cooldown:
        wait = int(cooldown - (now - last))
        await ctx.send(f"⏳ Wait {wait}s before playing horse race again.")
        return
    bot.horse_cooldowns[user_id] = now

    # Show horse names and numbers if not provided
    horse_names = [
        "Thunderbolt", "Shadow", "Blaze", "Majesty", "Storm", "Lucky", "Comet", "Flash", "Spirit", "Nova"
    ]
    emoji_server = bot.get_guild(1374726576742072371) or bot.get_guild(1374726576742072371)
    if emoji_server:
        horse_emojis = [
            discord.utils.get(emoji_server.emojis, name=f"sg_horse{i+1}") or "🐎"
            for i in range(num_horses)
        ]
    else:
        horse_emojis = ["🐎" for _ in range(num_horses)]
    horse_list = "\n".join([f"{i+1}. {horse_names[i]} |" for i in range(num_horses)])

    if amount is None or horse_number is None:
        embed = discord.Embed(
            title="🏇 Horse Race - Choose Your Horse!",
            description=f"**Choose your horse and bet amount!**\n\n{horse_list}\n\nUsage: `!horse <cash 1-300000> <horse_number 1-10>`\nYou have 30 seconds to choose.",
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)
        return
    def _parse_amount(raw):
        s = str(raw).strip().lower()
        m = re.match(r"^(\d+)\s*([kK]?)$", s)
        if not m:
            return None
        base = int(m.group(1))
        if m.group(2):
            base *= 1000
        return base
    amount_int = _parse_amount(amount)
    if amount_int is None:
        await ctx.send("Invalid amount. Use a number like 10000 or 10k.")
        return
    if not (min_bet <= amount_int <= max_bet):
        await ctx.send(f"Bet must be between {min_bet} and {max_bet}.")
        return
    if not (1 <= horse_number <= num_horses):
        await ctx.send(f"Horse number must be between 1 and {num_horses}.")
        return

    # Load user data
    users_data = load_users()
    user = get_user_data(users_data, ctx.author.id, ctx.guild.id)
    user_cash = user.get("economy", {}).get("cash", 0)
    if user_cash < amount_int:
        await ctx.send("You don't have enough cash to bet that amount.")
        return
    user["economy"]["cash"] -= amount_int
    save_users(users_data)

    finish_emoji = configured_red_flag_emoji or "🚩"
    cash_emoji = savage_cash_emoji

    # Race setup - 50-50 win chance
    track_length = 10
    positions = [0] * num_horses
    winner = None

    def render_track():
        lines = []
        for i in range(num_horses):
            horse = horse_emojis[i]
            pos = positions[i]
            left_dashes = "—" * max(0, pos)
            right_dashes = "—" * max(0, track_length - pos)
            track = left_dashes + horse + right_dashes
            end = finish_emoji if pos >= track_length else ""
            lines.append(f"{i+1}. {horse_names[i]:<12} | {track}{end}")
        return "\n".join(lines)

    embed = discord.Embed(
        title="🏇 Horse Race!",
        description=f"Bet: {cash_emoji} {amount_int}\nYour horse: **{horse_names[horse_number-1]} ({horse_number})**\n\n{render_track()}",
        color=discord.Color.purple()
    )
    msg = await ctx.send(embed=embed)

    # Enhanced weighted win chance - determine winner before animation
    # Get user's recent horse race performance
    recent_horses = user.get("recent_horses", [])
    if len(recent_horses) >= 5:
        recent_win_rate = sum(recent_horses[-5:]) / 5
    else:
        recent_win_rate = 0.5  # Default to 50% if not enough data
    
    # Adaptive win probability based on recent performance
    base_win_chance = 0.5
    if recent_win_rate > 0.7:  # User winning too much
        win_chance = 0.35
    elif recent_win_rate < 0.3:  # User losing too much
        win_chance = 0.65
    else:
        win_chance = base_win_chance
    
    # Determine winner with weighted probability
    if random.random() < win_chance:
        winner = horse_number
    else:
        # Choose from other horses with weighted probabilities
        other_horses = [i for i in range(1, num_horses + 1) if i != horse_number]
        # Give some horses slightly better odds to make it more interesting
        horse_weights = []
        for horse in other_horses:
            # Higher numbered horses have slightly better odds
            weight = 1.0 + (horse - 1) * 0.1
            horse_weights.append(weight)
        
        winner = WeightedRNG.weighted_choice(other_horses, horse_weights)

    # Animate race
    while not any(positions[i] >= track_length for i in range(num_horses)):
        await asyncio.sleep(0.5)
        for i in range(num_horses):
            # Winner horse moves faster
            if i + 1 == winner:
                positions[i] += random.choice([2, 3])
            else:
                positions[i] += random.choice([0, 1])
        embed.description = f"Bet: {cash_emoji} {amount_int}\nYour horse: **{horse_names[horse_number-1]} ({horse_number})**\n\n{render_track()}"
        await msg.edit(embed=embed)

    # Result - update the same embed message instead of sending a second embed
    users_data = load_users()
    user = get_user_data(users_data, ctx.author.id, ctx.guild.id)
    if winner == horse_number:
        winnings = amount_int * 2
        user["economy"]["cash"] += winnings
        # Track win
        user.setdefault("recent_horses", []).append(1)
        result = f"🏆 {horse_names[winner-1]} ({winner}) wins!\n{ctx.author.mention} **WON** {cash_emoji} {winnings}!\n"
    else:
        # Track loss
        user.setdefault("recent_horses", []).append(0)
        result = f"🏆 {horse_names[winner-1]} ({winner}) wins!\n{ctx.author.mention} **LOST** {cash_emoji} {amount_int}!\n"
    
    # Keep only last 10 horse race results
    if len(user["recent_horses"]) > 10:
        user["recent_horses"] = user["recent_horses"][-10:]
    
    save_user_data(user, ctx.author.id, ctx.guild.id)
    
    color = discord.Color.green() if winner == horse_number else discord.Color.red()

    # Edit the original race message to show final result and full match track in the same embed
    embed.title = "🏇 Horse Race Result"
    embed.description = result + "\n\n" + render_track()
    embed.color = color
    await msg.edit(embed=embed)
    return