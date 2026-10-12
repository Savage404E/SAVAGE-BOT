"""Registration for the economy command modules included in this project."""

from . import bank, cash, daily, leaderboard, lottery, profile


def register_economy_commands(
    bot,
    *,
    load_users,
    save_users,
    get_user_data,
    save_user_data,
    load_clans=None,
    get_clan_by_user=None,
    load_badges=None,
    save_badges=None,
    badge_list=None,
    agreed_users=None,
    roll_items=None,
    bottle_items=None,
    key_items=None,
    lootbox_items=None,
    dungeon_key_prices=None,
    constants=None,
    **_unused,
):
    """Inject shared services and register the requested economy commands."""
    constants = constants or {}
    dependencies = {
        "bot": bot,
        "load_users": load_users,
        "save_users": save_users,
        "get_user_data": get_user_data,
        "save_user_data": save_user_data,
        "load_clans": load_clans or (lambda: {}),
        "get_clan_by_user": get_clan_by_user or (lambda clans, user_id: (None, None)),
        "load_badges": load_badges or (lambda: {}),
        "save_badges": save_badges or (lambda data: None),
        "BADGE_LIST": badge_list or {},
        "agreed_users": agreed_users if agreed_users is not None else set(),
        "ROLL_ITEMS": roll_items or {},
        "BOTTLE_ITEMS": bottle_items or {},
        "KEY_ITEMS": key_items or {},
        "LOOTBOX_ITEMS": lootbox_items or {},
        "DUNGEON_KEY_PRICES": dungeon_key_prices or {},
        "BOT_OWNER_ID": constants.get("bot_owner_id", 0),
        "bar_shield_id": 0,
        "rum_emoji": "🍹",
        "savage_cash_emoji": "💵",
        "ARROW_EMOJI": "➡️",
        "profile_dot_id": 0,
        "profile_aura_id": 0,
        "profile_skull_emoji": "💀",
        "profile_rank_emoji": "🏆",
        "profile_xp_emoji": "⭐",
        "profile_trophy_emoji": "🏆",
        "profile_clock_emoji": "🕒",
    }
    modules = (cash, bank, daily, leaderboard, lottery, profile)
    for module in modules:
        module.__dict__.update(dependencies)

    commands_to_add = (
        (cash.cash, "cash", ()),
        (bank.bank_cmd, "bank", ()),
        (bank.bank_top10, "bank10", ()),
        (daily.daily, "daily", ()),
        (leaderboard.leaderboard, "leaderboard", ("lb",)),
        (lottery.lottery, "lottery", ()),
        (profile.profile, "profile", ()),
    )
    for command, command_name, aliases in commands_to_add:
        for registered_name, registered_command in list(bot.all_commands.items()):
            if registered_command is command:
                bot.remove_command(registered_name)
        command.name = command_name
        command.aliases = list(aliases)
        if command.name not in bot.all_commands:
            bot.add_command(command)


__all__ = ["register_economy_commands"]
