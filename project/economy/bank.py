"""Bank economy commands."""

import asyncio
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


# bank system
#Bank commands: bank (view only), bank remove @user <amount>, bank check @user (owner only)
import math
from decimal import Decimal, InvalidOperation

BANK_GIF = "https://cdn.dribbble.com/userupload/41903462/file/original-63ed3937b81e00d0b9ab5da7bd00c298.gif"  # green/bank gif (used as thumbnail)
BANK_EMOJI_SERVER_ID = 1189460443736055828
DEFAULT_BANK_STORAGE = Decimal(50000)  # 50k free storage by default
STORAGE_MULTIPLIER = Decimal(2)        # update pays -> storage increase = paid_amount * 2
BANK_UPGRADE_COST = Decimal(50000)
BANK_UPGRADE_SIZE = Decimal(50000)
BANK_UPGRADE_COOLDOWN_SECONDS = 60 * 60
savage_cash_emoji = "🎮"
ARROW_EMOJI = "🎮"


async def _send_bank_upgrade_success_dm(user_id: int):
    """Send the upgrade success DM exactly 60 minutes after the upgrade is confirmed."""
    await asyncio.sleep(BANK_UPGRADE_COOLDOWN_SECONDS)
    users_data = load_users()
    user_key = str(user_id)
    user = users_data["users"].get(user_key, {})
    economy = user.get("economy", {})
    if economy.get("bank_upgrade_dm_sent"):
        return

    try:
        member = await bot.fetch_user(user_id)
        if member is not None:
            await member.send("Bank Upgrade Successful.")
    except Exception:
        pass

    economy["bank_upgrade_dm_sent"] = True
    users_data["users"][user_key] = user
    save_users(users_data)

def format_money(amount):
    # show integers without decimals, decimals with 2 places using Decimal for accuracy
    try:
        amt = Decimal(str(amount))
    except Exception:
        return str(amount)
    if amt == amt.to_integral():
        return f"{int(amt):,}"
    return f"{amt.quantize(Decimal('0.01')):,}"

def _to_number_for_storage(d: Decimal):
    # store integers as int, otherwise as float to keep compatibility with existing code
    if d == d.to_integral():
        return int(d)
    return float(d)

