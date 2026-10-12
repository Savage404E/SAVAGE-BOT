"""Fishing game command."""

import builtins
import random
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord

from commands import _legacy_command

savage_cash_emoji = getattr(builtins, "savage_cash_emoji", "🎮")

if TYPE_CHECKING:
    bot: Any
    db_get: Any
    db_set: Any
    get_user_data: Any
    load_users: Any
    save_user_data: Any
    save_users: Any


# fish command
# User-preferred location is stored per user. Use !location to set/change fishing spot.

APP_WAVE2_EMOJI = "🎮"
SERVER_WAVE2_EMOJI = "🎮"
FISH_COOLDOWN_SECONDS = 60
FISH_MARKER = "🐟"

FISH_TYPES = {
    "common": {
        "fish": [
            "🎮",
            "🎮",
            "🎮",
            "🎮"
        ],
        "value_range": (10, 50),
        "weight": 50,
    },
    "uncommon": {
        "fish": [
            "🎮",
            "🎮",
            "🎮",
            "🎮"
        ],
        "value_range": (100, 500),
        "weight": 30,
    },
    "rare": {
        "fish": [
            "🎮",
            "🎮",
            "🎮",
            "🎮"
        ],
        "value_range": (1000, 5000),
        "weight": 15,
    },
    "epic": {
        "fish": [
            "🎮",
            "🎮",
            "🎮"
        ],
        "value_range": (8000, 15000),
        "weight": 1,
    },
    # Legendary fish can only be found in the Abyss; NOT part of any other location pools.
    "legendary": {
        "fish": [
            "🎮",
            "🎮",
            "🎮"
        ],
        "value_range": (30000, 50000),
        "weight": 1,
        "only_in": ["abyss"],
    }
}

FISH_LOCATION_IMAGES = {
    "pond": "https://raw.githubusercontent.com/Savage404E/SAVAGE-BOT/refs/heads/main/game_art/Quiet%20Pond.webp",
    "river": "https://raw.githubusercontent.com/Savage404E/SAVAGE-BOT/refs/heads/main/game_art/Flowing%20River.jpg",
    "ocean": "https://raw.githubusercontent.com/Savage404E/SAVAGE-BOT/refs/heads/main/game_art/Deep%20Ocean.jpg",
    "abyss": "https://raw.githubusercontent.com/Savage404E/SAVAGE-BOT/refs/heads/main/game_art/Abyssal%20Depths.jpg",
}

def is_abyss_available_now():
    """Abyssal Depths is available only on Sunday (UTC)."""
    return datetime.utcnow().weekday() == 6


FISHING_LOCATIONS = {
    "pond": {
        "name": f"{SERVER_WAVE2_EMOJI} Quiet Pond",
        "description": "A peaceful pond with common fish",
        "fish_pool": ["common", "uncommon"],
        "cost": 0
    },
    "river": {
        "name": f"{SERVER_WAVE2_EMOJI} Flowing River",
        "description": "A flowing river with better fish",
        "fish_pool": ["common", "uncommon", "rare"],
        "cost": 10000  # Only charged when changing to this location, see !location logic
    },
    "ocean": {
        "name": f"{SERVER_WAVE2_EMOJI} Deep Ocean",
        "description": "The deep ocean with rare catches",
        "fish_pool": ["common","uncommon", "rare", "epic"],
        "cost": 50000
    },
    "abyss": {
        "name": f"{SERVER_WAVE2_EMOJI} Abyssal Depths",
        "description": "Mysterious depths with legendary fish",
        "fish_pool": ["common","uncommon","rare", "epic", "legendary"],
        "cost": 100000,
        "availability_check": is_abyss_available_now,
        "unavailable_msg": "🕑 The Abyssal Depths is open only on Sunday (UTC). Use `!location` to select another spot!"
    }
}

def load_fish_cooldowns():
    return db_get("fish_cooldowns", {})

def save_fish_cooldowns(data):
    db_set("fish_cooldowns", data)

def load_fish_location_cooldowns():
    return db_get("fish_location_cooldowns", {})

def save_fish_location_cooldowns(data):
    db_set("fish_location_cooldowns", data)

def load_fishing_location_prefs():
    return db_get("fish_location_prefs", {})

def save_fishing_location_prefs(data):
    db_set("fish_location_prefs", data)

