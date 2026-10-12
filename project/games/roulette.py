#Roulette command
"""ouletteR game command."""

import asyncio
import random
import re
import time
from typing import TYPE_CHECKING, Any

import discord

from commands import _legacy_command

if TYPE_CHECKING:
    bot: Any
    get_user_data: Any
    load_users: Any
    save_users: Any


class RouletteBetModal(discord.ui.Modal):
    def __init__(self, ctx, bet, *, number_required=False):
        super().__init__(title="Roulette Bet")
        self.ctx = ctx
        self.bet = bet
        self.number_required = number_required
        if number_required:
            self.number = discord.ui.TextInput(
                label="Number (0-36)",
                placeholder="Enter a number from 0 to 36",
                required=True,
                max_length=2,
            )
            self.add_item(self.number)
        self.amount = discord.ui.TextInput(
            label="Bet amount",
            placeholder="Enter amount, e.g. 1000 or 10k",
            required=True,
            max_length=12,
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        bet = self.bet
        if self.number_required:
            bet = self.number.value.strip()
        await interaction.response.defer()
        await Roulette(self.ctx, bet, self.amount.value.strip())


class RouletteChoiceView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the roulette player can use these buttons.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Red", style=discord.ButtonStyle.danger, emoji="🔴")
    async def red(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RouletteBetModal(self.ctx, "red"))

    @discord.ui.button(label="Black", style=discord.ButtonStyle.secondary, emoji="⚫")
    async def black(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RouletteBetModal(self.ctx, "black"))

    @discord.ui.button(label="Number", style=discord.ButtonStyle.success, emoji="🔢")
    async def number(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RouletteBetModal(self.ctx, "number", number_required=True))


# roulette command
@_legacy_command
async def Roulette(ctx, bet: str = None, amount: str = None, gif: str = None):
    """
    Play Roulette Bet on red/black/green or a number (0-36).
    Payouts: 2x for color, 4x for green (0), 20x for number.
    Usage: roulette <red/black/green/number(0-36)> <amount> 
    """
    max_bet = 300_000
    min_bet = 1

    # --- 30s cooldown per user ---
    if not hasattr(bot, "roulette_cooldowns"):
        bot.roulette_cooldowns = {}
    user_id = ctx.author.id
    now = time.time()
    last = bot.roulette_cooldowns.get(user_id, 0)
    cooldown = 30
    if now - last < cooldown:
        wait = int(cooldown - (now - last))
        await ctx.send(f"⏳ Wait {wait}s before playing roulette again.")
        return
    if bet is None and amount is None:
        await ctx.send(
            "🎰 **Choose your roulette bet**\nSelect Red, Black, or Number below.",
            view=RouletteChoiceView(ctx),
        )
        return
    if bet is None or amount is None:
        await ctx.send("Usage: `!roulette <red/black/green/number> <amount> [gif_url]`")
        return

    # Validate amount
    users_data = load_users()
    user = get_user_data(users_data, ctx.author.id, ctx.guild.id)
    user_cash = user.get('economy', {}).get('cash', 0)
    def _parse_wager(raw):
        s = str(raw).strip().lower()
        if s == "all":
            return min(user_cash, max_bet)
        m = re.match(r"^(\d+)\s*([kK]?)$", s)
        if not m:
            return None
        base = int(m.group(1))
        if m.group(2):
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

    # Roulette wheel setup
    red_numbers = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
    black_numbers = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}
    green_number = 0

    # Parse bet
    bet_type = None
    bet_number = None
    bet_lower = bet.lower()
    if bet_lower in ["red", "r"]:
        bet_type = "red"
    elif bet_lower in ["black", "b"]:
        bet_type = "black"
    elif bet_lower in ["green", "g"]:
        bet_type = "green"
    else:
        try:
            bet_number = int(bet)
            if not (0 <= bet_number <= 36):
                await ctx.send("Number must be between 0 and 36.")
                return
            bet_type = "number"
        except ValueError:
            await ctx.send("Invalid bet. Use red, black, green, or a number 0-36.")
            return

    # Deduct bet
    user['economy']['cash'] -= wager
    save_users(users_data)

    # Animation: use your own GIF or a default one
    gif_url = gif or "https://cdn.discordapp.com/attachments/1384481743930790001/1387825412616487013/savage_Roulette.gif?ex=685ec0a2&is=685d6f22&hm=28f6fb63feac52cd4796486c6bc93b557b1ee0db99f4e3ef375d52eef9048707&"  # Replace with your own GIF if you want

    embed = discord.Embed(
        title="🎰 Roulette Spinning...",
        description=f"Bet: **{bet}** | Amount: **{wager}**\nSpinning the wheel...",
        color=discord.Color.blurple()
    )
    embed.set_image(url=gif_url)
    anim_msg = await ctx.send(embed=embed)
    await asyncio.sleep(7)  # Spinning for 7 seconds

    # Spin the wheel
    result = random.randint(0, 36)
    if result == 0:
        color = "green"
        color_emoji = "🟢"
    elif result in red_numbers:
        color = "red"
        color_emoji = "🔴"
    else:
        color = "black"
        color_emoji = "⚫"

    # Determine win/loss and payout
    payout = 0
    win = False
    if bet_type == "red" and color == "red":
        payout = wager * 1.5
        win = True
    elif bet_type == "black" and color == "black":
        payout = wager * 2
        win = True
    elif bet_type == "green" and color == "green":
        payout = wager * 3
        win = True
    elif bet_type == "number" and bet_number == result:
        payout = wager * 10
        win = True

    # Update cash if win
    if win:
        user['economy']['cash'] += payout
        save_users(users_data)

    # Show result in style
    style_win = f"🎉 **YOU WON!** {color_emoji} `{wager}` → `{payout}`!" if win else f"💀 **You lost!** {color_emoji} `{wager}`"
    result_embed = discord.Embed(
        title="🎰 Roulette Result",
        description=(
            f"Number: **{result}** {color_emoji}\n"
            f"Your bet: **{bet}**\n"
            f"{style_win}"
        ),
        color=discord.Color.green() if win else discord.Color.red()
    )
    result_embed.set_image(url=gif_url)
    await anim_msg.edit(embed=result_embed)