"""Crime game command."""

import random
import time
from typing import TYPE_CHECKING, Any

import discord

from commands import _legacy_command

if TYPE_CHECKING:
    WeightedRNG: Any
    get_user_data: Any
    load_users: Any
    save_users: Any
    savage_cash_emoji: str


# crime game
CRIME_JAIL_TIME = 10 * 60  # 10 minutes in seconds
CRIME_COOLDOWN_TIME = 5 * 60  # 5 minutes in seconds

def load_crime_jail():
    users_data = load_users()
    return users_data.get("crime_jail", {})

def save_crime_jail(data):
    users_data = load_users()
    users_data["crime_jail"] = data
    save_users(users_data)

def load_crime_cooldown():
    users_data = load_users()
    return users_data.get("crime_cooldowns", users_data.get("crime_cooldown", {}))

def save_crime_cooldown(data):
    users_data = load_users()
    users_data["crime_cooldowns"] = data
    save_users(users_data)

CRIME_SUCCESS_DIALOGS = [
    "You pulled off the heist like a boss! 💸",
    "Swag! You outsmarted everyone and got away with the loot.",
    "Aura on max! You made it look easy.",
    "You left no trace. The city whispers your name.",
    "Smooth criminal! You earned your cash in style."
]

CRIME_FAIL_DIALOGS = [
    "You tripped the alarm and got caught. Oops!",
    "The cops were waiting for you. Better luck next time.",
    "You dropped your wallet at the scene. Rookie mistake!",
    "Someone snitched on you. Crime doesn't pay today.",
    "You forgot your mask and everyone saw your face!"
]

CRIME_JAIL_GIF = "https://github.com/Savage404E/images-for-bot/blob/main/61460707a482e441a2ebe7deebf74c99.gif?raw=true"