@_legacy_command
async def bank_cmd(ctx, action: str = None, *args: str):
    """
    Usage:
    bank -> show bank embed (shows storage used / capacity)
    Owner-only subcommands (use as shown):
    bank remove @user <amount|all> -> remove cash from user's bank (bot owner only)
    bank check @user -> check other user's bank cash (bot owner only)
    """
    # Load user data using SQLite
    users_data = load_users()
    user_key = str(ctx.author.id)  # Use only user ID for cross-server consistency
    user = users_data["users"].get(user_key, {})
    economy = user.get("economy", {})
    
    # ensure bank keys exist with defaults
    if "bank" not in economy:
        economy["bank"] = 0
    if "bank_storage" not in economy:
        economy["bank_storage"] = _to_number_for_storage(DEFAULT_BANK_STORAGE)
        users_data["users"][user_key] = user
        save_users(users_data)

    cooldown_until = economy.get("bank_upgrade_cooldown_until")
    if cooldown_until is not None:
        try:
            cooldown_until = float(cooldown_until)
        except (TypeError, ValueError):
            cooldown_until = None

    if cooldown_until is not None and cooldown_until > time.time():
        remaining_seconds = max(1, int(math.ceil(cooldown_until - time.time())))
        remaining_minutes = max(1, math.ceil(remaining_seconds / 60))
        await ctx.send(f"⏳ Bank upgrade is active. You can use the bank again in {remaining_minutes} minute(s).")
        return

    if cooldown_until is not None and cooldown_until <= time.time():
        if not economy.get("bank_upgrade_dm_sent"):
            try:
                await ctx.author.send("Bank Upgrade Successful.")
            except Exception:
                pass
            economy["bank_upgrade_dm_sent"] = True
        economy.pop("bank_upgrade_cooldown_until", None)
        users_data["users"][user_key] = user
        save_users(users_data)

    # ensure numeric typed values for local calculations
    try:
        user_bank = Decimal(str(economy.get("bank", 0)))
    except Exception:
        user_bank = Decimal(0)
    try:
        user_cash = Decimal(str(economy.get("cash", 0)))
    except Exception:
        user_cash = Decimal(0)
    try:
        bank_capacity = Decimal(str(economy.get("bank_storage", DEFAULT_BANK_STORAGE)))
    except Exception:
        bank_capacity = DEFAULT_BANK_STORAGE

    # Build bank-specific leaderboard (rank by bank balance only) using SQLite
    bank_list = []
    for user_key, user_data in users_data["users"].items():
        try:
            # user_key is now just the user ID (no guild)
            uid = int(user_key)
            economy = user_data.get("economy", {})
            b = Decimal(str(economy.get("bank", 0)))
            bank_list.append((uid, b))
        except Exception:
            continue
    # sort descending by bank
    bank_list_sorted = sorted(bank_list, key=lambda x: x[1], reverse=True)

    total_users = max(1, len(bank_list_sorted))
    # find top holder and top amount
    top_holder_id = bank_list_sorted[0][0] if bank_list_sorted else None
    top_bank_amt = bank_list_sorted[0][1] if bank_list_sorted else Decimal(0)

    # determine rank by bank (first position of user's id in sorted list)
    user_rank = None
    for idx, (uid, b) in enumerate(bank_list_sorted, start=1):
        if uid == int(ctx.author.id):
            user_rank = idx
            break
    if user_rank is None:
        # user not found in data? put at end
        user_rank = len(bank_list_sorted) + 1

    # percent relative to top bank holder (if top has >0)
    if top_bank_amt > 0:
        try:
            bank_percent_of_top = (user_bank / top_bank_amt) * 100
        except Exception:
            bank_percent_of_top = Decimal(0)
    else:
        bank_percent_of_top = Decimal(0)

    # Friendly values
    try:
        top_holder_mention = f"<@{top_holder_id}>" if top_holder_id else "N/A"
    except Exception:
        top_holder_mention = "N/A"

    # If owner-only subcommands (add, remove, check) were invoked, parse them from the raw message
    if action is not None and action.lower() in ("add", "remove", "check"):
        owner_id = 1243921225554726954
        if ctx.author.id != owner_id:
            await ctx.send("Only the bot owner can use this subcommand.")
            return

        tokens = ctx.message.content.split()
        # tokens[0] = prefix+bank, tokens[1] = action, rest = args
        if len(tokens) < 3:
            await ctx.send("Usage: `bank add @user <amount>` / `bank remove @user <amount|all>` / `bank check @user`")
            return

        # resolve mentioned user first if present
        target_member = None
        if ctx.message.mentions:
            target_member = ctx.message.mentions[0]
        else:
            # try parse id from tokens[2]
            try:
                candidate = tokens[2]
                uid = int(re.sub(r"\D", "", candidate))
                # try to get member from guild, fallback to fetch user
                if ctx.guild:
                    target_member = ctx.guild.get_member(uid)
                if not target_member:
                    try:
                        target_member = await bot.fetch_user(uid)
                    except Exception:
                        target_member = None
            except Exception:
                target_member = None

        if not target_member:
            await ctx.send("Could not find the target user. Mention them or provide a valid user ID.")
            return

        # Load fresh data and target user record (guild-aware)
        users_data = load_users()
        target = get_user_data(users_data, target_member.id, ctx.guild.id)

        if action.lower() == "check":
            bank_amt = target.get("economy", {}).get("bank", 0)
            await ctx.send(f"{target_member.mention} Bank Balance: {format_money(bank_amt)}")
            return

        # action == add or remove
        # amount may be token[3] onwards (in case of formatting); default to 'all'
        amt_token = "all"
        if len(tokens) >= 4:
            amt_token = tokens[3]

        # parse amount
        try:
            if action.lower() == "remove" and str(amt_token).lower() == "all":
                remove_amt = Decimal(str(target.get("economy", {}).get("bank", 0)))
            else:
                amount_text = str(amt_token).strip().lower().replace(",", "")
                multiplier = Decimal(1000) if amount_text.endswith("k") else Decimal(1)
                if multiplier == Decimal(1000):
                    amount_text = amount_text[:-1]
                remove_amt = Decimal(amount_text) * multiplier
        except (InvalidOperation, AttributeError):
            await ctx.send("Invalid amount. Use a number like `10000` or `10k` (or `all` when removing).")
            return

        if remove_amt <= 0:
            await ctx.send("Amount must be greater than zero (or use `all`).")
            return

        economy = target.setdefault("economy", {})
        current_bank = Decimal(str(economy.get("bank", 0)))
        if action.lower() == "add":
            new_bank = current_bank + remove_amt
            result_message = f"✅ Added {format_money(remove_amt)} to {target_member.mention}'s bank. New bank balance: {format_money(new_bank)}"
        else:
            removed = min(current_bank, remove_amt)
            new_bank = current_bank - removed
            result_message = f"✅ Removed {format_money(removed)} from {target_member.mention}'s bank. New bank balance: {format_money(new_bank)}"
        economy["bank"] = _to_number_for_storage(new_bank)
        save_users(users_data)
        await ctx.send(result_message)
        return

    # process normal actions
    if action is None:
        # show embed with gif as small thumbnail in corner and storage info
        emoji_server = bot.get_guild(BANK_EMOJI_SERVER_ID)
        bank_emoji_text = savage_cash_emoji

        def build_bank_embed():
            embed = discord.Embed(
                color=discord.Color.green(),
            )
            embed.set_thumbnail(url=BANK_GIF)
            point_emoji = "🎮"
            embed.add_field(name=f"{point_emoji} Bank Balance :", value=f"{format_money(user_bank)} / {format_money(bank_capacity)} {bank_emoji_text}", inline=False)
            embed.add_field(
                name=f"{point_emoji} Bank Rank :",
                value=(
                    f"Rank: `{user_rank}/{total_users}`\n"
                ),
                inline=False
            )
            embed.add_field(
                name=f"{point_emoji} Bank Upgrade cost :",
                value=f"{format_money(BANK_UPGRADE_COST)} {savage_cash_emoji} {ARROW_EMOJI} {format_money(BANK_UPGRADE_SIZE)} Bank {ARROW_EMOJI} size",
                inline=False,
            )
            return embed

        embed = build_bank_embed()

        class BankView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=180)

            @discord.ui.button(label="ADD", style=discord.ButtonStyle.green)
            async def add_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_modal(BankAddModal())

            @discord.ui.button(label="REMOVE", style=discord.ButtonStyle.red)
            async def remove_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_modal(BankRemoveModal())

            @discord.ui.button(label="UPGRADE", style=discord.ButtonStyle.blurple)
            async def upgrade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                confirm_embed = discord.Embed(title="Bank Upgrade Confirmation", color=discord.Color.orange())
                confirm_embed.description = (
                    f"You sure want to spend **{format_money(BANK_UPGRADE_COST)}** {savage_cash_emoji} "
                    f"to increase bank size up to **{format_money(BANK_UPGRADE_SIZE)}** more?"
                )
                await interaction.response.edit_message(embed=confirm_embed, view=BankUpgradeConfirmView())

        class BankUpgradeConfirmView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=180)

            @discord.ui.button(label="YES", style=discord.ButtonStyle.green)
            async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                users_data = load_users()
                user_key = str(interaction.user.id)
                user = users_data["users"].get(user_key, {})
                economy = user.get("economy", {})

                try:
                    user_cash = Decimal(str(economy.get("cash", 0)))
                    bank_capacity = Decimal(str(economy.get("bank_storage", DEFAULT_BANK_STORAGE)))
                except Exception:
                    await interaction.response.edit_message(embed=discord.Embed(title="Bank Upgrade", description="Error loading bank data."), view=None)
                    return

                if user_cash < BANK_UPGRADE_COST:
                    fail_embed = discord.Embed(title="Bank Upgrade", color=discord.Color.red())
                    fail_embed.description = f"You need **{format_money(BANK_UPGRADE_COST)}** {savage_cash_emoji} to upgrade your bank."
                    await interaction.response.edit_message(embed=fail_embed, view=BankView())
                    return

                new_cash = user_cash - BANK_UPGRADE_COST
                new_capacity = bank_capacity + BANK_UPGRADE_SIZE
                economy["cash"] = _to_number_for_storage(new_cash)
                economy["bank_storage"] = _to_number_for_storage(new_capacity)
                economy["bank_upgrade_cooldown_until"] = time.time() + BANK_UPGRADE_COOLDOWN_SECONDS
                economy["bank_upgrade_dm_sent"] = False
                users_data["users"][user_key] = user
                save_users(users_data)
                asyncio.create_task(_send_bank_upgrade_success_dm(interaction.user.id))

                success_embed = discord.Embed(title="Bank Upgrade Successful", color=discord.Color.green())
                success_embed.description = (
                    f"Spent **{format_money(BANK_UPGRADE_COST)}** {savage_cash_emoji} and increased bank size by **{format_money(BANK_UPGRADE_SIZE)}**."
                )
                success_embed.add_field(name="New Bank Capacity", value=f"{format_money(new_capacity)} {savage_cash_emoji}", inline=False)
                success_embed.add_field(name="New Cash", value=f"{format_money(new_cash)} {savage_cash_emoji}", inline=False)
                success_embed.add_field(name="Cooldown", value=f"You can use the bank again in 60 minutes.", inline=False)
                await interaction.response.edit_message(embed=success_embed, view=None)

            @discord.ui.button(label="NO", style=discord.ButtonStyle.red)
            async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.edit_message(embed=build_bank_embed(), view=BankView())

        class BankAddModal(discord.ui.Modal):
            def __init__(self):
                super().__init__(title="Add to Bank")

                self.add_item(discord.ui.TextInput(
                    label="Amount to deposit",
                    placeholder="Enter amount or 'all'",
                    required=True,
                    style=discord.TextStyle.short,
                    max_length=20
                ))

            async def on_submit(self, interaction: discord.Interaction):
                amount_input = self.children[0].value
                await self.process_bank_add(interaction, amount_input)

            async def process_bank_add(self, interaction, amount_input):
                # Reload fresh data using SQLite
                users_data = load_users()
                user_key = str(interaction.user.id)  # Use only user ID for cross-server consistency
                user = users_data["users"].get(user_key, {})
                economy = user.get("economy", {})

                try:
                    user_cash = Decimal(str(economy.get("cash", 0)))
                    user_bank = Decimal(str(economy.get("bank", 0)))
                    bank_capacity = Decimal(str(economy.get("bank_storage", DEFAULT_BANK_STORAGE)))
                except Exception:
                    await interaction.response.send_message("Error loading bank data.", ephemeral=True)
                    return

                # Parse amount
                if amount_input.lower() == "all":
                    amount = user_cash
                else:
                    try:
                        amount = Decimal(str(amount_input))
                    except Exception:
                        await interaction.response.send_message("Invalid amount. Use a number or 'all'.", ephemeral=True)
                        return

                if amount <= 0:
                    await interaction.response.send_message("Amount must be greater than zero.", ephemeral=True)
                    return

                if amount > user_cash:
                    await interaction.response.send_message(f"You don't have enough cash! You have {format_money(user_cash)}.", ephemeral=True)
                    return

                # Check bank capacity
                available_space = bank_capacity - user_bank
                if amount > available_space:
                    amount = available_space
                    if amount <= 0:
                        await interaction.response.send_message("Your bank is full! Upgrade your storage.", ephemeral=True)
                        return

                # Process deposit
                new_cash = user_cash - amount
                new_bank = user_bank + amount

                economy["cash"] = _to_number_for_storage(new_cash)
                economy["bank"] = _to_number_for_storage(new_bank)
                users_data["users"][user_key] = user
                save_users(users_data)

                await interaction.response.send_message(
                    f"**Bank Deposit Successful!**\n"
                    f"Deposited: {format_money(amount)}\n"
                    f"New Bank Balance: {format_money(new_bank)}\n"
                    f"New Cash: {format_money(new_cash)}"
                )

        class BankRemoveModal(discord.ui.Modal):
            def __init__(self):
                super().__init__(title="Remove from Bank")

                self.add_item(discord.ui.TextInput(
                    label="Amount to withdraw",
                    placeholder="Enter amount or 'all'",
                    required=True,
                    style=discord.TextStyle.short,
                    max_length=20
                ))

            async def on_submit(self, interaction: discord.Interaction):
                amount_input = self.children[0].value
                await self.process_bank_remove(interaction, amount_input)

            async def process_bank_remove(self, interaction, amount_input):
                # Reload fresh data using SQLite
                users_data = load_users()
                user_key = str(interaction.user.id)  # Use only user ID for cross-server consistency
                user = users_data["users"].get(user_key, {})
                economy = user.get("economy", {})

                try:
                    user_cash = Decimal(str(economy.get("cash", 0)))
                    user_bank = Decimal(str(economy.get("bank", 0)))
                except Exception:
                    await interaction.response.send_message("Error loading bank data.", ephemeral=True)
                    return

                # Parse amount
                if amount_input.lower() == "all":
                    amount = user_bank
                else:
                    try:
                        amount = Decimal(str(amount_input))
                    except Exception:
                        await interaction.response.send_message("Invalid amount. Use a number or 'all'.", ephemeral=True)
                        return

                if amount <= 0:
                    await interaction.response.send_message("Amount must be greater than zero.", ephemeral=True)
                    return

                if amount > user_bank:
                    await interaction.response.send_message(f"You don't have enough in bank! You have {format_money(user_bank)}.", ephemeral=True)
                    return

                # Process withdrawal
                new_cash = user_cash + amount
                new_bank = user_bank - amount

                economy["cash"] = _to_number_for_storage(new_cash)
                economy["bank"] = _to_number_for_storage(new_bank)
                users_data["users"][user_key] = user
                save_users(users_data)

                await interaction.response.send_message(
                    f"**Bank Withdrawal Successful!**\n"
                    f"Withdrawn: {format_money(amount)}\n"
                    f"New Bank Balance: {format_money(new_bank)}\n"
                    f"New Cash: {format_money(new_cash)}"
                )

        await ctx.send(
            content=f"{ctx.author.mention} BANK",
            embed=embed,
            view=BankView(),
            allowed_mentions=discord.AllowedMentions(
                users=[ctx.author],
                roles=False,
                everyone=False,
                replied_user=False,
            ),
        )
        return

    # Text-based subcommands for add, back, and update have been removed
    # Users can only use the buttons for these operations now
    if action is not None and action.lower() not in ("add", "remove", "check"):
        await ctx.send("Unknown action. Use `bank` to view your bank or use the buttons.")
        return

