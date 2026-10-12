"""Net-worth leaderboard command."""

import math
import time
from typing import TYPE_CHECKING, Any

import discord

from commands import _legacy_command

if TYPE_CHECKING:
    agreed_users: set[int]
    get_user_data: Any
    load_users: Any
    savage_cash_emoji: str


def get_agreed_cash_users():
    """Return cash, bank, and net worth for every accepted user."""
    users_data = load_users()
    user_values = {}
    for user_id in agreed_users:
        try:
            user_values[int(user_id)] = {"cash": 0, "bank": 0, "net_worth": 0}
        except (TypeError, ValueError):
            continue

    for user_key, user in users_data.get("users", {}).items():
        try:
            uid_int = int(user_key)
        except (TypeError, ValueError):
            continue
        if uid_int not in user_values:
            continue
        economy = user.get("economy", {}) or {}
        try:
            cash = int(economy.get("cash", user.get("cash", 0)) or 0)
        except (TypeError, ValueError):
            cash = 0
        try:
            bank = int(economy.get("bank", user.get("bank", 0)) or 0)
        except (TypeError, ValueError):
            bank = 0
        net_worth = cash + bank
        if net_worth > user_values[uid_int]["net_worth"]:
            user_values[uid_int] = {
                "cash": cash,
                "bank": bank,
                "net_worth": net_worth,
            }

    return [
        {"id": uid, **values}
        for uid, values in user_values.items()
    ]


# (prefix)lb - net worth, top 50
@_legacy_command
async def leaderboard(ctx, page: int = 1):
    await ctx.send(
        view=NetWorthLeaderboardView(ctx, page),
        allowed_mentions=discord.AllowedMentions(users=[ctx.author]),
    )


def get_aura_users():
    users_data = load_users()
    user_auras = {}
    for user_id in agreed_users:
        try:
            user_auras[int(user_id)] = 0
        except (TypeError, ValueError):
            continue

    for user_key, user in users_data.get("users", {}).items():
        try:
            user_id = int(user_key)
        except (TypeError, ValueError):
            continue
        if user_id not in user_auras:
            continue
        try:
            aura = int(user.get("aura", 0) or 0)
        except (TypeError, ValueError):
            aura = 0
        user_auras[user_id] = max(user_auras.get(user_id, 0), aura)
    return sorted(
        ({"id": user_id, "aura": aura} for user_id, aura in user_auras.items()),
        key=lambda user: user["aura"],
        reverse=True,
    )


def get_aura_username(ctx, user_id):
    member = ctx.guild.get_member(user_id) if getattr(ctx, "guild", None) else None
    user = member or ctx.bot.get_user(user_id)
    username = user.name if user else f"User {user_id}"
    return f"@\u200b{username}"


def create_leaderboard_content(ctx, page, author):
    users = get_agreed_cash_users()
    users_sorted_local = sorted(users, key=lambda x: x["net_worth"], reverse=True)
    per_page_local = 10
    total_pages_local = max(1, math.ceil(len(users_sorted_local) / per_page_local))
    page = max(1, min(page, total_pages_local))
    start_local = (page - 1) * per_page_local
    end_local = start_local + per_page_local

    user_id_local = author.id
    user_rank_local = next((i + 1 for i, u in enumerate(users_sorted_local) if u["id"] == user_id_local), None)
    user_stats_local = next((u for u in users_sorted_local if u["id"] == user_id_local), None)
    percent_local = (user_rank_local / len(users_sorted_local) * 100) if user_rank_local and len(users_sorted_local) > 0 else None
    percent_text_local = f"Top {percent_local:.2f}%" if percent_local is not None else "N/A"

    current_page_users = users_sorted_local[start_local:end_local]
    rankings_text_local = "\n".join(
        f"**#{i + start_local + 1}** {get_aura_username(ctx, user['id'])}"
        f"\n-# {savage_cash_emoji} Net Worth: {user['net_worth']:,}"
        for i, user in enumerate(current_page_users)
    ) if current_page_users else "No users to show."
    user_stats_text = (
        f"{savage_cash_emoji} Net Worth: {user_stats_local['net_worth']:,}"
        if user_stats_local
        else "Net Worth: N/A"
    )
    stats_text = (
        "# 🎮 NetWorth Leaderboard 🎮 \n"
        f"**🎮 {author.mention} Current Stats**\n"
        f"-# **🎮 Rank: {user_rank_local if user_rank_local else 'N/A'} ({percent_text_local})**\n"
        f"-# **{user_stats_text}**"
    )
    rankings_text = (
        f"### 🎮 Rankings (Page {page}/{total_pages_local})\n"
        f"{rankings_text_local}\n\n"
        f"-# Page: {page}/{total_pages_local} • Last Updated: <t:{int(time.time())}:R> • Total players: {len(users_sorted_local)}"
    )
    return stats_text, rankings_text