@_legacy_command
async def crime(ctx):
    if ctx.guild is None:
        await ctx.send("This command can only be used in a server.")
        return

    jail_data = load_crime_jail()
    cooldown_data = load_crime_cooldown()
    user_id = str(ctx.author.id)
    now = int(time.time())
    
    # Bypass for specific user ID
    BYPASS_USER_ID = "15118435360309248"

    # Check jail status (with bypass)
    if user_id in jail_data and user_id != BYPASS_USER_ID:
        jail_until = jail_data[user_id]
        if now < jail_until:
            left = jail_until - now
            mins, secs = divmod(left, 60)
            embed = discord.Embed(
                title="🚨 Jailed!",
                description=f"You are in jail for another `{mins}m {secs}s` and cannot use game commands.",
                color=discord.Color.red()
            )
            embed.set_image(url=CRIME_JAIL_GIF)
            await ctx.send(embed=embed)
            return
        else:
            del jail_data[user_id]
            save_crime_jail(jail_data)

    # Check cooldown
    if user_id in cooldown_data:
        cooldown_until = cooldown_data[user_id]
        if now < cooldown_until:
            left = cooldown_until - now
            mins, secs = divmod(left, 60)
            embed = discord.Embed(
                title="⏳ Cooldown!",
                description=f"You must wait `{mins}m {secs}s` before committing another crime.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        else:
            del cooldown_data[user_id]
            save_crime_cooldown(cooldown_data)

    # Enhanced weighted crime outcomes with user performance tracking
    users_data = load_users()
    user = get_user_data(users_data, ctx.author.id, ctx.guild.id)
    
    # Get user's recent crime performance
    recent_crimes = user.get("recent_crimes", [])
    if len(recent_crimes) >= 5:
        recent_success_rate = sum(recent_crimes[-5:]) / 5
    else:
        recent_success_rate = 0.4  # Default to 40% if not enough data
    
    # Define weighted outcomes with adaptive probabilities
    base_outcomes = {
        "win": {"weight": 40, "amount_range": (200, 5000), "dialog_type": "success"},
        "fine": {"weight": 35, "amount_range": (100, 3000), "dialog_type": "fail"},
        "jail": {"weight": 25, "amount_range": None, "dialog_type": "jail"}
    }
    
    # Adjust weights based on recent performance
    if recent_success_rate > 0.6:  # User winning too much
        base_outcomes["win"]["weight"] = 30
        base_outcomes["fine"]["weight"] = 40
        base_outcomes["jail"]["weight"] = 30
    elif recent_success_rate < 0.2:  # User losing too much
        base_outcomes["win"]["weight"] = 50
        base_outcomes["fine"]["weight"] = 30
        base_outcomes["jail"]["weight"] = 20
    
    # Select outcome using weighted RNG
    outcomes = list(base_outcomes)
    weights = [base_outcomes[outcome_name]["weight"] for outcome_name in outcomes]
    outcome = WeightedRNG.weighted_choice(outcomes, weights)
    
    # Generate amount based on outcome
    if base_outcomes[outcome]["amount_range"]:
        min_amount, max_amount = base_outcomes[outcome]["amount_range"]
        # Higher amounts for wins, lower for fines
        if outcome == "win":
            amount = random.randint(min_amount, max_amount)
        else:  # fine
            amount = random.randint(min_amount, max_amount)
    else:
        amount = 0
    
    if outcome == "win":
        economy = user.setdefault("economy", {})
        economy["cash"] = economy.get("cash", 0) + amount
        dialog = random.choice(CRIME_SUCCESS_DIALOGS)
        embed = discord.Embed(
            title="💰 Crime Success!",
            description=f"{dialog}\nYou earned **{amount}** cash!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        # Track success
        user.setdefault("recent_crimes", []).append(1)
    elif outcome == "fine":
        economy = user.setdefault("economy", {})
        fine = min(economy.get("cash", 0), amount)
        economy["cash"] = economy.get("cash", 0) - fine
        dialog = random.choice(CRIME_FAIL_DIALOGS)
        embed = discord.Embed(
            title="🚨 Crime Failed!",
            description=f"{dialog}\nYou got caught and fined **{fine}** cash!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        # Track failure
        user.setdefault("recent_crimes", []).append(0)
    else:
        jail_data[user_id] = now + CRIME_JAIL_TIME
        save_crime_jail(jail_data)
        embed = discord.Embed(
            title="🚓 Crime Failed! Jailed!",
            description="You got caught and are now in jail for **10 minutes**!",
            color=discord.Color.dark_red()
        )
        embed.set_image(url=CRIME_JAIL_GIF)
        await ctx.send(embed=embed)
        # Track failure (jail)
        user.setdefault("recent_crimes", []).append(0)
    
    # Keep only last 10 crime results
    if len(user["recent_crimes"]) > 10:
        user["recent_crimes"] = user["recent_crimes"][-10:]
    
    save_users(users_data)

    # Set 5min cooldown after every attempt
    cooldown_data[user_id] = now + CRIME_COOLDOWN_TIME
    save_crime_cooldown(cooldown_data)

# Block jailed users from gambling commands
GAMBLING_COMMANDS_JAIL = {"coinflip", "cf", "roulette", "plinko", "pyramid", "pyramid5", "horse", "car", "carrace", "slot", "Slot"}

async def block_jail_gambling(ctx):
    # Only block for specific commands
    if ctx.command and ctx.command.name in GAMBLING_COMMANDS_JAIL:
        jail_data = load_crime_jail()
        user_id = str(ctx.author.id)
        now = int(time.time())
        # Bypass for specific user ID
        BYPASS_USER_ID = "15118435360309248"
        if user_id in jail_data and now < jail_data[user_id] and user_id != BYPASS_USER_ID:
            left = jail_data[user_id] - now
            mins, secs = divmod(left, 60)
            embed = discord.Embed(
                title="?? Jailed!",
                description=f"You are in jail for another `{mins}m {secs}s` and cannot use this command.",
                color=discord.Color.red()
            )
            embed.set_image(url=CRIME_JAIL_GIF)
            try:
                await ctx.send(embed=embed)
            except Exception:
                pass
            return False
    return True


# work cmd
WORK_COOLDOWN_TIME = 10 * 60
WORK_DAILY_LIMIT = 12
WORK_SCENARIOS = [
    "You delivered a package across town.",
    "You helped repair equipment at the mine.",
    "You cleaned up the docks after a busy day.",
    "You helped a shopkeeper restock their shelves.",
    "You carried supplies to the city guards.",
]


@_legacy_command
async def work(ctx):
    """Complete a short job to earn a little cash."""
    if ctx.guild is None:
        await ctx.send("This command can only be used in a server.")
        return

    users_data = load_users()
    user_id = str(ctx.author.id)
    now = int(time.time())
    day_id = now // 86400
    work_data = users_data.setdefault("work_data", {})
    work_state = work_data.setdefault(user_id, {})

    if work_state.get("day") != day_id:
        work_state["day"] = day_id
        work_state["count"] = 0

    if work_state.get("count", 0) >= WORK_DAILY_LIMIT:
        await ctx.send("You have finished your 8 shifts for today. Come back tomorrow!")
        return

    cooldown_until = int(work_state.get("cooldown_until", 0))
    if now < cooldown_until:
        left = cooldown_until - now
        minutes, seconds = divmod(left, 60)
        await ctx.send(f"You can work again in {minutes}m {seconds}s.")
        return

    user = get_user_data(users_data, ctx.author.id, ctx.guild.id)
    amount = random.randint(100, 2000)
    economy = user.setdefault("economy", {})
    economy["cash"] = economy.get("cash", 0) + amount
    work_state["count"] = work_state.get("count", 0) + 1
    work_state["cooldown_until"] = now + WORK_COOLDOWN_TIME
    save_users(users_data)

    embed = discord.Embed(
        title="🌟🛠️ WORK SHIFT COMPLETE! 🛠️🌟",
        description=(
            f"🎯 **Today's job:** {random.choice(WORK_SCENARIOS)}\n\n"
            f"🎉💸 You earned **{amount:,}** {savage_cash_emoji}!\n"
            f"⏰ Your next shift is available in **10 minutes**.\n"
            f"🔥 Shifts completed today: **{work_state['count']}/{WORK_DAILY_LIMIT}**"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text="Keep grinding and stack that cash! 💪✨")
    await ctx.send(embed=embed)

