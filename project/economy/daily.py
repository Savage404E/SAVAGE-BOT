"""Daily reward command."""

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from commands import _legacy_command

if TYPE_CHECKING:
    bot: Any
    get_user_data: Any
    load_users: Any
    save_user_data: Any
    save_users: Any
    savage_cash_emoji: str
    load_badges: Any
    save_badges: Any

SERVER_DAILY_ROLE_BONUSES = {
    1365696441556926555: {
        "name": "𓆩𓆪 PREMIUM AURA 𓆪",
        "amount": 5000,
        "emoji": "🎮",
        "badge": "7",
    },
    1282802068569985024: {
        "name": "´ཀ` BOOSTER ´ཀ`",
        "amount": 10000,
        "emoji": "🎮",
        "badge": "6",
    },
    1554043997410959431: {
        "name": "𓆩𓆪 OG | SUBSCRIBERS 𓆪",
        "amount": 3000,
        "emoji": "🎮",
        "badge": "3",
    },
}

ROLE_BADGE_KEYS = {
    1365696441556926555: "7",
    1282802068569985024: "6",
    1554043997410959431: "3",
}


# daily system:
# Daily functions now use SQLite (part of users data)

def get_time_left(last_claim):
    try:
        now = datetime.now(timezone.utc)
        next_claim = datetime.fromisoformat(last_claim)
        if next_claim.tzinfo is None:
            next_claim = next_claim.replace(tzinfo=timezone.utc)
        next_claim += timedelta(hours=24)
    except (TypeError, ValueError):
        return None
    delta = next_claim - now
    if delta.total_seconds() < 0:
        return None
    return str(delta).split(".")[0]  # HH:MM:SS


def grant_daily_role_bonus(member):
    """Award role-based daily cash bonuses and badge rewards for the configured server."""
    if member is None or member.guild is None or member.guild.id != 1189460443736055828:
        return 0, []

    bonus_total = 0
    bonus_rows = []
    badges = load_badges() if callable(load_badges) else {}
    uid_str = str(member.id)
    user_badges = badges.setdefault(uid_str, [])

    for role_id, config in SERVER_DAILY_ROLE_BONUSES.items():
        if any(role.id == role_id for role in member.roles):
            bonus_total += int(config["amount"])
            bonus_rows.append((config["emoji"], int(config["amount"]), config["name"]))
            badge_key = ROLE_BADGE_KEYS.get(role_id)
            if badge_key and badge_key not in user_badges:
                user_badges.append(badge_key)

    if user_badges:
        badges[uid_str] = user_badges
    if callable(save_badges):
        save_badges(badges)

    return bonus_total, bonus_rows


@_legacy_command
async def daily(ctx):
    user_id = str(ctx.author.id)
    users_data = load_users()
    daily_data = users_data.get("daily_data", {})
    now = datetime.now(timezone.utc).isoformat()
    user = daily_data.get(user_id, {"streak": 0, "last_claim": None})
    # Ensure required keys exist
    if "streak" not in user:
        user["streak"] = 0
    if "last_claim" not in user:
        user["last_claim"] = None

    # Check if already claimed
    last_claim = user.get("last_claim")
    if last_claim:
        time_left = get_time_left(last_claim)
        if time_left:
            await ctx.send(f" 🎮 Next claim in: `{time_left}`")
            return

    # Update streak
    if last_claim:
        try:
            last_claim_time = datetime.fromisoformat(last_claim)
            if last_claim_time.tzinfo is None:
                last_claim_time = last_claim_time.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            last_claim_time = None
        if last_claim_time is None:
            user["streak"] = 1
        elif (datetime.now(timezone.utc) - last_claim_time).total_seconds() > 48 * 3600:
            user["streak"] = 1
        else:
            user["streak"] = user.get("streak", 0) + 1
    else:
        user["streak"] = 1

    # Determine reward
    current_streak = user.get("streak", 0)
    reward = 2000

    # Add any server role bonus rewards and badges
    role_bonus_total, role_bonus_rows = grant_daily_role_bonus(ctx.author)
    total_reward = reward + role_bonus_total

    # Update data
    user["last_claim"] = now
    daily_data[user_id] = user
    users_data["daily_data"] = daily_data
    save_users(users_data)

    # Add reward to user's main cash wallet
    users_data = load_users()
    user = get_user_data(users_data, ctx.author.id, ctx.guild.id)
    user["economy"]["cash"] = user["economy"].get("cash", 0) + total_reward
    save_user_data(user, ctx.author.id, ctx.guild.id)

    # Show all custom emojis in the server
    emoji_server = bot.get_guild(1374726576742072371)
    # Use Discord application emojis
    gift_emoji = "🎮"
    cash_emoji = savage_cash_emoji
    aura_emoji = "🎮"

    reward_lines = [
        f"{gift_emoji} | **{ctx.author.display_name}** daily Reward!",
        f"{cash_emoji} | +{reward} cash.",
    ]
    for emoji, amount, role_name in role_bonus_rows:
        reward_lines.append(f"{emoji} | **{role_name}**: +{amount:,} cash")
    reward_lines.append(f"{aura_emoji} | You're on a **{current_streak} daily streak**.")

    await ctx.send("\n".join(reward_lines))