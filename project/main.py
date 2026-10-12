import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ext.commands import Bot
import logging
import random
import asyncio
from datetime import datetime, timedelta , timezone
from discord.ui import View, Button
from discord import ButtonStyle
import math
import time
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import os
import re
import logging
import traceback
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
from db import db_get, db_set, db_has, db_delete, migrate_to_normalized_schema

migrate_to_normalized_schema()

#================================================
#Weighted Probability Utilities
class WeightedRNG:
    @staticmethod
    def weighted_choice(items, weights):
        """Enhanced weighted selection with validation and fallback"""
        if not items or len(items) != len(weights):
            return random.choice(items) if items else None
        
        total = sum(weights)
        if total == 0:
            return random.choice(items)
        
        # Normalize weights
        normalized_weights = [w/total for w in weights]
        return random.choices(items, weights=normalized_weights, k=1)[0]
    
    @staticmethod
    def weighted_outcome(outcomes_config):
        """
        outcomes_config: {
            "outcome1": {"weight": 40, "value": 100},
            "outcome2": {"weight": 30, "value": 50},
            "outcome3": {"weight": 30, "value": 0}
        }
        """
        outcomes = list(outcomes_config.keys())
        weights = [outcomes_config[outcome]["weight"] for outcome in outcomes]
        
        selected = WeightedRNG.weighted_choice(outcomes, weights)
        return selected, outcomes_config[selected]["value"]
    
    @staticmethod
    def adaptive_weighted_choice(base_weights, user_win_rate=None):
        """Adjust weights based on user performance"""
        if user_win_rate is None:
            return base_weights
        
        # If user is winning too much, reduce good outcomes
        if user_win_rate > 0.7:
            adjusted_weights = []
            for i, weight in enumerate(base_weights):
                # Reduce weight of better outcomes (assuming they come first)
                adjustment = 0.7 if i < len(base_weights) // 2 else 1.3
                adjusted_weights.append(weight * adjustment)
            return adjusted_weights
        
        # If user is losing too much, boost good outcomes
        elif user_win_rate < 0.3:
            adjusted_weights = []
            for i, weight in enumerate(base_weights):
                # Boost weight of better outcomes
                adjustment = 1.3 if i < len(base_weights) // 2 else 0.7
                adjusted_weights.append(weight * adjustment)
            return adjusted_weights
        
        return base_weights

# Enable comprehensive logging for hosting environment
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set Discord.py to show all errors
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.DEBUG)

# Show all uncaught exceptions
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))
    traceback.print_exception(exc_type, exc_value, exc_traceback)

sys.excepthook = handle_exception

# Log startup message
logging.info("=== SAVAGE BOT STARTING UP ===")
logging.info("Enhanced logging enabled for hosting environment")
logging.info("All errors and exceptions will be logged")

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# override=True so values from .env replace any stale DISCORD_* vars in the OS environment
_parent_env = os.path.join(os.path.dirname(_BASE_DIR), ".env")
_local_env = os.path.join(_BASE_DIR, ".env")
if os.path.isfile(_parent_env):
    load_dotenv(_parent_env, encoding="utf-8", override=True)
if os.path.isfile(_local_env):
    load_dotenv(_local_env, encoding="utf-8", override=True)

# Test database connection on startup
try:
    logging.info("Testing database connection...")
    test_key = "db_test"
    db_set(test_key, "test_value")
    test_result = db_get(test_key, None)
    if test_result == "test_value":
        logging.info("✅ Database connection successful")
        db_delete(test_key)
    else:
        logging.error("❌ Database connection failed - test value mismatch")
except Exception as e:
    logging.error(f"❌ Database connection failed: {e}")


def _normalize_token(raw: str) -> str:
    t = (raw or "").strip().strip('"').strip("'")
    if t.startswith("\ufeff"):
        t = t.lstrip("\ufeff")
    return t.replace(" ", "").replace("\n", "").replace("\r", "")


