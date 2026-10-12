#mine command
"""Mines game command."""

import builtins
import random
import re
import time
from typing import TYPE_CHECKING, Any

import discord

from commands import _legacy_command

savage_cash_emoji = getattr(builtins, "savage_cash_emoji", "🎮")

if TYPE_CHECKING:
    bot: Any
    savage_cash_emoji: str
    get_user_data: Any
    load_users: Any
    save_users: Any


# add for cooldown tracking

GRID_SIZE = 5
DEFAULT_MINES = 3

#Stepped multiplier schedule (start low, ramp to 3x max)
#thresholds are number of safe cells opened
MULTIPLIER_SCHEDULE = [
    (0, 0.0),
    (1, 0.20),
    (3, 0.50),
    (5, 0.80),
    (7, 1.00),
    (9, 1.30),
    (11, 1.50),
    (13, 1.70),
    (15, 2.00),
    (16, 2.20),
    (18, 2.40),
    (19, 2.60),
    (20, 2.80),
    (21, 3.00),
]

def get_cash_emoji():
    return getattr(builtins, "savage_cash_emoji", savage_cash_emoji)

active_games = {}  # user_id -> GameState
mines_cooldowns = {}  # user_id -> last command timestamp (seconds)

class GameState:
    def __init__(self, bet: int, mines: int):
        self.bet = bet
        self.mines = mines
        self.revealed = set()
        self.alive = True
        self.paused = False  # Track pause state

        cells = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)]
        self.mine_cells = set(random.sample(cells, mines))

    @property
    def safe_count(self):
        return GRID_SIZE * GRID_SIZE - self.mines

    @property
    def hits(self):
        return len(self.revealed)

    def is_mine(self, row, col):
        return (row, col) in self.mine_cells

    def current_multiplier(self):
        m = 1.0
        for threshold, mult in MULTIPLIER_SCHEDULE:
            if self.hits >= threshold:
                m = mult
            else:
                break
        return m

    def current_winnings(self):
        return int(self.bet * self.current_multiplier())


class MinesView(discord.ui.View):
    def __init__(self, user: discord.User, game: GameState):
        super().__init__(timeout=120)
        self.user = user
        self.game = game

        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                self.add_item(CellButton(r, c))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id

    async def on_timeout(self):
        """Pause the game instead of ending it on timeout."""
        if self.game:
            self.game.paused = True
        for child in self.children:
            child.disabled = True

    async def end_game_message(self, interaction: discord.Interaction, text: str):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=text, view=self)
        self.stop()


class CellButton(discord.ui.Button):
    def __init__(self, row, col):
        super().__init__(style=discord.ButtonStyle.secondary,
                         label="⬛",
                         row=row,
                         custom_id=f"cell_{row}_{col}")
        self.row = row
        self.col = col

    async def callback(self, interaction: discord.Interaction):
        game: GameState = active_games.get(interaction.user.id)
        view: MinesView = self.view

        if not game or not game.alive:
            await interaction.response.send_message("No active game.", ephemeral=True)
            return

        if (self.row, self.col) in game.revealed:
            await interaction.response.send_message("Already opened.", ephemeral=True)
            return

        if game.is_mine(self.row, self.col):
            game.alive = False
            self.style = discord.ButtonStyle.danger
            self.label = "💣"

            for child in view.children:
                if isinstance(child, CellButton) and game.is_mine(child.row, child.col):
                    child.style = discord.ButtonStyle.danger
                    child.label = "💣"

            # Track loss for anti-streak protection
            users_data = load_users()
            user = get_user_data(users_data, interaction.user.id, interaction.guild.id if interaction.guild else None)
            user.setdefault("recent_mines", []).append(0)  # Loss
            if len(user["recent_mines"]) > 10:
                user["recent_mines"] = user["recent_mines"][-10:]
            save_users(users_data)

            await view.end_game_message(
                interaction,
                f"💥 You hit a mine and lost your bet of {game.bet} coins."
            )
            active_games.pop(interaction.user.id, None)
            return

        game.revealed.add((self.row, self.col))
        self.style = discord.ButtonStyle.success
        self.label = "✅"

        winnings = game.current_winnings()
        cash_emoji = get_cash_emoji()
        text = (
            f"Safe spot! Current multiplier: **{game.current_multiplier():.2f}x**\n"
            f"Potential cashout: **{winnings}** {cash_emoji}\n"
            f"Opened: {game.hits}/{game.safe_count} safe cells."
        )

        await interaction.response.edit_message(content=text, view=view)


class CashoutButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success,
                         label="Cash Out",
                         row=0)

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        game: GameState = active_games.get(user_id)
        # Cash out against the active game; also disable the grid view if present
        if not game or not game.alive:
            await interaction.response.send_message("No active game.", ephemeral=True)
            return
        
        win = game.current_winnings()
        # Use main economy system
        users_data = load_users()
        user = get_user_data(users_data, user_id, interaction.guild.id if interaction.guild else None)
        user.setdefault("economy", {})["cash"] = user["economy"].get("cash", 0) + win
        save_users(users_data)
        
        # Track mines performance for anti-streak protection
        user.setdefault("recent_mines", []).append(1 if win > 0 else 0)
        if len(user["recent_mines"]) > 10:
            user["recent_mines"] = user["recent_mines"][-10:]
        
        game.alive = False
        active_games.pop(user_id, None)
        
        # Disable the grid view if it exists
        grid_view = mines_views.get(user_id)
        if grid_view and hasattr(grid_view, "message") and grid_view.message:
            for child in grid_view.children:
                child.disabled = True
            try:
                cash_emoji = get_cash_emoji()
                await grid_view.message.edit(content=f"✅ You cashed out **{win}** {cash_emoji}", view=grid_view)
            except Exception:
                pass
        
        # Disable this cashout button and respond
        self.disabled = True
        try:
            cash_emoji = get_cash_emoji()
            await interaction.response.send_message(f"✅ You have cashed out successfully!\n💰 Winnings: **{win}** {cash_emoji}")
        except discord.InteractionResponded:
            await interaction.followup.send(f"✅ You have cashed out successfully!\n💰 Winnings: **{win}** {cash_emoji}")
        
        try:
            await interaction.message.edit(view=self.view)
        except Exception:
            pass


class CashoutView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(CashoutButton())


mines_views = {}

@_legacy_command
async def mine(ctx, amount: str = None):
    """Start a Mines game with a bet amount and 3 mines. Resume paused game if one exists."""
    user_id = ctx.author.id

    # Check for paused game and resume it
    if user_id in active_games:
        game = active_games[user_id]
        if game.paused and game.alive:
            # Resume the paused game
            game.paused = False
            view = MinesView(ctx.author, game)
            grid_msg = await ctx.send(
                f"💣 Mines Game resumed!\nBet: **{game.bet}** | Mines: **{game.mines}**\nClick tiles to reveal safe spots, or cash out below.",
                view=view
            )
            view.message = grid_msg
            mines_views[user_id] = view
            cashout_view = CashoutView()
            await ctx.send("(cash out)", view=cashout_view)
            return
        elif game.alive:
            await ctx.send("You already have an active game.")
            return

    # Load user data first using main economy system
    users_data = load_users()
    user = get_user_data(users_data, user_id, ctx.guild.id if ctx.guild else None)
    balance = user.get("economy", {}).get("cash", 0)

    # Ask for bet amount if not provided
    if amount is None:
        await ctx.send(f"💰 How much cash do you want to bet? (You have **{balance}** cash)\nExample: `smine 50000` or `smine 50k`")
        return

    # Parse the bet amount
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

    bet_amt = _parse_amount(amount)
    if bet_amt is None:
        await ctx.send("Invalid amount! Use a number like 10000 or 10k, or 'all'.")
        return

    if bet_amt <= 0:
        await ctx.send("Bet amount must be positive!")
        return

    if bet_amt > balance:
        await ctx.send(f"You don't have enough cash! You have **{balance}** cash.")
        return

    # 30-second cooldown check
    now = time.time()
    last = mines_cooldowns.get(user_id, 0)
    cooldown = 30  # 30 seconds
    if now - last < cooldown:
        wait = int(cooldown - (now - last))
        await ctx.send(f"⏳ Wait {wait}s before playing Mines again.")
        return

    # Use fixed 3 mines
    mines = DEFAULT_MINES

    # Add anti-streak protection for mine placement
    recent_mines = user.get("recent_mines", [])
    if len(recent_mines) >= 5:
        recent_win_rate = sum(recent_mines[-5:]) / 5
    else:
        recent_win_rate = 0.5  # Default to 50% if not enough data
    
    # Adjust mine count based on recent performance
    adjusted_mines = mines
    if recent_win_rate > 0.7:  # User winning too much
        adjusted_mines = min(mines + 1, 8)  # Add more mines, max 8
    elif recent_win_rate < 0.3:  # User losing too much
        adjusted_mines = max(mines - 1, 1)  # Remove mines, min 1
    
    # Deduct bet and set cooldown
    user.setdefault("economy", {})["cash"] -= bet_amt
    save_users(users_data)
    mines_cooldowns[user_id] = now

    game = GameState(bet_amt, adjusted_mines)
    active_games[user_id] = game

    view = MinesView(ctx.author, game)
    grid_msg = await ctx.send(
        f"💣 Mines Game started!\nBet: **{bet_amt}** | Mines: **{adjusted_mines}**\nClick tiles to reveal safe spots, or cash out below.",
        view=view
    )
    # Track the grid view to allow disabling on cashout
    view.message = grid_msg
    mines_views[user_id] = view
    # Send cashout control in a separate view to keep 25-cell grid intact
    cashout_view = CashoutView()
    await ctx.send("(cash out)", view=cashout_view)