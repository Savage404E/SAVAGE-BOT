"""Cash balance command."""

from typing import TYPE_CHECKING, Any
from decimal import Decimal, InvalidOperation
import re

import discord

from commands import _legacy_command

if TYPE_CHECKING:
    bot: Any
    rum_emoji: str
    savage_cash_emoji: str
    BOT_OWNER_ID: int
    get_user_data: Any
    load_users: Any
    save_users: Any


# Cash command
@_legacy_command
async def _resolve_cash_member(ctx, value):
    if ctx.message.mentions:
        return ctx.message.mentions[0]
    match = re.fullmatch(r"<@!?(\d+)>", str(value))
    try:
        user_id = int(match.group(1)) if match else int(value)
    except (TypeError, ValueError):
        return None
    member = ctx.guild.get_member(user_id) if ctx.guild else None
    if member:
        return member
    try:
        return await bot.fetch_user(user_id)
    except Exception:
        return None


def _parse_cash_amount(value):
    try:
        amount_text = str(value).strip().lower().replace(",", "")
        multiplier = Decimal(1000) if amount_text.endswith("k") else Decimal(1)
        if multiplier == Decimal(1000):
            amount_text = amount_text[:-1]
        amount = Decimal(amount_text) * multiplier
        if amount <= 0 or amount != amount.to_integral_value():
            return None
        return int(amount)
    except (InvalidOperation, ValueError):
        return None


@_legacy_command
async def cash(ctx, *args: str):
    """Show balances, or let the bot owner add/remove another user's cash."""
    if ctx.guild is None:
        await ctx.send("This command can only be used in a server.")
        return

    if args and args[0].lower() in ("add", "remove"):
        action = args[0].lower()
        if len(args) != 3:
            await ctx.send(
                f"Usage: `cash {action} @user <amount>` (amount may use `k`, e.g. `10k`)."
            )
            return
        if ctx.author.id != BOT_OWNER_ID:
            await ctx.send("Only the bot owner can use this command.")
            return
        user_obj = await _resolve_cash_member(ctx, args[1])
        amount = _parse_cash_amount(args[2])
        if user_obj is None:
            await ctx.send("Provide a valid @user or user ID.")
            return
        if amount is None:
            await ctx.send("Amount must be a positive whole number, such as `10000` or `10k`.")
            return
        users_data = load_users()
        user = get_user_data(users_data, user_obj.id, ctx.guild.id)
        economy = user.setdefault("economy", {})
        current_cash = economy.get("cash", 0)
        if action == "add":
            economy["cash"] = current_cash + amount
        else:
            economy["cash"] = max(0, current_cash - amount)
        save_users(users_data)
        verb = "Added" if action == "add" else "Removed"
        await ctx.send(f"{verb} {amount:,} cash for {user_obj.mention}. New balance: {economy['cash']:,}.")
        return

    if len(args) > 1:
        await ctx.send("Usage: `cash` or `cash @user`.")
        return

    users_data = load_users()
    user_obj = ctx.author
    if args:
        user_obj = await _resolve_cash_member(ctx, args[0])
        if user_obj is None:
            await ctx.send("Provide a valid @user or user ID.")
            return
    if user_obj.id != ctx.author.id:
        appinfo = await bot.application_info()
        is_owner = ctx.author.id == appinfo.owner.id if hasattr(appinfo, "owner") else False
        if not is_owner:
            await ctx.send("You can only check your own balance.")
            return

    user = get_user_data(users_data, user_obj.id, ctx.guild.id)
    cash_emoji = savage_cash_emoji
    cash_amount = user.get("economy", {}).get('cash', 0)
    bond_amount = user.get('rum', 0)

    # Show amounts as whole numbers (no decimal points).
    try:
        cash_display = f"{int(round(float(cash_amount))):,}"
    except Exception:
        cash_display = str(cash_amount)
    try:
        bond_display = f"{int(round(float(bond_amount))):,}"
    except Exception:
        bond_display = str(bond_amount)

    await ctx.send(
        f"*{user_obj.mention}* Wallet !\n"
        f"CASH: {cash_display} {cash_emoji}\n"
        f"RUM: {bond_display} {rum_emoji}"
    )