def _parse_token_from_dotenv_path(path: str):
    """Read DISCORD_BOT_TOKEN / DISCORD_TOKEN from a .env file on disk (ignores comments)."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if s.startswith("DISCORD_BOT_TOKEN="):
                    return _normalize_token(s.split("=", 1)[1])
                if s.startswith("DISCORD_TOKEN="):
                    return _normalize_token(s.split("=", 1)[1])
    except OSError:
        return None
    return None


def _read_bot_token():
    # Prefer literal file contents so unsaved editor buffers can't fake success
    t = (
        _parse_token_from_dotenv_path(_local_env)
        or _parse_token_from_dotenv_path(_parent_env)
        or _normalize_token(os.environ.get("DISCORD_BOT_TOKEN", ""))
        or _normalize_token(os.environ.get("DISCORD_TOKEN", ""))
    )
    return t

#============================================================================
# only bot commands will be answerd ! setup
#============================================================================
intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.message_content = True  # Enabled - Bot has Message Content Intent permission

def generate_command_variations(cmd):
    """Generate all variations of a command with gaps between letters."""
    variations = [cmd, cmd.upper()]
    
    # Generate variations with 1-3 spaces between letters
    cmd_len = len(cmd)
    if cmd_len > 1:
        for gap_count in range(1, 4):
            # Create variation with gaps between each letter
            gap_str = ' ' * gap_count
            variation = gap_str.join(cmd)
            variations.append(variation)
            variations.append(variation.upper())
    
    return variations

def get_prefix(bot, message):
    guild_id = str(message.guild.id) if message.guild else None
    system_data = load_system()
    base = system_data["system"]["prefixes"].get(guild_id, 's')
    
    # List of all commands that should support variations
    commands_list = [
        "mine", "daily", "cash", "give", "bank", "lottery", "leaderboard", "lb",
        "roll", "flip", "horse", "pyramid", "rob", "slots",
        "wheel", "rules", "help", "ping", "server", "vote", "prefix",
        "disable", "enable", "dungeon", "wallet", "profile",
        "battle", "trade", "gift", "role", "shop", "inventory", "clan", "clan_invite",
        "gamepass", "crime", "loot", "sell", "zoo", "hunt", "zoolb", "count"
    ]
    
    p = []
    
    # Add standard space variations for prefix 's'
    spaces = ['s' + (' ' * i) for i in range(0, 4)] + ['S' + (' ' * i) for i in range(0, 4)]
    p.extend(spaces)
    p.append("$")
    
    # Add command variations for prefix 's'
    for cmd in commands_list:
        cmd_variations = generate_command_variations(cmd)
        for variation in cmd_variations:
            p.append(f"s{variation}")
            p.append(f"S{variation}")
    
    # If custom prefix is set, add variations for it too
    if base:
        p.extend([base, str(base).upper()])
        p.extend([f"{base}" + (' ' * i) for i in range(1, 4)])
        p.extend([f"{str(base).upper()}" + (' ' * i) for i in range(1, 4)])
        
        # Add command variations for custom prefix
        for cmd in commands_list:
            cmd_variations = generate_command_variations(cmd)
            for variation in cmd_variations:
                p.append(f"{base}{variation}")
                p.append(f"{str(base).upper()}{variation}")
    
    return p

bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None,
    case_insensitive=True,
    allowed_mentions=discord.AllowedMentions(
        everyone=False,
        roles=False,
        users=True,
        replied_user=False,
    ),
)
BOT_OWNER_ID = 1243921225554726954


@bot.event
async def on_command_error(ctx, error):
    """Gracefully handle expected user input mistakes without spammy tracebacks."""
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.CommandOnCooldown):
        retry = getattr(error, "retry_after", 0)
        command_name = getattr(ctx.command, "name", "this command")
        if command_name == "zoo":
            await ctx.send(f"⏳ Wait {retry:.0f}s before checking the zoo again.")
        elif command_name == "hunt":
            await ctx.send(f"⏳Wait {retry:.0f}s before using `hunt` again.")
        else:
            await ctx.send(f"⏳ Wait {retry:.0f}s before using `{command_name}` again.")
        return

    if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument, commands.TooManyArguments)):
        if ctx.command is not None:
            usage = getattr(ctx.command, "usage", None)
            if usage:
                await ctx.send(f"Invalid input for `{ctx.command.name}`. Usage: `{usage}`")
            else:
                await ctx.send(f"Invalid input for `{ctx.command.name}`. Check the command usage.")
        return

    if isinstance(error, commands.CheckFailure):
        return

    logging.exception("Unhandled command error in %s", ctx.command, exc_info=error)


def _legacy_command(command):
    """Keep staged legacy definitions importable without registering them."""
    return command


def _legacy_tree_command(*args, **kwargs):
    """Keep staged slash definitions importable without registering them."""
    return lambda command: command


def _legacy_subcommand(*args, **kwargs):
    """Keep staged group subcommands importable without registering them."""
    return lambda command: command
#============================================================================
# SQlite Database Utilities
#============================================================================
def load_users():
    """Load consolidated user data from SQLite database"""
    try:
        if db_has("users"):
            return db_get("users", {"users": {}, "xp_data": {}, "daily_data": {}, "rob_cooldowns": {}, "lottery_data": {"players": {}, "history": []}, "cf_streaks": {}, "slot_cooldowns": {}, "plinko_cooldowns": {}, "crime_jail": {}, "crime_cooldowns": {}, "split_games": {}, "share_balances": {}, "share_cooldowns": {}, "mines_games": {}, "mines_cooldowns": {}})
        else:
            return {"users": {}, "xp_data": {}, "daily_data": {}, "rob_cooldowns": {}, "lottery_data": {"players": {}, "history": []}, "cf_streaks": {}, "slot_cooldowns": {}, "plinko_cooldowns": {}, "crime_jail": {}, "crime_cooldowns": {}, "split_games": {}, "share_balances": {}, "share_cooldowns": {}, "mines_games": {}, "mines_cooldowns": {}}
    except Exception as e:
        logging.error(f"Error loading users data: {e}")
        return {"users": {}, "xp_data": {}, "daily_data": {}, "rob_cooldowns": {}, "lottery_data": {"players": {}, "history": []}, "cf_streaks": {}, "slot_cooldowns": {}, "plinko_cooldowns": {}, "crime_jail": {}, "crime_cooldowns": {}, "split_games": {}, "share_balances": {}, "share_cooldowns": {}, "mines_games": {}, "mines_cooldowns": {}}

def save_users(data):
    """Save consolidated user data to SQLite database"""
    try:
        # Get current data to detect changes
        current_data = load_users()
        
        # Detect user changes and log them
        if current_data and "users" in current_data:
            for user_id, new_user_data in data.get("users", {}).items():
                old_user_data = current_data["users"].get(user_id, {})
                
                # Check if user data changed
                if old_user_data != new_user_data:
                    changes = {}
                    for key, new_value in new_user_data.items():
                        old_value = old_user_data.get(key)
                        if old_value != new_value:
                            changes[key] = {"old": old_value, "new": new_value}
                    
                    if changes:
                        try:
                            from db import log_user_change
                            log_user_change(user_id, changes, "economy_update")
                        except Exception as log_error:
                            logging.error(f"Failed to log user change: {log_error}")
        
        db_set("users", data)
    except Exception as e:
        logging.error(f"Error saving users data: {e}")

def load_clans_data():
    """Load consolidated clan data from SQLite database"""
    try:
        if db_has("clans"):
            return db_get("clans", {"clans": {}, "clan_msgs": {}, "clan_invites": {}, "clan_war_limits": {}, "clan_invite_off": {}, "clan_history": {}, "clan_war_state": {"enabled": False}, "clan_codes": {"next_code": 1}})
        else:
            return {"clans": {}, "clan_msgs": {}, "clan_invites": {}, "clan_war_limits": {}, "clan_invite_off": {}, "clan_history": {}, "clan_war_state": {"enabled": False}, "clan_codes": {"next_code": 1}}
    except Exception as e:
        logging.error(f"Error loading clans data: {e}")
        return {"clans": {}, "clan_msgs": {}, "clan_invites": {}, "clan_war_limits": {}, "clan_invite_off": {}, "clan_history": {}, "clan_war_state": {"enabled": False}, "clan_codes": {"next_code": 1}}

def save_clans_data(data):
    """Save consolidated clan data to SQLite database"""
    try:
        db_set("clans", data)
    except Exception as e:
        logging.error(f"Error saving clans data: {e}")

def load_system():
    """Load consolidated system data"""
    try:
        return db_get("system", {"system": {"prefixes": {}, "disabled_channels": [], "rules_agreed_users": []}, "bot_event": {}, "market_drop": {}})
    except Exception as e:
        logging.error(f"Error loading system data: {e}")
        return {"system": {"prefixes": {}, "disabled_channels": [], "rules_agreed_users": []}, "bot_event": {}, "market_drop": {}}

def save_system(data):
    """Save consolidated system data"""
    try:
        db_set("system", data)
    except Exception as e:
        logging.error(f"Error saving system data: {e}")

def load_shop():
    """Load consolidated shop data"""
    try:
        return db_get("shop", {"shop": {"categories": {}, "items": {}}})
    except Exception as e:
        logging.error(f"Error loading shop data: {e}")
        return {"shop": {"categories": {}, "items": {}}}

def save_shop(data):
    """Save consolidated shop data"""
    try:
        db_set("shop", data)
    except Exception as e:
        logging.error(f"Error saving shop data: {e}")

def get_user_data(users_data, user_id, guild_id):
    """Get user data from consolidated structure"""
    user_key = str(user_id)  # Use only user ID for cross-server consistency
    return users_data["users"].setdefault(user_key, {
        "economy": {"cash": 0, "bank": 0, "inventory": {}},
        "xp": {"level": 1, "xp": 0},
        "daily": {"last_claim": 0},
        "cooldowns": {"rob": 0, "crime": 0, "slot": 0, "plinko": 0, "wheel": 0, "roll": 0},
        "streaks": {"coinflip": 0},
        "profiles": {"dungeon": {}}
    })

#Clean up duplicate user data entries
def cleanup_duplicate_users():
    """Clean up duplicate user data entries and merge them into single entries"""
    users_data = load_users()
    users = users_data.get("users", {})
    
    # Track merged users and their data
    merged_users = {}
    duplicate_count = 0
    
    for user_key, user_data in users.items():
        try:
            # Extract user_id from user_key (handle both old format "user_id_guild_id" and new format "user_id")
            if "_" in user_key:
                user_id = user_key.split("_")[0]
            else:
                user_id = user_key
            
            user_id = str(user_id)
            
            if user_id in merged_users:
                # Merge data - keep highest values and combine inventories
                existing = merged_users[user_id]
                
                # Merge economy data (keep highest values)
                existing_econ = existing.get("economy", {})
                new_econ = user_data.get("economy", {})
                
                merged_econ = {
                    "cash": max(existing_econ.get("cash", 0), new_econ.get("cash", 0)),
                    "bank": max(existing_econ.get("bank", 0), new_econ.get("bank", 0)),
                    "inventory": {**existing_econ.get("inventory", {}), **new_econ.get("inventory", {})}
                }
                
                # Merge XP data (keep highest)
                existing_xp = existing.get("xp", {})
                new_xp = user_data.get("xp", {})
                merged_xp = {
                    "level": max(existing_xp.get("level", 1), new_xp.get("level", 1)),
                    "xp": max(existing_xp.get("xp", 0), new_xp.get("xp", 0))
                }
                
                # Merge daily data (keep most recent)
                existing_daily = existing.get("daily", {})
                new_daily = user_data.get("daily", {})
                merged_daily = {
                    "last_claim": max(existing_daily.get("last_claim", 0), new_daily.get("last_claim", 0))
                }
                
                # Merge cooldowns (keep most recent)
                existing_cd = existing.get("cooldowns", {})
                new_cd = user_data.get("cooldowns", {})
                merged_cd = {}
                for cd_type in ["rob", "crime", "slot", "plinko", "wheel", "roll"]:
                    merged_cd[cd_type] = max(existing_cd.get(cd_type, 0), new_cd.get(cd_type, 0))
                
                # Merge streaks (keep highest)
                existing_streaks = existing.get("streaks", {})
                new_streaks = user_data.get("streaks", {})
                merged_streaks = {
                    "coinflip": max(existing_streaks.get("coinflip", 0), new_streaks.get("coinflip", 0))
                }
                
                # Merge profiles
                existing_profiles = existing.get("profiles", {})
                new_profiles = user_data.get("profiles", {})
                merged_profiles = {**existing_profiles, **new_profiles}
                
                # Update merged user data
                merged_users[user_id] = {
                    "economy": merged_econ,
                    "xp": merged_xp,
                    "daily": merged_daily,
                    "cooldowns": merged_cd,
                    "streaks": merged_streaks,
                    "profiles": merged_profiles
                }
                
                duplicate_count += 1
            else:
                # First occurrence of this user
                merged_users[user_id] = user_data
                
        except Exception as e:
            logging.error(f"Error processing user key {user_key}: {e}")
            continue
    
    # Update users data with merged entries
    users_data["users"] = merged_users
    save_users(users_data)
    
    logging.info(f"Cleaned up {duplicate_count} duplicate user entries")
    return duplicate_count


#================================================
#image to emoji
S_HEADS_ID = 1460636733464117359
S_TAILS_ID = 1460636753240264936
ARROW_ID = 1546197369500991528
DOT_ID = 1546195209065467975
QNA_BOOK_ID = 1546992619945725962
QNA_TIMER_ID = 1546991164383694848
SAVAGE_CASH_ID = 1554026648251404408
SOUL_ID = 1546146196303781960
S_HEART_ID = 1546147996679409724
DAMAGE_ID = 1546147989226000555
DUNGEON_ID = 1546147991826726942
HEALTH_ID = 1546147994049585202
BOOST_ID = 1546147943911002174
S_LOVE_ID = 1546152813485097083
S_CAKE_ID = 1546152837015146618
S_CROWN_ID = 1546152856699011122
S_RIZZ_ID = 1546152818174328902
S_CAT_ID = 1546152816085831710
AURA_ID = 1546203726031884348
S_CLOCK_ID = 1190240901243111424
BAR_SHIELD_ID = 1546154803766366308
SKULL_SHIELD_ID = 1546154778126712892
DEVELOPER_BADGE_ID = 1546156656943960104
BUG_HUNTER_BADGE_ID = 1552193415620464700
SUPPORTER_BADGE_ID = 1554363240425852939
MEMBER_BADGE_ID = 1546156703022583948
LEVEL_50_BADGE_ID = 1546990647737585716
GAMEPASS_BADGE_ID = 1554364387215679528
RUM_ID = 1554030604805214358
RUM_BADGE_ID = 1554016348307460096
R_RING_ID = 1546159403110109285
M_RING_ID = 1546159370830872626
L_RING_ID = 1546159390950817883
GIFT_ROSE_ID = 1546160176128721037
GIFT_BASKET_ID = 1546160173171740773

GREEN_KEY_ID = 1546142246066192517
PURPLE_KEY_ID = 1546142219080179802
RED_KEY_ID = 1546142225946382509
BLUE_KEY_ID = 1546142221500158014
BLACK_KEY_ID = 1546142223651840020

BASIC_LOOTBOX_ID = 1546143922110079096
RARE_LOOTBOX_ID = 1546143925197344779
ETHEREAL_LOOTBOX_ID = 1546143928049209396
AURA_LOOTBOX_ID = 1546143930293420153
SAVAGE_LOOTBOX_ID = 1546143933254602814

S_HEADS = "🎮"
S_TAILS = "🎮"
ARROW = f"🎮"
DOT = f"🎮"
QNA_BOOK = f"🎮"
QNA_TIMER = f"🎮"
RED_FLAG = "🚩"
S_BOMB = "💣"
GREEN_FLAG = "🟩"
S_PYRAMID = "🔺"
SAVAGE_CASH = f"🎮"
SOUL = f"🎮"
S_HEART = f"🎮"
DAMAGE = f"🎮"
DUNGEON = f"🎮"
HEALTH = f"🎮"
BOOST = f"🎮"
S_LOVE = f"🎮"
S_CAKE = f"🎮"
S_CROWN = f"🎮"
S_RIZZ = f"🎮"
S_CAT = f"🎮"
AURA = f"🎮"
BAR_SHIELD = f"🎮"
SKULL_SHIELD = f"🎮"
DEVELOPER_BADGE = f"🎮"
BUG_HUNTER_BADGE = f"🎮"
SUPPORTER_BADGE = f"🎮"
MEMBER_BADGE = f"🎮"
LEVEL_50_BADGE = f"🎮"
GAMEPASS_BADGE = f"🎮"
RUM = f"🎮"
RUM_BADGE = f"🎮"
R_RING = f"🎮"
M_RING = f"🎮"
L_RING = f"🎮"
GIFT_ROSE = f"🎮"
GIFT_BASKET = f"🎮"
GREEN_KEY = f"🎮"
PURPLE_KEY = f"🎮"
RED_KEY = f"🎮"
BLUE_KEY = f"🎮"
BLACK_KEY = f"🎮"
BASIC_LOOTBOX = f"🎮"
RARE_LOOTBOX = f"🎮"
ETHEREAL_LOOTBOX = f"🎮"
AURA_LOOTBOX = f"🎮"
SAVAGE_LOOTBOX = f"🎮"


__all__ = [
    "S_HEADS_ID",
    "S_TAILS_ID",
	"ARROW_ID",
	"DOT_ID",
    "QNA_BOOK_ID",
    "QNA_TIMER_ID",
	"SAVAGE_CASH_ID",
	"SOUL_ID",
	"S_HEART_ID",
	"DAMAGE_ID",
	"DUNGEON_ID",
	"HEALTH_ID",
	"BOOST_ID",
	"S_LOVE_ID",
	"S_CAKE_ID",
	"S_CROWN_ID",
	"S_RIZZ_ID",
	"S_CAT_ID",
    "AURA_ID",
	"BAR_SHIELD_ID",
	"SKULL_SHIELD_ID",
	"DEVELOPER_BADGE_ID",
	"BUG_HUNTER_BADGE_ID",
	"SUPPORTER_BADGE_ID",
	"MEMBER_BADGE_ID",
	"LEVEL_50_BADGE_ID",
	"GAMEPASS_BADGE_ID",
	"RUM_ID",
	"RUM_BADGE_ID",
	"R_RING_ID",
	"M_RING_ID",
	"L_RING_ID",
	"GIFT_ROSE_ID",
	"GIFT_BASKET_ID",
	"GREEN_KEY_ID",
	"PURPLE_KEY_ID",
	"RED_KEY_ID",
	"BLUE_KEY_ID",
	"BLACK_KEY_ID",
	"BASIC_LOOTBOX_ID",
	"RARE_LOOTBOX_ID",
	"ETHEREAL_LOOTBOX_ID",
	"AURA_LOOTBOX_ID",
	"SAVAGE_LOOTBOX_ID",
    "S_HEADS",
    "S_TAILS",
	"ARROW",
	"DOT",
    "QNA_BOOK",
    "QNA_TIMER",
	"SAVAGE_CASH",
	"SOUL",
	"S_HEART",
	"DAMAGE",
	"DUNGEON",
	"HEALTH",
	"BOOST",
	"S_LOVE",
	"S_CAKE",
	"S_CROWN",
	"S_RIZZ",
	"S_CAT",
    "AURA",
	"BAR_SHIELD",
	"SKULL_SHIELD",
	"DEVELOPER_BADGE",
	"BUG_HUNTER_BADGE",
	"SUPPORTER_BADGE",
	"MEMBER_BADGE",
	"LEVEL_50_BADGE",
	"GAMEPASS_BADGE",
	"RUM",
	"RUM_BADGE",
	"R_RING",
	"M_RING",
	"L_RING",
	"GIFT_ROSE",
	"GIFT_BASKET",
	"GREEN_KEY",
	"PURPLE_KEY",
	"RED_KEY",
	"BLUE_KEY",
	"BLACK_KEY",
	"BASIC_LOOTBOX",
	"RARE_LOOTBOX",
	"ETHEREAL_LOOTBOX",
	"AURA_LOOTBOX",
	"SAVAGE_LOOTBOX",
]



#================================================
# Register command packages .
import builtins

builtins.bot = bot
builtins.savage_cash_emoji = SAVAGE_CASH
builtins.rum_emoji = RUM

# Legacy command modules use lowercase emoji ID globals.
_emoji_ids = {
    "savage_cash_id": SAVAGE_CASH_ID,
    "dot_id": DOT_ID,
    "aura_id": AURA_ID,
    "soul_id": SOUL_ID,
    "s_heart_id": S_HEART_ID,
    "damage_id": DAMAGE_ID,
    "dungeon_id": DUNGEON_ID,
    "health_id": HEALTH_ID,
    "boost_id": BOOST_ID,
    "s_love_id": S_LOVE_ID,
    "s_cake_id": S_CAKE_ID,
    "s_crown_id": S_CROWN_ID,
    "s_rizz_id": S_RIZZ_ID,
    "s_cat_id": S_CAT_ID,
    "s_clock_id": S_CLOCK_ID,
    "bar_shield_id": BAR_SHIELD_ID,
    "skull_shield_id": SKULL_SHIELD_ID,
    "developer_badge_id": DEVELOPER_BADGE_ID,
    "bug_hunter_badge_id": BUG_HUNTER_BADGE_ID,
    "supporter_badge_id": SUPPORTER_BADGE_ID,
    "member_badge_id": MEMBER_BADGE_ID,
    "level_50_badge_id": LEVEL_50_BADGE_ID,
    "gamepass_badge_id": GAMEPASS_BADGE_ID,
    "rum_id": RUM_ID,
    "rum_badge_id": RUM_BADGE_ID,
    "r_ring_id": R_RING_ID,
    "m_ring_id": M_RING_ID,
    "l_ring_id": L_RING_ID,
    "gift_rose_id": GIFT_ROSE_ID,
    "gift_basket_id": GIFT_BASKET_ID,
    "green_key_id": GREEN_KEY_ID,
    "purple_key_id": PURPLE_KEY_ID,
    "red_key_id": RED_KEY_ID,
    "blue_key_id": BLUE_KEY_ID,
    "black_key_id": BLACK_KEY_ID,
    "basic_lootbox_id": BASIC_LOOTBOX_ID,
    "rare_lootbox_id": RARE_LOOTBOX_ID,
    "ethereal_lootbox_id": ETHEREAL_LOOTBOX_ID,
    "aura_lootbox_id": AURA_LOOTBOX_ID,
    "savage_lootbox_id": SAVAGE_LOOTBOX_ID,
}
for _name, _value in _emoji_ids.items():
    setattr(builtins, _name, _value)

from economy import register_economy_commands
from games import register_games_commands
from commands.general import register_general_commands
from commands.general.rules import auto_agree_user
from commands.owner import register_owner_commands
from commands.dungeon import register_dungeon_commands
from commands.dungeon.clan import get_clan_by_user
from commands.social import register_social_commands


def load_badges():
    return db_get("badges", {})


def save_user_data(user_data, user_id, guild_id=None):
    users_data = load_users()
    users_data["users"][str(user_id)] = user_data
    save_users(users_data)


def save_disabled_channels(channels):
    system_data = load_system()
    system_data.setdefault("system", {})["disabled_channels"] = channels
    save_system(system_data)


def get_rules_embed():
    return None


def rules_accept_view():
    return None


disabled_channels = load_system().get("system", {}).get("disabled_channels", {})
agreed_users = set(load_system().get("system", {}).get("rules_agreed_users", []))
badge_list = load_badges()
lootbox_items = {}
bottle_items = {}
key_items = {}
dungeon_key_prices = {}
emoji_ids = {}

register_economy_commands(
    bot,
    load_users=load_users,
    save_users=save_users,
    get_user_data=get_user_data,
    save_user_data=save_user_data,
    load_clans=lambda: load_clans_data().get("clans", {}),
    get_clan_by_user=get_clan_by_user,
    load_badges=load_badges,
    save_badges=lambda data: (db_set("badges", data)),
    badge_list={
        "1": ("developer_badge", DEVELOPER_BADGE_ID),
        "2": ("bug_hunter_badge", BUG_HUNTER_BADGE_ID),
        "3": ("Support_badge", SUPPORTER_BADGE_ID),
        "4": ("member_badge", MEMBER_BADGE_ID),
        "5": ("50_level", LEVEL_50_BADGE_ID),
        "6": ("gamepass_badge", GAMEPASS_BADGE_ID),
        "7": ("rum_badge", RUM_BADGE_ID),
    },
    agreed_users=agreed_users,
    constants={
        "bot_owner_id": BOT_OWNER_ID,
        "rum_id": RUM_ID,
        "savage_cash_id": SAVAGE_CASH_ID,
        "gift_rose_id": GIFT_ROSE_ID,
        "gift_basket_id": GIFT_BASKET_ID,
        "r_ring_id": R_RING_ID,
        "m_ring_id": M_RING_ID,
        "l_ring_id": L_RING_ID,
        "green_key_id": GREEN_KEY_ID,
        "purple_key_id": PURPLE_KEY_ID,
        "red_key_id": RED_KEY_ID,
        "blue_key_id": BLUE_KEY_ID,
        "black_key_id": BLACK_KEY_ID,
    },
    bottle_items=bottle_items,
    key_items=key_items,
    lootbox_items=lootbox_items,
    dungeon_key_prices=dungeon_key_prices,
)
register_games_commands(
    bot,
    load_users=load_users,
    save_users=save_users,
    get_user_data=get_user_data,
    save_user_data=save_user_data,
    db_get=db_get,
    db_set=db_set,
    weighted_rng=WeightedRNG,
    heads_emoji=S_HEADS,
    tails_emoji=S_TAILS,
    cash_emoji=SAVAGE_CASH,
    arrow_emoji=ARROW,
    dot_emoji=DOT,
    red_flag_emoji=RED_FLAG,
    bomb_emoji=S_BOMB,
    green_flag_emoji=GREEN_FLAG,
    pyramid_emoji=S_PYRAMID,
)
register_general_commands(
    bot,
    load_system=load_system,
    save_system=save_system,
    db_get=db_get,
    db_set=db_set,
    db_has=db_has,
    disabled_channels=disabled_channels,
    save_disabled_channels=save_disabled_channels,
    bot_owner_id=BOT_OWNER_ID,
    agreed_users=agreed_users,
    get_rules_embed=get_rules_embed,
    rules_accept_view=rules_accept_view,
    arrow_emoji=ARROW,
    load_users=load_users,
    get_user_data=get_user_data,
    save_user_data=save_user_data,
)
register_dungeon_commands(
    bot,
    load_users=load_users,
    save_users=save_users,
    get_user_data=get_user_data,
    save_user_data=save_user_data,
    db_get=db_get,
    db_set=db_set,
    load_clans_data=load_clans_data,
    save_clans_data=save_clans_data,
    load_system=load_system,
    bottle_items=bottle_items,
    bot_owner_id=BOT_OWNER_ID,
)
register_social_commands(
    bot,
    load_users=load_users,
    save_users=save_users,
    get_user_data=get_user_data,
    save_user_data=save_user_data,
    load_badges=load_badges,
    save_badges=lambda data: db_set("badges", data),
    badge_list=badge_list,
    emoji_ids=emoji_ids,
    qna_book_emoji=QNA_BOOK,
    qna_timer_emoji=QNA_TIMER,
    arrow_emoji=ARROW,
    owner_id=BOT_OWNER_ID,
    share_emojis={
        "dp_love": S_LOVE,
        "s_cake": S_CAKE,
        "s_crown": S_CROWN,
        "rizzz": S_RIZZ,
        "sp_cat": S_CAT,
        "aura": AURA,
    },
)
register_owner_commands(
    bot,
    db_get=db_get,
    db_set=db_set,
    load_users=load_users,
    save_users=save_users,
    get_user_data=get_user_data,
    load_system=load_system,
    save_system=save_system,
    load_shop=load_shop,
    save_user_data=save_user_data,
    bot_owner_id=BOT_OWNER_ID,
    s_clock_id=S_CLOCK_ID,
    auto_agree_user=auto_agree_user,
)



#============================================================
# BOT TOKEN
_token = _read_bot_token()
if not _token:
    raise RuntimeError(
        "Missing DISCORD_BOT_TOKEN. Copy project/.env.example to project/.env and add your token:\n"
        "DISCORD_BOT_TOKEN=your_token_from_discord\n"
        "Discord → Applications → your bot → Bot → reset/copy Token."
    )

_token_placeholders = frozenset({
    "paste_your_discord_bot_token_here",
    "paste_bot_token_here",
    "your_bot_token_here",
})
if _token in _token_placeholders or _token.count(".") != 2 or len(_token) < 55:
    raise RuntimeError(
        "The token read from project/.env or the process environment is missing, is still a placeholder, or is not shaped like a Bot token "
        "(expect ~68 characters and exactly two '.').\n"
        "Paste the token from Discord → Applications → Bot → Token, then save the file with Ctrl+S before running. "
        "If you already pasted it in the editor but see this, the .env file on disk was not saved."
    )
bot.run(_token)
