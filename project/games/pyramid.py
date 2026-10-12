#Pyramid command 5x5 Game
"""Pyramid game command."""

import random
import re
import time
from typing import TYPE_CHECKING, Any

import discord

from commands import _legacy_command

if TYPE_CHECKING:
    bot: Any
    savage_cash_emoji: str
    configured_bomb_emoji: str
    configured_green_flag_emoji: str
    configured_pyramid_emoji: str
    get_user_data: Any
    load_users: Any
    save_user_data: Any
    save_users: Any


# pyramid command
@_legacy_command
async def pyramid(ctx, amount: str = None):
    """
    Pyramid 5x5: 5 levels, each with 5 buttons (2 safe, 3 bombs). Survive all 5 levels to win 3x your bet!
    Usage: !pyramid <amount>
    """
    max_bet = 200_000
    min_bet = 100

    # Cooldown per user (60s)
    if not hasattr(bot, "pyramid_cooldowns"):
        bot.pyramid_cooldowns = {}
    user_id = ctx.author.id
    now = time.time()
    last = bot.pyramid_cooldowns.get(user_id, 0)
    cooldown = 60
    if now - last < cooldown:
        wait = int(cooldown - (now - last))
        await ctx.send(f"⏳ Wait {wait}s before playing Pyramid again.")
        return
      
    # Validate amount
    users_data = load_users()
    user = get_user_data(users_data, ctx.author.id, ctx.guild.id)
    economy = user.get('economy', {})
    user_cash = economy.get('cash', 0)
    if amount is None:
        await ctx.send(f"Usage: `!pyramid <amount>` (min {min_bet})")
        return
    def _parse_bet(raw):
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
    bet = _parse_bet(amount)
    if bet is None:
        await ctx.send("Invalid amount. Use a number like 10000 or 10k, or 'all'.")
        return

    if bet < min_bet:
        await ctx.send(f"Minimum bet is {min_bet}.")
        return
    if bet > user_cash:
        await ctx.send("You don't have enough cash to bet that amount.")
        return
    if bet > max_bet:
        bet = max_bet

    # Deduct bet
    economy['cash'] = economy.get('cash', 0) - bet
    save_users(users_data)
    bot.pyramid_cooldowns[user_id] = now

    # Use Discord application emojis
    cash_emoji = savage_cash_emoji
    safe_emoji = "🟩"
    bomb_emoji = configured_bomb_emoji or "💣"
    step_emoji = configured_green_flag_emoji or "🟩"
    pyramid_emoji = configured_pyramid_emoji or "🔺"

    class Pyramid5View(discord.ui.View):
        def __init__(self, bet, level=0, safe_indices=None, timeout=60):
            super().__init__(timeout=timeout)
            self.bet = bet
            self.level = level
            # For each level, pick 2 safe indices, rest are bombs (randomized each level)
            self.safe_indices = safe_indices or [sorted(random.sample(range(5), 2)) for _ in range(5)]
            self.active = True
            self.message = None
            self.disable_all = False
            self.make_buttons()

        async def interaction_check(self, interaction):
            return interaction.user == ctx.author

        async def on_timeout(self):
            self.disable_all = True
            self.make_buttons()
            if self.message:
                try:
                    await self.message.edit(content="⏰ Timed out! Game ended.", view=self)
                except Exception:
                    pass

        def make_buttons(self):
            self.clear_items()
            for i in range(5):
                # Use emoji object directly instead of string label
                btn = discord.ui.Button(
                    emoji=step_emoji,
                    label=f"{i+1}",
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"pyramid5_{self.level}_{i}",
                    row=0,
                    disabled=self.disable_all
                )
                # Attach the callback with the correct index
                async def callback(interaction, idx=i, v=self):
                    await v.button_callback(interaction, idx)
                btn.callback = callback
                self.add_item(btn)

        async def button_callback(self, interaction, idx):
            if not self.active or self.disable_all:
                try:
                    await interaction.response.send_message("Game is over!", ephemeral=True)
                except discord.InteractionResponded:
                    pass
                return
            safe_idx = self.safe_indices[self.level]
            # If not safe, it's a bomb (randomized each level)
            if idx in safe_idx:
                self.level += 1
                if self.level == 5:
                    payout = int(self.bet * 3)
                    economy['cash'] = economy.get('cash', 0) + payout
                    save_user_data(user, ctx.author.id, ctx.guild.id)
                    embed = discord.Embed(
                        title=f"{pyramid_emoji} Pyramid 5x5 Winner!",
                        description=f"🏆 You survived all 5 levels!\n{cash_emoji} **You won {payout}!**",
                        color=discord.Color.green()
                    )
                    self.active = False
                    self.disable_all = True
                    self.make_buttons()
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    # Respawn new view for next level to avoid "This interaction failed"
                    new_view = Pyramid5View(self.bet, self.level, self.safe_indices)
                    new_view.message = self.message
                    embed = discord.Embed(
                        title=f"{pyramid_emoji} Pyramid 5x5 - Level {self.level+1}/5",
                        description=f"{safe_emoji} Safe! Advance to the next level.\nPick a button (2 safe, 3 bombs).",
                        color=discord.Color.orange()
                    )
                    await interaction.response.edit_message(embed=embed, view=new_view)
            else:
                embed = discord.Embed(
                    title=f"{bomb_emoji} Pyramid 5x5 - Bomb!",
                    description=f"💀 You hit a bomb at level {self.level+1} and lost your bet of {cash_emoji} `{self.bet}`!",
                    color=discord.Color.red()
                )
                self.active = False
                self.disable_all = True
                self.make_buttons()
                await interaction.response.edit_message(embed=embed, view=self)

    # Send the initial view
    embed = discord.Embed(
        title=f"{pyramid_emoji} Pyramid 5x5 - Level 1/5",
        description=f"Pick a button (2 safe, 3 bombs).",
        color=discord.Color.orange()
    )
    view = Pyramid5View(bet)
    msg = await ctx.send(embed=embed, view=view)
    view.message = msg