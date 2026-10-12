"""User profile command."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord

from commands import _legacy_command
from commands.dungeon.pet import get_pet_collection, get_pet_emoji
from commands.general.badge import get_effective_badges_for_user
from commands.social.level import get_xp_progress

if TYPE_CHECKING:
    BOTTLE_ITEMS: dict
    LOOTBOX_ITEMS: dict
    ROLL_ITEMS: dict
    KEY_ITEMS: dict
    BADGE_LIST: dict
    get_user_data: Any
    load_users: Any
    load_badges: Any
    load_clans: Any
    get_clan_by_user: Any
    bar_shield_id: int
    savage_cash_emoji: str
    profile_dot_id: int
    profile_aura_id: int
    profile_skull_emoji: str
    profile_rank_emoji: str
    profile_xp_emoji: str
    profile_trophy_emoji: str
    profile_clock_emoji: str


# profile
@_legacy_command
async def profile(ctx, target: discord.User = None):
    """Show your profile or another user's profile. Usage: !profile [@user]"""
    if ctx.guild is None:
        await ctx.send("This command can only be used in a server.")
        return
    user_obj = target or ctx.author
    
    # Load all necessary data
    users_data = load_users()
    user = get_user_data(users_data, user_obj.id, ctx.guild.id)

    # Get XP data for level and started date
    xp_data = users_data.get("xp_data", {})
    uid_str = str(user_obj.id)
    user_xp = xp_data.get(uid_str, {"xp": 0, "start_date": None})
    xp = user_xp.get("xp", 0)
    level, xp_in_level, xp_for_next = get_xp_progress(xp)
    
    # Get started date
    start_date = user_xp.get("start_date")
    if not start_date:
        start_date = user_obj.created_at.strftime("%Y-%m-%d")
    
    # Format started date nicely (e.g., "November 14, 2025")
    try:
        date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%B %d, %Y")
    except Exception:
        formatted_date = start_date
    
    # Calculate net worth (cash + bonds + inventory value)
    net_worth = 0
    economy = user.get("economy", {})
    net_worth += int(economy.get("cash", 0) or 0)
    net_worth += int(user.get("bond", 0) or 0)  # Add bonds/rum
    
    # Calculate inventory value
    inventory = user.get("inventory", [])
    inventory_value = 0
    
    # Add value from roll items
    for entry in inventory:
        item_id = entry.get("item_id") if isinstance(entry, dict) else entry
        quantity = int(entry.get("quantity", 1) or 1) if isinstance(entry, dict) else 1
        if item_id in ROLL_ITEMS:
            item_data = ROLL_ITEMS[item_id]
            inventory_value += int(item_data.get("price", 0)) * quantity
        elif item_id in BOTTLE_ITEMS:
            item_data = BOTTLE_ITEMS[item_id]
            inventory_value += int(item_data.get("price", 0)) * quantity
        elif item_id in KEY_ITEMS:
            item_data = KEY_ITEMS[item_id]
            inventory_value += int(item_data.get("price", 0)) * quantity
        elif item_id in LOOTBOX_ITEMS:
            item_data = LOOTBOX_ITEMS[item_id]
            inventory_value += int(item_data.get("price", 0)) * quantity
    
    net_worth += inventory_value

    # Calculate leaderboard rank based on net worth
    users = []
    for uid, u in users_data.get("users", {}).items():
        try:
            uid_int = int(uid.split("_")[0])  # Extract user_id from "user_id_guild_id" format
        except Exception:
            continue
        nw = 0
        user_economy = u.get("economy", {})
        nw += int(user_economy.get("cash", 0) or 0)
        nw += int(u.get("bond", 0) or 0)  # Add bonds/rum
        
        # Calculate inventory value for ranking
        user_inventory = u.get("inventory", [])
        user_inventory_value = 0
        for entry in user_inventory:
            item_id = entry.get("item_id") if isinstance(entry, dict) else entry
            quantity = int(entry.get("quantity", 1) or 1) if isinstance(entry, dict) else 1
            if item_id in ROLL_ITEMS:
                item_data = ROLL_ITEMS[item_id]
                user_inventory_value += int(item_data.get("price", 0)) * quantity
            elif item_id in BOTTLE_ITEMS:
                item_data = BOTTLE_ITEMS[item_id]
                user_inventory_value += int(item_data.get("price", 0)) * quantity
            elif item_id in KEY_ITEMS:
                item_data = KEY_ITEMS[item_id]
                user_inventory_value += int(item_data.get("price", 0)) * quantity
            elif item_id in LOOTBOX_ITEMS:
                item_data = LOOTBOX_ITEMS[item_id]
                user_inventory_value += int(item_data.get("price", 0)) * quantity
        
        nw += user_inventory_value
        users.append({"id": uid_int, "net_worth": nw})
    
    users_sorted = sorted(users, key=lambda x: x["net_worth"], reverse=True)
    user_rank = next((i + 1 for i, u in enumerate(users_sorted) if u["id"] == user_obj.id), None)
    if user_rank is None:
        user_rank = len(users_sorted) + 1
    
    # Get clan
    clans = load_clans()
    clan_name, clan = get_clan_by_user(clans, str(user_obj.id))
    clan_display = clan_name if clan_name else "None"
    
    # Get aura (default to 0 if not found)
    aura = user.get("aura", 0)
    
    # Get badges
    member = ctx.guild.get_member(user_obj.id)
    user_badges = get_effective_badges_for_user(user_obj.id, ctx.guild, member=member, level=level)

    # Show readable badge names without requiring server-specific emoji.
    badge_parts = []
    for bid in user_badges:
        name, _ = BADGE_LIST.get(str(bid), (None, None))
        if name:
            badge_parts.append(name.replace("_", " ").title())

    badges_display = " ".join(badge_parts) if badge_parts else "None"
    
    # Discord will render these emoji strings automatically
    s_dot = "🎮"
    s_skull = profile_skull_emoji
    clan_shield = "🎮"
    s_clock = profile_clock_emoji
    savage_cash = savage_cash_emoji
    s_aura = "✨"
    trophy = profile_trophy_emoji
    
    # Format net worth with commas
    net_worth_formatted = f"{net_worth:,}"
    
    # Build embed
    embed = discord.Embed(
        color=discord.Color.blue()
    )
    
    # Set user profile image as thumbnail
    embed.set_thumbnail(url=user_obj.display_avatar.replace(size=1024).url)
    
    owned_pet_ids = get_pet_collection(user_obj.id)
    owned_pet_emojis = dict.fromkeys(
        emoji
        for pet_id in owned_pet_ids
        if (emoji := get_pet_emoji(bot, ctx.guild, str(pet_id), ""))
    )
    pet_emoji_display = " ".join(owned_pet_emojis) or "None"
    pet_emoji_line = f"🎮 **PETS: ** {pet_emoji_display}"

    # About me section
    about_me = (
        f"{s_skull} **NAME: ** {user_obj.display_name}\n"
        f"{s_clock} **Started At: ** {formatted_date}\n"
        f"{savage_cash} **Net Worth: ** {net_worth_formatted}\n"
        f"{clan_shield} **Clan: ** {clan_display}\n"
        f"{s_aura} **Aura: ** {aura}\n"
        f"{profile_rank_emoji} **Level: ** {level}\n"
        f"{trophy} **Global RANK: ** {user_rank:,}\n"
        f"{pet_emoji_line}"
    )
    
    embed.add_field(
        name=f"{s_dot} `     About me:       `",
        value=about_me,
        inline=False
    )

    # My Badges section
    embed.add_field(
        name=f"{s_dot} `     My Badges:      `",
        value=badges_display if badges_display != "None" else "No badges yet.",
        inline=False
    )

    owns_banner_11 = any(
        (entry.get("item_id") if isinstance(entry, dict) else entry) == "banner_11"
        for entry in inventory
    )
    if owns_banner_11:
        embed.set_image(
            url="https://raw.githubusercontent.com/Savage404E/SAVAGE-BOT/refs/heads/main/moneybb.gif"
        )
    
    # Set footer
    embed.set_footer(text="https://discord.gg/besavage")
    
    await ctx.send(embed=embed)