def get_fishing_location(user_id):
    """Return the user's fishing location, defaulting new users to Quiet Pond."""
    user_id = str(user_id)
    prefs = load_fishing_location_prefs()
    location = prefs.get(user_id)
    if location not in FISHING_LOCATIONS:
        location = "pond"
        prefs[user_id] = location
        save_fishing_location_prefs(prefs)
    if location == "abyss" and not is_abyss_available_now():
        prefs[user_id] = "pond"
        save_fishing_location_prefs(prefs)
        return "pond"
    return location

def get_fish_by_rarity(rarity):
    """Get a random fish from the specified rarity"""
    if rarity not in FISH_TYPES:
        return None, None
    fish_list = FISH_TYPES[rarity]["fish"]
    fish_name = random.choice(fish_list)
    value_range = FISH_TYPES[rarity]["value_range"]
    value = random.randint(value_range[0], value_range[1])
    return fish_name, value

def select_fish_from_location(location_key):
    """Select a fish based on location's fish pool and weights"""
    location = FISHING_LOCATIONS.get(location_key, FISHING_LOCATIONS["pond"])
    fish_pool = location["fish_pool"]
    weights = []
    rarities = []
    for rarity in fish_pool:
        if rarity in FISH_TYPES:
            weights.append(FISH_TYPES[rarity]["weight"])
            rarities.append(rarity)
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]
    selected_rarity = random.choices(rarities, weights=normalized_weights)[0]
    fish_name, value = get_fish_by_rarity(selected_rarity)
    return fish_name, value, selected_rarity

def get_fish_collection(user_id):
    """Get user's fish collection"""
    users_data = load_users()
    user = get_user_data(users_data, int(user_id), None)
    return user.get("fish_collection", [])

def add_fish_to_collection(user_id, fish_name, rarity):
    """Add fish to user's collection"""
    users_data = load_users()
    user = get_user_data(users_data, int(user_id), None)
    if "fish_collection" not in user:
        user["fish_collection"] = []
    
    # Check if fish is already in collection
    for fish in user["fish_collection"]:
        if fish["name"] == fish_name:
            fish["count"] += 1
            break
    else:
        # Add new fish to collection
        user["fish_collection"].append({
            "name": fish_name,
            "rarity": rarity,
            "count": 1,
            "first_caught": time.time()
        })
    
    save_users(users_data)

def get_fish_collection_stats(user_id):
    """Get user's fish collection statistics"""
    collection = get_fish_collection(user_id)
    total_fish = sum(fish["count"] for fish in collection)
    unique_fish = len(collection)
    
    rarity_counts = {"common": 0, "uncommon": 0, "rare": 0, "epic": 0, "legendary": 0}
    for fish in collection:
        rarity_counts[fish["rarity"]] += fish["count"]
    
    return {
        "total_fish": total_fish,
        "unique_fish": unique_fish,
        "rarity_counts": rarity_counts
    }