# New command: (prefix)bank10 (bot owner only) - show top 10 bank holders by bank balance
@bot.command(name="bank10")
async def bank_top10(ctx):
    owner_id = 1243921225554726954
    if ctx.author.id != owner_id:
        await ctx.send("Only the bot owner can use this command.")
        return

    users_data = load_users()
    bank_list = []
    for uid, u in users_data.get("users", {}).items():
        try:
            b = Decimal(str(u.get("economy", {}).get("bank", u.get("bank", 0))))
        except Exception:
            try:
                b = Decimal(u.get("economy", {}).get("bank", u.get("bank", 0)))
            except Exception:
                b = Decimal(0)
        try:
            bank_list.append((int(uid), b))
        except Exception:
            continue

    if not bank_list:
        await ctx.send("No bank data available.")
        return

    bank_list_sorted = sorted(bank_list, key=lambda x: x[1], reverse=True)
    top10 = bank_list_sorted[:10]

    embed = discord.Embed(title="🏦 Top 10 Bank Holders", color=discord.Color.gold())
    lines = []
    for idx, (uid, amt) in enumerate(top10, start=1):
        lines.append(f"**{idx}.** <@{uid}> — {format_money(amt)}")
    embed.description = "\n".join(lines)
    embed.set_footer(text="Global bank leaderboard — Top 10")
    await ctx.send(embed=embed)
