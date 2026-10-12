#plinko command
# Cooldown tracking for plinko
"""Plinko game command."""

import asyncio
import random
import re
import time
from typing import TYPE_CHECKING, Any

import discord

from commands import _legacy_command

if TYPE_CHECKING:
    bot: Any
    savage_cash_emoji: str
    configured_arrow_emoji: str
    configured_dot_emoji: str
    get_user_data: Any
    load_users: Any
    save_users: Any


# plinko command
def load_plinko_cooldown():
    users_data = load_users()
    return users_data.get("plinko_cooldowns", {})

def save_plinko_cooldown(data):
    users_data = load_users()
    users_data["plinko_cooldowns"] = data
    save_users(users_data)

@_legacy_command
async def plinko(ctx, amount: str):
    """Play Plinko with your cash."""
    # Use main economy data file
    users_data = load_users()
    user = get_user_data(users_data, ctx.author.id, ctx.guild.id)
    user_id = str(ctx.author.id)
    balance = user.get('economy', {}).get('cash', 0)

    # Check cooldown
    cooldown_data = load_plinko_cooldown()
    current_time = time.time()
    if user_id in cooldown_data:
        cooldown_end = cooldown_data[user_id]
        if current_time < cooldown_end:
            remaining = int(cooldown_end - current_time)
            await ctx.send(f"⏰ You need to wait {remaining}s before playing Plinko again!")
            return
    
    # Use Discord application emojis by ID; no guild lookup is required.
    plinko_emoji = "🎰"
    arrow1 = configured_arrow_emoji or "🎮"
    dot = configured_dot_emoji or "🎮"
    ball = "🔵"
    peg = "⚫"
    star = "⭐"
    cash_emoji = savage_cash_emoji

    # Validate amount with support for 'k' suffix and 'all'
    def _parse_amount(raw):
        s = str(raw).strip().lower()
        if s == "all":
            return min(balance, 250000)
        m = re.match(r"^(\d+)\s*([kK]?)$", s)
        if not m:
            return None
        base = int(m.group(1))
        if m.group(2):
            base *= 1000
        return base
    amount_int = _parse_amount(amount)
    if amount_int is None:
        await ctx.send("Invalid amount! Use a number like 10000 or 10k, or 'all'.")
        return

    if amount_int <= 0:
        await ctx.send("Amount must be positive!")
        return

    if amount_int > balance:
        await ctx.send("You don't have enough cash!")
        return

    if amount_int > 250000:
        amount_int = 250000

    # Define Plinko board configuration
    ROWS = 8
    COLS = 9
    MULTIPLIERS = [0.0, 0.25, 0.5, 1.5, 2.0, 1.5, 0.5, 0.25, 0.0]

    # Create initial board display
    board = [[peg for _ in range(COLS)] for _ in range(ROWS)]
    position = COLS // 2
    board[0][position] = ball  # Starting position

    def board_to_string():
        board_str = ""
        for row in board:
            board_str += "".join(row) + "\n"
        return board_str

    # Create initial embed
    embed = discord.Embed(
        title=f"{plinko_emoji} Plinko Result",
        color=discord.Color.blurple()
    )
    embed.add_field(name="Final Board", value=board_to_string(), inline=False)

    # Deduct bet amount
    user['economy']['cash'] -= amount_int
    save_users(users_data)

    message = await ctx.send(embed=embed)

    # Simulate ball drop
    path = [(0, position)]

    for row in range(ROWS - 1):
        # Clear previous ball position
        for r in range(ROWS):
            for c in range(COLS):
                if board[r][c] == ball:
                    board[r][c] = peg

        # Move ball
        move = random.choice([-1, 1])
        position = max(0, min(COLS - 1, position + move))
        path.append((row + 1, position))

        # Place stars on all previous positions
        for prev_row, prev_pos in path[:-1]:
            board[prev_row][prev_pos] = star

        # Place current ball
        board[row + 1][position] = ball

        embed.set_field_at(0, name="Final Board", value=board_to_string(), inline=False)
        await message.edit(embed=embed)
        await asyncio.sleep(0.7)

    # Calculate winnings
    final_multiplier = MULTIPLIERS[position]
    winnings = int(amount_int * final_multiplier)

    # Update balance with winnings
    user['economy']['cash'] += winnings
    save_users(users_data)

    # Set cooldown (30 seconds)
    cooldown_data[user_id] = current_time + 30
    save_plinko_cooldown(cooldown_data)

    # Determine result color and message
    if winnings > amount_int:
        color = discord.Color.green()
    elif winnings == amount_int:
        color = discord.Color.gold()
    else:
        color = discord.Color.red()

    # Create multiplier table
    mult_table = "| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |\n"
    mult_table += "1 & 9= 0.0x | 2 & 8= 0.25x\n"
    mult_table += "3 & 7=0.5x | 4 & 6= 1.5x\n"
    mult_table += "5 = 2.0x bet prize"

    # Final result embed
    result_embed = discord.Embed(
        title=f"{plinko_emoji} Plinko Result",
        color=color
    )
    result_embed.add_field(name="Final Board", value=board_to_string(), inline=False)
    result_embed.add_field(name="", value=mult_table, inline=False)
    result_embed.add_field(
        name="Results",
        value=(
            f"{arrow1}Final Position: {position + 1}\n"
            f"{dot}Multiplier: {final_multiplier}x\n"
            f"{dot}Won: {cash_emoji} {winnings} cash\n"
            f"{dot}New Balance: {cash_emoji} {user['economy']['cash']} cash"
        ),
        inline=False
    )

    await message.edit(embed=result_embed)