def to_superscript(value: int) -> str:
    """Convert a count into superscript digits to match the inventory display style."""
    digits = str(value)
    sup_map = {
        "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
        "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    }
    return "".join(sup_map.get(ch, ch) for ch in digits)

# Always use the animated wave emoji 🎮, not Unicode.
def get_wave2_emoji(bot, guild):  # Arguments kept for code compatibility
    return "🎮"


def build_fish_dashboard_embed(user_id: str):
    """Create the main fish dashboard embed for a user."""
    location = get_fishing_location(user_id)
    stats = get_fish_collection_stats(user_id)
    water_emoji = SERVER_WAVE2_EMOJI
    location_text = f"{FISHING_LOCATIONS[location]['name'].replace(SERVER_WAVE2_EMOJI, water_emoji)}" if location else "Not set"

    embed = discord.Embed(
        title="🎮 IT'S TIME TO DO SOME FISHING",
        description="🎣 Welcome to the fishing system! Choose your action below.",
        color=discord.Color.blue()
    )
    embed.set_image(url=FISH_LOCATION_IMAGES.get(location, FISH_LOCATION_IMAGES["pond"]))

    embed.add_field(
        name=f"🎮 | FISH COLLECTED : {stats['total_fish']}/50",
        value=f"Unique Species: {stats['unique_fish']}",
        inline=False
    )

    embed.add_field(
        name=f"🎮 | location : {location_text}",
        value="Ready to fish!",
        inline=False
    )

    return embed


class FishingLocationView(discord.ui.View):
    """View for selecting fishing location (for !location), charge cost only to change location."""
    def __init__(self, ctx_or_interaction, pref_data):
        super().__init__(timeout=60)
        self.ctx_or_interaction = ctx_or_interaction
        self.pref_data = pref_data
        # Handle both ctx and interaction objects
        if hasattr(ctx_or_interaction, 'author'):
            self.user_id = str(ctx_or_interaction.author.id)
        else:
            self.user_id = str(ctx_or_interaction.user.id)
        self.prev_loc = pref_data.get(self.user_id, None)
        for loc_key, loc_data in FISHING_LOCATIONS.items():
            location_name = loc_data["name"].replace(SERVER_WAVE2_EMOJI, "").strip()
            label = f"{location_name} ({loc_data['cost']})" if loc_data['cost'] > 0 else location_name
            style = discord.ButtonStyle.green
            disabled = False
            button = discord.ui.Button(
                label=label,
                style=style,
                emoji=savage_cash_emoji if loc_data["cost"] > 0 else "🎮",
                disabled=disabled,
            )
            async def button_callback(interaction, loc_key=loc_key):
                # Get user mention based on object type
                if hasattr(self.ctx_or_interaction, 'author'):
                    user_mention = self.ctx_or_interaction.author.mention
                    guild = self.ctx_or_interaction.guild
                else:
                    user_mention = self.ctx_or_interaction.user.mention
                    guild = self.ctx_or_interaction.guild
                    
                if str(interaction.user.id) != self.user_id:
                    await interaction.response.send_message("Only you can pick your fishing spot!", ephemeral=True)
                    return

                cooldowns = load_fish_location_cooldowns()
                now = time.time()
                last_change = cooldowns.get(self.user_id, 0)
                if now - last_change < FISH_COOLDOWN_SECONDS:
                    left = int(FISH_COOLDOWN_SECONDS - (now - last_change))
                    await interaction.response.send_message(
                        f"⏳ You must wait `{left}s` before changing your fishing location again.",
                        ephemeral=True,
                    )
                    return

                if loc_key == "abyss" and not is_abyss_available_now():
                    await interaction.response.send_message(
                        "🕑 The Abyssal Depths unlocks only on Sunday (UTC). Pick another location for now.",
                        ephemeral=True,
                    )
                    return
                prev_loc = self.pref_data.get(self.user_id, None)
                if prev_loc == loc_key:
                    spot = FISHING_LOCATIONS[loc_key]
                    embed = discord.Embed(
                        title="📍 Fishing Location Already Set!",
                        description=f"{user_mention}, your fishing spot is already:\n\n**{spot['name']}**\n{spot['description']}",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text="Use !fish to start fishing here. Use !location to change.")
                    await interaction.response.edit_message(embed=embed, view=FishMenuView(self.ctx_or_interaction))
                    return
                # Only charge if new location has a cost
                cost = FISHING_LOCATIONS[loc_key]["cost"]
                users_data = load_users()
                user = get_user_data(users_data, int(self.user_id), guild.id)
                if cost > 0:
                    economy = user.get("economy", {})
                    if economy.get("cash", 0) < cost:
                        await interaction.response.send_message(
                            f"💸 You need {cost}{savage_cash_emoji} to set your fishing location to {FISHING_LOCATIONS[loc_key]['name']}. You have {economy.get('cash', 0)}{savage_cash_emoji}.",
                            ephemeral=True
                        )
                        return
                    economy["cash"] = economy.get("cash", 0) - cost
                    save_user_data(user, int(self.user_id), guild.id)
                self.pref_data[self.user_id] = loc_key
                save_fishing_location_prefs(self.pref_data)
                cooldowns[self.user_id] = now
                save_fish_location_cooldowns(cooldowns)
                updated_embed = build_fish_dashboard_embed(self.user_id)
                await interaction.response.edit_message(embed=updated_embed, view=FishMenuView(self.ctx_or_interaction))
            button.callback = button_callback
            self.add_item(button)

# Old location command removed - functionality now integrated into the main fish command with buttons

# ======================================
# Animated "lower the hook" mini-game where hook descends, with obstacles
# ======================================
import copy

class FishingHookView(discord.ui.View):
    """Fishing mini-game: Hook down to the fish, dodging obstacles!"""
    OBSTACLE_EMOJIS = ["🪨", "🧱", "🪵", "🪙", "🦀", "🐚"]
    EMPTY_EMOJI = None   # set to the water emoji at runtime
    HOOK_EMOJI = "🎣"
    MOVE_LEFT = -1
    MOVE_RIGHT = 1
    MOVE_DOWN = 0

    def __init__(self, ctx, user, data, fish_name, fish_value, rarity, fishing_spot):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.user = user
        self.users_data = data
        self.fish_name = fish_name
        self.fish_value = fish_value
        self.rarity = rarity
        self.fishing_spot = fishing_spot
        self.caught = False
        self.failed = False
        self.EMPTY_EMOJI = SERVER_WAVE2_EMOJI

        # Difficulty params
        if self.rarity in ["epic", "legendary"]:
            self.ROWS = 7
            self.MAX_MOVES = 12
            self.LANE_LENGTH = 9
            self.obstacle_rows = 5
        elif self.rarity in ["rare"]:
            self.ROWS = 6
            self.MAX_MOVES = 10
            self.LANE_LENGTH = 9
            self.obstacle_rows = 4
        else:
            self.ROWS = 5
            self.MAX_MOVES = 8
            self.LANE_LENGTH = 7
            self.obstacle_rows = 3

        self.fish_col = random.randint(0, self.LANE_LENGTH - 1)
        self.fish_row = self.ROWS - 1

        self.hook_row = 0
        self.hook_col = random.randint(0, self.LANE_LENGTH - 1)
        self.moves_left = self.MAX_MOVES
        self.message = None

        self.grid = self._generate_grid_with_obstacles()

        self._add_buttons()

    def _generate_grid_with_obstacles(self):
        grid = [[self.EMPTY_EMOJI for _ in range(self.LANE_LENGTH)] for _ in range(self.ROWS)]
        grid[self.fish_row][self.fish_col] = FISH_MARKER  # Hide fish name during play
        
        # Ensure at least one clear path exists from hook start to fish
        # Create a guaranteed path: ensure the fish column has no obstacles in critical rows
        # Keep fish row clear except for the fish itself
        for row in range(1, self.ROWS - 1):
            # Ensure fish column has at least some clear spaces
            if row % 2 == 0:  # Every other row in fish column is clear
                if grid[row][self.fish_col] == self.EMPTY_EMOJI:
                    pass  # Keep it clear
        
        num_obstacles = random.randint(
            self.obstacle_rows * (self.LANE_LENGTH // 4),  # Reduced obstacle count
            self.obstacle_rows * (self.LANE_LENGTH // 3)  # Reduced max obstacles
        )
        placed = 0
        attempts = 0
        max_attempts = num_obstacles * 10
        
        while placed < num_obstacles and attempts < max_attempts:
            attempts += 1
            row = random.randint(1, self.ROWS - 2)
            col = random.randint(0, self.LANE_LENGTH - 1)
            
            # Don't place obstacles in fish column on every other row (ensures path)
            if col == self.fish_col and row % 2 == 0:
                continue
            
            # Don't place obstacles directly blocking the path from hook to fish
            # Allow some obstacles but ensure there's always a way through
            if grid[row][col] == self.EMPTY_EMOJI and not (row == self.fish_row and col == self.fish_col):
                grid[row][col] = random.choice(self.OBSTACLE_EMOJIS)
                placed += 1
        
        return grid

    def reset_buttons_and_update(self):
        self.clear_items()
        # Allow horizontal movement on fish row if not aligned and moves left
        # Disable buttons only if: at edge, failed/caught, or no moves left
        left_disabled = (self.hook_col <= 0) or self.failed or self.caught or (self.moves_left <= 0)
        right_disabled = (self.hook_col >= self.LANE_LENGTH - 1) or self.failed or self.caught or (self.moves_left <= 0)
        # Disable down if at bottom row (fish row) OR if already caught/failed OR if out of moves
        down_disabled = (self.hook_row >= self.ROWS - 1) or self.failed or self.caught or (self.moves_left <= 0)
        btn_left = discord.ui.Button(label="⬅️", style=discord.ButtonStyle.secondary, disabled=left_disabled, row=0)
        btn_down = discord.ui.Button(label="⬇️ Lower Hook", style=discord.ButtonStyle.success, emoji=self.HOOK_EMOJI, disabled=down_disabled, row=0)
        btn_right = discord.ui.Button(label="➡️", style=discord.ButtonStyle.secondary, disabled=right_disabled, row=0)

        async def move_left_callback(interaction):
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message("That's not your fishing game!", ephemeral=True)
                return
            if self.failed or self.caught:
                await interaction.response.defer()
                return
            if self.moves_left <= 0:
                self.failed = True
                self.disable_all()
                await self.send_fail_embed(interaction, reason="you ran out of moves!\n")
                self.stop()
                return
            if self.hook_col > 0:
                self.hook_col -= 1
                self.moves_left -= 1
                # Check if we're now aligned with fish on fish row
                if self.hook_row == self.fish_row and self.hook_col == self.fish_col:
                    self.caught = True
                    self.users_data = load_users()
                    self.user = get_user_data(self.users_data, self.ctx.author.id, self.ctx.guild.id)
                    economy = self.user.setdefault("economy", {})
                    economy["cash"] = economy.get("cash", 0) + self.fish_value
                    # Add fish to collection
                    add_fish_to_collection(str(self.ctx.author.id), self.fish_name, self.rarity)
                    save_users(self.users_data)
                    rarity_emojis = {
                        "common": "⚪", "uncommon": "🟢", "rare": "🔵", "epic": "🟣", "legendary": "🟡"
                    }
                    rarity_emoji = rarity_emojis.get(self.rarity, "⚪")
                    win_embed = discord.Embed(
                        title="🎣 Fish Caught!",
                        description=f'{self.ctx.author.mention} caught: {rarity_emoji} **{self.fish_name}**!\n💰 **+{self.fish_value} cash**\n\n{self.fishing_spot["name"]}',
                        color=discord.Color.gold()
                    )
                    win_embed.set_footer(text=f"Rarity: {self.rarity.upper()}")
                    self.disable_all()
                    await interaction.response.edit_message(embed=win_embed, view=self)
                    self.stop()
                    return
            await self.update_state(interaction)

        async def move_right_callback(interaction):
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message("That's not your fishing game!", ephemeral=True)
                return
            if self.failed or self.caught:
                await interaction.response.defer()
                return
            if self.moves_left <= 0:
                self.failed = True
                self.disable_all()
                await self.send_fail_embed(interaction, reason="you ran out of moves!\n")
                self.stop()
                return
            if self.hook_col < self.LANE_LENGTH - 1:
                self.hook_col += 1
                self.moves_left -= 1
                # Check if we're now aligned with fish on fish row
                if self.hook_row == self.fish_row and self.hook_col == self.fish_col:
                    self.caught = True
                    self.users_data = load_users()
                    self.user = get_user_data(self.users_data, self.ctx.author.id, self.ctx.guild.id)
                    economy = self.user.setdefault("economy", {})
                    economy["cash"] = economy.get("cash", 0) + self.fish_value
                    # Add fish to collection
                    add_fish_to_collection(str(self.ctx.author.id), self.fish_name, self.rarity)
                    save_users(self.users_data)
                    rarity_emojis = {
                        "common": "⚪", "uncommon": "🟢", "rare": "🔵", "epic": "🟣", "legendary": "🟡"
                    }
                    rarity_emoji = rarity_emojis.get(self.rarity, "⚪")
                    win_embed = discord.Embed(
                        title="🎣 Fish Caught!",
                        description=f'{self.ctx.author.mention} caught: {rarity_emoji} **{self.fish_name}**!\n💰 **+{self.fish_value} cash**\n\n{self.fishing_spot["name"]}',
                        color=discord.Color.gold()
                    )
                    win_embed.set_footer(text=f"Rarity: {self.rarity.upper()}")
                    self.disable_all()
                    await interaction.response.edit_message(embed=win_embed, view=self)
                    self.stop()
                    return
            await self.update_state(interaction)

        async def move_down_callback(interaction):
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message("That's not your fishing game!", ephemeral=True)
                return
            if self.failed or self.caught:
                await interaction.response.defer()
                return
            if self.hook_row + 1 >= self.ROWS:
                await self.update_state(interaction)
                return
            cell_below = self.grid[self.hook_row + 1][self.hook_col]
            if cell_below in self.OBSTACLE_EMOJIS:
                self.hook_row += 1
                self.moves_left -= 1
                self.failed = True
                self.disable_all()
                await self.send_fail_embed(interaction, reason=f"Oh no! Your hook hit an obstacle {cell_below} and snapped!\n")
                self.stop()
                return
            # Check if the next position is the fish (by coordinate, not by what's currently rendered)
            elif self.hook_row + 1 == self.fish_row and self.hook_col == self.fish_col:
                self.hook_row += 1
                self.moves_left -= 1
                self.caught = True
                self.users_data = load_users()
                self.user = get_user_data(self.users_data, self.ctx.author.id, self.ctx.guild.id)
                economy = self.user.setdefault("economy", {})
                economy["cash"] = economy.get("cash", 0) + self.fish_value
                # Add fish to collection
                add_fish_to_collection(str(self.ctx.author.id), self.fish_name, self.rarity)
                save_users(self.users_data)
                rarity_emojis = {
                    "common": "⚪", "uncommon": "🟢", "rare": "🔵", "epic": "🟣", "legendary": "🟡"
                }
                rarity_emoji = rarity_emojis.get(self.rarity, "⚪")
                win_embed = discord.Embed(
                    title="🎣 Fish Caught!",
                    description=f'{self.ctx.author.mention} caught: {rarity_emoji} **{self.fish_name}**!\n💰 **+{self.fish_value} cash**\n\n{self.fishing_spot["name"]}',
                    color=discord.Color.gold()
                )
                win_embed.set_footer(text=f"Rarity: {self.rarity.upper()}")
                self.disable_all()
                await interaction.response.edit_message(embed=win_embed, view=self)
                self.stop()
                return
            else:
                self.hook_row += 1
                self.moves_left -= 1
            await self.update_state(interaction)

        btn_left.callback = move_left_callback
        btn_down.callback = move_down_callback
        btn_right.callback = move_right_callback

        self.add_item(btn_left)
        self.add_item(btn_down)
        self.add_item(btn_right)

    def _add_buttons(self):
        self.reset_buttons_and_update()

    def render_grid(self):
        render = copy.deepcopy(self.grid)
        # If hook and fish in same spot on fish row (i.e., caught), overlay real fish name. Only reveal on catch (caught == True)
        if self.hook_row == self.fish_row and self.hook_col == self.fish_col:
            # If caught (or failed), show fish name, else keep the fish marker.
            if self.caught or self.failed:
                render[self.hook_row][self.hook_col] = self.HOOK_EMOJI + self.fish_name
            else:
                render[self.hook_row][self.hook_col] = self.HOOK_EMOJI + FISH_MARKER
        else:
            render[self.hook_row][self.hook_col] = self.HOOK_EMOJI
        # All blank spaces are always <a:wave2:...> emoji.
        lines = [" ".join(r) for r in render]
        return "\n".join(lines)

    def get_lane_str(self):
        return self.render_grid()

    async def interaction_check(self, interaction):
        return interaction.user.id == self.ctx.author.id

    def disable_all(self):
        for item in self.children:
            item.disabled = True

    async def on_timeout(self):
        self.disable_all()
        if not self.caught and not self.failed:
            await self.send_fail_embed(None, timeout=True)
        self.stop()

    async def send_fail_embed(self, interaction=None, reason="", timeout=False):
        em = discord.Embed(
            title="🎣 Fish Escaped!" if not timeout else "🎣 Fish Got Away!",
            description=(
                f"{self.ctx.author.mention}, " +
                (reason if reason else "you failed to catch the fish!\n") +
                f"The {self.fish_name} swam away...\n\n"
                f"!location - to shift to other ocean or a lake .\n\n"
                f"{self.fishing_spot['name']}"
            ),
            color=discord.Color.red()
        )
        em.set_footer(text="Try again next time! (Dodge obstacles and align with the fish)")
        try:
            target_msg = self.message
            if interaction:
                await interaction.response.edit_message(embed=em, view=self)
            elif target_msg:
                await target_msg.edit(embed=em, view=self)
        except Exception:
            pass

    async def update_state(self, interaction):
        self.reset_buttons_and_update()
        if self.caught or self.failed:
            return  # Already handled

        if self.moves_left <= 0:
            # Only fail if not aligned with fish
            if not (self.hook_row == self.fish_row and self.hook_col == self.fish_col):
                self.failed = True
                self.disable_all()
                await self.send_fail_embed(interaction, reason="you ran out of moves!\n")
                self.stop()
                return
            # If aligned but moves are 0, they should have already won, but check anyway
            elif self.hook_row == self.fish_row and self.hook_col == self.fish_col:
                self.caught = True
                self.users_data = load_users()
                self.user = get_user_data(self.users_data, self.ctx.author.id, self.ctx.guild.id)
                economy = self.user.setdefault("economy", {})
                economy["cash"] = economy.get("cash", 0) + self.fish_value
                # Add fish to collection
                add_fish_to_collection(str(self.ctx.author.id), self.fish_name, self.rarity)
                save_users(self.users_data)
                rarity_emojis = {
                    "common": "⚪", "uncommon": "🟢", "rare": "🔵", "epic": "🟣", "legendary": "🟡"
                }
                rarity_emoji = rarity_emojis.get(self.rarity, "⚪")
                win_embed = discord.Embed(
                    title="🎣 Fish Caught!",
                    description=f'{self.ctx.author.mention} caught: {rarity_emoji} **{self.fish_name}**!\n💰 **+{self.fish_value} cash**\n\n{self.fishing_spot["name"]}',
                    color=discord.Color.gold()
                )
                win_embed.set_footer(text=f"Rarity: {self.rarity.upper()}")
                self.disable_all()
                try:
                    await interaction.response.edit_message(embed=win_embed, view=self)
                except:
                    if self.message:
                        await self.message.edit(embed=win_embed, view=self)
                self.stop()
                return
        
        # Removed the auto-fail when reaching fish row but not aligned
        # Players can now move horizontally on the fish row to align with the fish

        lane_str = self.get_lane_str()
        emoji_tip = f"{self.HOOK_EMOJI} = Hook | {FISH_MARKER} = Fish | {'/'.join(self.OBSTACLE_EMOJIS[:2])} = Obstacles"
        details = (
            f"Dodge obstacles as you steer your hook to the fish below!\n"
            f"{emoji_tip}\n"
            f"Steer ⬅️ or ➡️, or use ⬇️ to drop the hook to the next row.\n"
            f"Moves left: **{self.moves_left}**"
        )
        embed = discord.Embed(
            title=f"🎣 {self.fishing_spot['name']}",
            description=f"{lane_str}\n\n{details}",
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Line up with the fish and lower the hook. Don't hit obstacles!")
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.InteractionResponded:
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self)

class FishCollectionView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=300)
        self.ctx = ctx

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji="⬅️", row=0)
    async def back_to_dashboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only you can use these buttons!", ephemeral=True)
            return

        embed = build_fish_dashboard_embed(str(interaction.user.id))
        await interaction.response.edit_message(embed=embed, view=FishMenuView(self.ctx))


# Main Fish Menu View with buttons
class FishMenuView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=300)
        self.ctx = ctx
        
    @discord.ui.button(label="GO FISHING", style=discord.ButtonStyle.primary, emoji="🎮", row=0)
    async def go_fishing(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only you can use these buttons!", ephemeral=True)
            return
            
        user_id = str(interaction.user.id)
        now = time.time()
        users_data = load_users()
        user = get_user_data(users_data, interaction.user.id, interaction.guild.id)
        location = get_fishing_location(user_id)
            
        cooldowns = load_fish_cooldowns()
        last = cooldowns.get(user_id, 0)
        if now - last < FISH_COOLDOWN_SECONDS:
            left = int(FISH_COOLDOWN_SECONDS - (now - last))
            await interaction.response.send_message(f"⏳ You must wait `{left}s` before fishing again.", ephemeral=True)
            return
            
        if location == "abyss" and not is_abyss_available_now():
            await interaction.response.send_message(
                "🕑 The Abyssal Depths unlocks only on Sunday (UTC). Please pick another location.",
                ephemeral=True,
            )
            return

        fishing_spot = FISHING_LOCATIONS[location]
        play_cost = 30   # Fixed cost to play at any location
        economy = user.get("economy", {})
        if economy.get("cash", 0) < play_cost:
            await interaction.response.send_message(f"💸 You need {play_cost} cash to fish. You have {economy.get('cash', 0)} cash.", ephemeral=True)
            return
            
        economy["cash"] = economy.get("cash", 0) - play_cost
        save_users(users_data)
        fish_name, fish_value, rarity = select_fish_from_location(location)
        rarity_emojis = {
            "common": "⚪", "uncommon": "🟢", "rare": "🔵", "epic": "🟣", "legendary": "🟡"
        }
        rarity_emoji = rarity_emojis.get(rarity, "⚪")
        view = FishingHookView(self.ctx, user, users_data, fish_name, fish_value, rarity, fishing_spot)
        lane_display = view.get_lane_str()
        emoji_tip = f"🎣 = Hook | {FISH_MARKER} = Fish | {'/'.join(FishingHookView.OBSTACLE_EMOJIS[:2])} = Obstacles"
        intro = (
            f"🎮 {interaction.user.mention} is casting...\n"
            f"A fish appeared at the bottom of the water!\n"
            f"{lane_display}\n\n"
            f"{emoji_tip}\n"
            f"Moves left: **{view.moves_left}**"
        )
        embed = discord.Embed(
            title=f"{fishing_spot['name'].replace(SERVER_WAVE2_EMOJI, '').strip()}",
            description=intro,
            color=discord.Color.blue()
        )
        embed.set_footer(text="⬅️ ➡️ to steer, ⬇️ to lower. Get the hook on the fish and avoid all obstacles!")
        cooldowns[user_id] = now
        save_fish_cooldowns(cooldowns)
        await interaction.response.edit_message(embed=embed, view=view)
        view.message = await interaction.original_response()
        
    @discord.ui.button(label="SET LOCATION", style=discord.ButtonStyle.secondary, emoji="📍", row=0)
    async def set_location(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only you can use these buttons!", ephemeral=True)
            return
            
        pref_data = load_fishing_location_prefs()
        water_emoji = SERVER_WAVE2_EMOJI
        embed = discord.Embed(
            title="🎯 Choose Your Fishing Location",
            description="Pick your default fishing spot! This will be used for !fish until you change it.",
            color=discord.Color.blue()
        )
        for loc_key, loc_data in FISHING_LOCATIONS.items():
            cost_text = f"**{loc_data['cost']}{savage_cash_emoji}**" if loc_data['cost'] > 0 else "**FREE**"
            display_name = loc_data['name'].replace(SERVER_WAVE2_EMOJI, water_emoji)
            embed.description += f"• {display_name} - {cost_text}\n  {loc_data['description']}\n\n"
        embed.set_footer(text="You can use !fish after setting a location. Change anytime with !location. Cost is only charged to change!")
        view = FishingLocationView(self.ctx, pref_data)
        await interaction.response.edit_message(embed=embed, view=view)
        
    @discord.ui.button(label="Collections", style=discord.ButtonStyle.success, emoji="📚", row=0)
    async def view_collections(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only you can use these buttons!", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        collection = get_fish_collection(user_id)
        stats = get_fish_collection_stats(user_id)

        rarity_emojis = {"common": "⚪", "uncommon": "🟢", "rare": "🔵", "epic": "🟣", "legendary": "🟡"}

        embed = discord.Embed(
            title="🎣 Your Fish Collection",
            description=f"**Total Fish:** {stats['total_fish']} | **Unique Species:** {stats['unique_fish']}",
            color=discord.Color.blue()
        )

        # Show rarity breakdown
        rarity_text = ""
        for rarity, count in stats['rarity_counts'].items():
            if count > 0:
                emoji = rarity_emojis.get(rarity, "⚪")
                rarity_text += f"{emoji} {rarity.title()}: {count}\n"

        if rarity_text:
            embed.add_field(name="📊 Rarity Breakdown", value=rarity_text, inline=False)

        # Show the actual fish emoji in the collection, not the rarity color emoji.
        rarity_label_map = {
            "common": "Common",
            "uncommon": "Rare",
            "rare": "Epic",
            "epic": "Toxic",
            "legendary": "Legendary",
        }
        for rarity in ["common", "uncommon", "rare", "epic", "legendary"]:
            section_emoji = rarity_emojis.get(rarity, "⚪")
            entries = []
            fish_names = FISH_TYPES.get(rarity, {}).get("fish", [])
            for fish_name in fish_names:
                fish_emoji = fish_name.split()[0] if fish_name else "🐟"
                count = 0
                for fish in collection:
                    if fish.get("name") == fish_name:
                        count = fish.get("count", 0)
                        break
                entries.append(f"{fish_emoji}{to_superscript(count)}")

            if entries:
                embed.add_field(
                    name=f"{section_emoji} {rarity_label_map.get(rarity, rarity.title())}",
                    value=" ".join(entries),
                    inline=False,
                )

        if not any(FISH_TYPES.get(rarity, {}).get("fish", []) for rarity in ["common", "uncommon", "rare", "epic", "legendary"]):
            embed.add_field(name="🐟 Fish Collection", value="No fish are available in this pool yet.", inline=False)

        embed.set_footer(text=f"Collection progress: {stats['total_fish']}/50 fish")
        await interaction.response.edit_message(embed=embed, view=FishCollectionView(self.ctx))

@_legacy_command
async def fish(ctx):
    """
    🎣 Main fishing command with location system and collections
    Shows menu with GO FISHING, SET LOCATION, and Collections buttons
    """
    user_id = str(ctx.author.id)
    embed = build_fish_dashboard_embed(user_id)
    view = FishMenuView(ctx)
    await ctx.send(embed=embed, view=view)