def create_aura_leaderboard_content(ctx, page, author):
    users_sorted_local = get_aura_users()
    per_page_local = 10
    total_pages_local = max(1, math.ceil(len(users_sorted_local) / per_page_local))
    page = max(1, min(page, total_pages_local))
    start_local = (page - 1) * per_page_local
    end_local = start_local + per_page_local

    user_id_local = author.id
    user_rank_local = next((i + 1 for i, u in enumerate(users_sorted_local) if u["id"] == user_id_local), None)
    user_stats_local = next((u for u in users_sorted_local if u["id"] == user_id_local), None)
    current_page_users = users_sorted_local[start_local:end_local]
    rankings_text_local = "\n".join(
        [
            f"**#{i + start_local + 1}** {get_aura_username(ctx, user['id'])}"
            f"\n-# 🎮 AURA: {user['aura']}"
            for i, user in enumerate(current_page_users)
        ]
    ) if current_page_users else "No users to show."
    stats_text = (
        "# 🎮 Aura Leaderboard 🎮\n"
        f"### **🎮 {author.mention} AURA Stats**\n"
        f"-#🎮 Rank : {user_rank_local if user_rank_local else 'N/A'}\n"
        f"-#🎮 AURA : {user_stats_local['aura'] if user_stats_local else 'N/A'}"
    )
    rankings_text = (
        f"### 🎮 AURA Rankings (Page {page}/{total_pages_local})\n"
        f"{rankings_text_local}\n\n"
        f"-# Page: {page}/{total_pages_local} • Last Updated: <t:{int(time.time())}:R> • Total players: {len(users_sorted_local)}"
    )
    return stats_text, rankings_text


class NetWorthLeaderboardView(discord.ui.LayoutView):
    def __init__(self, ctx, page, author=None):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.page = page
        self.author = author or ctx.author
        self.total_pages = max(1, math.ceil(len(get_agreed_cash_users()) / 10))

        back_button = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, disabled=page <= 1)
        aura_button = discord.ui.Button(label="AURA", style=discord.ButtonStyle.primary)
        next_button = discord.ui.Button(label="Next", style=discord.ButtonStyle.secondary, disabled=page >= self.total_pages)
        back_button.callback = self.back
        aura_button.callback = self.open_aura
        next_button.callback = self.next

        stats_text, rankings_text = create_leaderboard_content(ctx, page, self.author)
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(stats_text),
            discord.ui.Separator(),
            discord.ui.TextDisplay(rankings_text),
            discord.ui.Separator(),
            discord.ui.ActionRow(back_button, aura_button, next_button),
            accent_colour=discord.Color.blue(),
        ))

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Only the leaderboard owner can change pages.", ephemeral=True)
            return False
        return True

    async def back(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            attachments=[],
            view=NetWorthLeaderboardView(self.ctx, self.page - 1, interaction.user),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def next(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            attachments=[],
            view=NetWorthLeaderboardView(self.ctx, self.page + 1, interaction.user),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def open_aura(self, interaction: discord.Interaction):
        aura_total_pages = max(1, math.ceil(len(get_aura_users()) / 10))
        aura_page = min(self.page, aura_total_pages)
        await interaction.response.edit_message(
            content=None,
            embed=None,
            attachments=[],
            view=AuraLeaderboardView(self.ctx, aura_page, self.page, interaction.user),
            allowed_mentions=discord.AllowedMentions.none(),
        )


class AuraLeaderboardView(discord.ui.LayoutView):
    def __init__(self, ctx, page, net_worth_page, author=None):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.page = page
        self.net_worth_page = net_worth_page
        self.author = author or ctx.author
        self.total_pages = max(1, math.ceil(len(get_aura_users()) / 10))

        back_button = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, disabled=page <= 1)
        next_button = discord.ui.Button(label="Next", style=discord.ButtonStyle.secondary, disabled=page >= self.total_pages)
        net_worth_button = discord.ui.Button(label="NetWorth", style=discord.ButtonStyle.primary)
        back_button.callback = self.back
        next_button.callback = self.next
        net_worth_button.callback = self.open_net_worth

        stats_text, rankings_text = create_aura_leaderboard_content(ctx, page, self.author)
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(stats_text),
            discord.ui.Separator(),
            discord.ui.TextDisplay(rankings_text),
            discord.ui.Separator(),
            discord.ui.ActionRow(back_button, net_worth_button, next_button),
            accent_colour=discord.Color.blue(),
        ))

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Only the leaderboard owner can change pages.", ephemeral=True)
            return False
        return True

    async def back(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            attachments=[],
            view=AuraLeaderboardView(self.ctx, self.page - 1, self.net_worth_page, interaction.user),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def next(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            attachments=[],
            view=AuraLeaderboardView(self.ctx, self.page + 1, self.net_worth_page, interaction.user),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def open_net_worth(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            attachments=[],
            view=NetWorthLeaderboardView(self.ctx, self.net_worth_page, interaction.user),
            allowed_mentions=discord.AllowedMentions.none(),
        )