"""Gambling and games command registration."""

from . import coinflip, crime, fish, horse, hunt, mine, plinko, pyramid, rob, roulette, slot


def register_games_commands(
	bot,
	*,
	load_users=None,
	save_users=None,
	get_user_data=None,
	save_user_data=None,
	db_get=None,
	db_set=None,
	weighted_rng=None,
	heads_emoji=None,
	tails_emoji=None,
	cash_emoji=None,
	arrow_emoji=None,
	dot_emoji=None,
	red_flag_emoji=None,
	bomb_emoji=None,
	green_flag_emoji=None,
	pyramid_emoji=None,
	legacy_commands=None,
):
	"""Inject shared services and register the existing game commands."""
	legacy_commands = legacy_commands or {}
	dependencies = {
		"bot": bot,
		"load_users": load_users,
		"save_users": save_users,
		"get_user_data": get_user_data,
		"save_user_data": save_user_data,
		"db_get": db_get,
		"db_set": db_set,
		"configured_heads_emoji": heads_emoji,
		"configured_tails_emoji": tails_emoji,
		"configured_cash_emoji": cash_emoji,
		"savage_cash_emoji": cash_emoji,
		"configured_arrow_emoji": arrow_emoji,
		"configured_dot_emoji": dot_emoji,
		"configured_red_flag_emoji": red_flag_emoji,
		"configured_bomb_emoji": bomb_emoji,
		"configured_green_flag_emoji": green_flag_emoji,
		"configured_pyramid_emoji": pyramid_emoji,
	}
	if weighted_rng is not None:
		dependencies["WeightedRNG"] = weighted_rng

	modules = (coinflip, crime, fish, horse, hunt, mine, plinko, pyramid, rob, roulette, slot)
	for module in modules:
		module.__dict__.update(dependencies)
	if crime.block_jail_gambling not in getattr(bot, "_checks", ()):
		bot.add_check(crime.block_jail_gambling)

	commands_to_add = (
		(coinflip.coinflip, "coinflip", ("cf",)),
		(slot.slot, "slot", ()),
		(roulette.Roulette, "roulette", ("rr",)),
		(plinko.plinko, "plinko", ()),
		(crime.crime, "crime", ()),
		(crime.work, "work", ()),
		(horse.horse, "horse", ()),
		(pyramid.pyramid, "pyramid", ()),
		(rob.rob, "rob", ()),
		(mine.mine, "mine", ()),
		(fish.fish, "fish", ()),
		(hunt.hunt, "hunt", ("h",)),
		(hunt.hunt_shop, "hunt_shop", ("huntshop",)),
		(hunt.equip_gun, "equip_gun", ("gun",)),
		(hunt.sell, "sell", ("ssell",)),
		(hunt.zoo, "zoo", ()),
		(hunt.zoolb, "zoolb", ()),
		(hunt.book, "book", ()),
	)
	for command, command_name, aliases in commands_to_add:
		for registered_name, registered_command in list(bot.all_commands.items()):
			if registered_command is command:
				bot.remove_command(registered_name)
		command.name = command_name
		command.aliases = [alias for alias in aliases if alias != command_name]
		if command.name not in bot.all_commands:
			bot.add_command(command)


__all__ = ["register_games_commands"]