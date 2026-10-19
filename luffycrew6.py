# ═══════════════════════════════════════════════════════════════════════
#   LUFFY CREW v6.0 — PRODUCTION READY
#   Parent-Child Architecture | 72 Commands | Bulletproof Routing
# ═══════════════════════════════════════════════════════════════════════

import os, sys, json, time, random, asyncio, logging, re, traceback, signal
import aiohttp, psutil
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, List, Set, Optional, Any, Tuple, Callable
from urllib.parse import quote

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions, Bot
)
from telegram.ext import (
    Application, ApplicationBuilder, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from telegram.error import TelegramError, RetryAfter, Forbidden, BadRequest
from telegram.constants import ParseMode

try:
    from telegram import ReactionTypeEmoji
    HAS_REACTIONS = True
except ImportError:
    ReactionTypeEmoji = None
    HAS_REACTIONS = False

try:
    GROUP_FILTER = filters.ChatType.GROUPS
except AttributeError:
    GROUP_FILTER = filters.ChatType.GROUP | filters.ChatType.SUPERGROUP

# ═══════════════════════════════════════════════════════════════════════
#   CONFIG
# ═══════════════════════════════════════════════════════════════════════

BOT_TOKEN = os.getenv("BOT_TOKEN", "8920918134:AAFdzB6WZJ1_mpSU1lE7jyHlJfX8ehmhaMg").strip()
OWNER_ID_RAW = os.getenv("OWNER_ID", "8783373485").strip()
try:
    OWNER_ID = int(OWNER_ID_RAW)
except ValueError:
    OWNER_ID = 0

SUDO_FILE, BOTS_FILE, TARGETS_FILE = "sudo_users.json", "bots.json", "targets.json"
PFP_FILE, CONFIG_FILE = "pfp_loop.json", "config.json"

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("LUFFY")
START_TIME = time.time()

AUTHORIZATION_MSG = (
    "𓆩ᴊʜᴀᴛᴜ ᴛᴇʀʏ ᴀᴜᴋᴀᴛ ʜᴀ? 𝐋ᴜꜰꜰʏ  sE ʟᴀᴅɴᴇ ᴋɪ? tᴇʀʏ ᴍᴍʏ ᴋɪ ᴘᴜsʏʏ ᴘʀ ᴀʙᴅᴜʟ ᴋɪ ᴄʜᴀᴘᴀʟ ᴍᴀʀᴅᴜɴɢᴀ😁🍃"
)

DEFAULT_MENU_HEADER = (
    "╔══════════════════════════════╗\n"
    "   🏴‍☠️  𝗟𝗨𝗙𝗙𝗬 𝗖𝗥𝗘𝗪 𝗔𝗥𝗘 𝗥𝗘𝗔𝗗𝗬  🏴‍☠️\n"
    "╚══════════════════════════════╝\n\n"
    "🔥 𝐌𝐔𝐋𝐓𝐈-𝐁𝐎𝐓 𝐂𝐎𝐍𝐓𝐑𝐎𝐋𝐋𝐄𝐑 🔥\n\n"
    "➤ ᴘʟᴇᴀꜱᴇ ᴀᴅᴅ ᴍᴏʀᴇ ʙᴏᴛꜱ ʙʏ ᴛᴀᴘᴘɪɴɢ ᴏɴ ᴀᴅᴅ ᴛᴏᴋᴇɴ/ʙᴏᴛꜱ\n"
    "➤ ᴀʟʟ ꜰᴇᴀᴛᴜʀᴇꜱ ᴡᴏʀᴋ ɪɴ ɪɴʟɪɴᴇ ʙᴜᴛᴛᴏɴꜱ\n"
    "➤ ᴜɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜꜱᴇʀꜱ ᴡɪʟʟ ʙᴇ ʙʟᴏᴄᴋᴇᴅ 🚫\n"
)

CFG: Dict[str, Any] = {
    "start_text": DEFAULT_MENU_HEADER,
    "start_media_type": None,
    "start_media_file_id": None,
    "game_over_media": "https://files.catbox.moe/flcgis.mp4",
    "game_over_type": "video",
}

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k in CFG:
                if k in data:
                    CFG[k] = data[k]
    except Exception as e:
        log.warning(f"config load failed: {e}")

def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(CFG, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning(f"config save failed: {e}")

load_config()

DEFAULT_INTERVALS = {"nc": 0.1, "spam": 0.02, "raid": 0.05, "pfp": 0.1, "slide": 0.01}
CHAT_INTERVALS: Dict[int, Dict[str, float]] = defaultdict(dict)

def get_interval(chat_id: int, key: str) -> float:
    return CHAT_INTERVALS.get(chat_id, {}).get(key, DEFAULT_INTERVALS.get(key, 0.1))

def set_interval(chat_id: int, key: str, value: float):
    if key == "all":
        for k in DEFAULT_INTERVALS:
            CHAT_INTERVALS[chat_id][k] = value
    else:
        CHAT_INTERVALS[chat_id][key] = value

# ── Per-bot flood cooldown ─────────────────────────────────────────────
_bot_cooldown: Dict[int, float] = defaultdict(float)

def _cooldown_ok(bot_id: int) -> bool:
    return time.monotonic() >= _bot_cooldown.get(bot_id, 0)

def _set_cooldown(bot_id: int, seconds: float):
    _bot_cooldown[bot_id] = time.monotonic() + seconds

INVIS_SUFFIXES = ["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff",
                  "\u00ad", "\u034f", "\u3164", "\u17b4", "\u17b5"]

# ═══════════════════════════════════════════════════════════════════════
#   ULTRA GUARD — per-bot rate tracking
# ═══════════════════════════════════════════════════════════════════════

class UltraGuard:
    def __init__(self, bot_id: int):
        self.bot_id = bot_id
        self._successes = 0
        self._failures = 0
        self._last_error = ""
        self._flood_until = 0.0

    @property
    def delay(self) -> float:
        return max(0.0, self._flood_until - time.monotonic())

    def stats(self) -> Dict[str, Any]:
        return {
            "successes": self._successes,
            "failures": self._failures,
            "last_error": self._last_error,
            "flood_until": self._flood_until,
        }

_guards: Dict[int, UltraGuard] = {}

def get_guard(bot_id: int) -> UltraGuard:
    if bot_id not in _guards:
        _guards[bot_id] = UltraGuard(bot_id)
    return _guards[bot_id]

# ═══════════════════════════════════════════════════════════════════════
#   SAFE CALL — per-bot rate-limited, never raises
# ═══════════════════════════════════════════════════════════════════════

async def safe_call(fn: Callable, *args, bot_id: int = None, timeout: float = 2.0, **kwargs):
    if bot_id is not None and not _cooldown_ok(bot_id):
        return None
    try:
        return await asyncio.wait_for(fn(*args, **kwargs), timeout=timeout)
    except asyncio.TimeoutError:
        if bot_id is not None:
            _set_cooldown(bot_id, 2.0)
            get_guard(bot_id)._failures += 1
        return None
    except RetryAfter as e:
        ra = float(getattr(e, "retry_after", 5.0))
        if bot_id is not None:
            _set_cooldown(bot_id, ra)
            get_guard(bot_id)._last_error = f"FLOOD_WAIT_{ra}"
        return None
    except (Forbidden, BadRequest) as e:
        if bot_id is not None:
            get_guard(bot_id)._failures += 1
            get_guard(bot_id)._last_error = str(e)[:100]
        return None
    except Exception as e:
        if bot_id is not None:
            get_guard(bot_id)._failures += 1
            get_guard(bot_id)._last_error = str(e)[:100]
        return None

# ═══════════════════════════════════════════════════════════════════════
#   SAFE EDIT — bulletproof inline message updater
# ═══════════════════════════════════════════════════════════════════════

async def safe_edit(q, text: str, reply_markup=None, parse_mode=None) -> bool:
    """
    Bulletproof edit. Tries text edit, caption edit, then new message.
    Handles: InaccessibleMessage, missing text/caption, markdown failures,
    "not modified", and all other edge cases.
    """
    try:
        msg = getattr(q, 'message', None)
        bot = q.bot

        if msg is None:
            try:
                await bot.send_message(
                    chat_id=q.from_user.id, text=text,
                    reply_markup=reply_markup, parse_mode=parse_mode
                )
                return True
            except Exception:
                return False

        chat = getattr(msg, 'chat', None)
        chat_id = getattr(chat, 'id', None) if chat else None
        msg_id = getattr(msg, 'message_id', None)
        if chat_id is None or msg_id is None:
            return False

        msg_text = getattr(msg, 'text', None)
        msg_caption = getattr(msg, 'caption', None)
        has_media = bool(
            msg_caption or
            getattr(msg, 'photo', None) or
            getattr(msg, 'video', None) or
            getattr(msg, 'animation', None) or
            getattr(msg, 'document', None) or
            getattr(msg, 'audio', None) or
            getattr(msg, 'voice', None)
        )

        # Build parse_mode attempts (original + fallback to None)
        parse_modes = [parse_mode, None] if parse_mode else [None]

        if msg_text is not None:
            for pm in parse_modes:
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id, message_id=msg_id,
                        text=text, reply_markup=reply_markup, parse_mode=pm
                    )
                    return True
                except BadRequest as e:
                    s = str(e).lower()
                    if "not modified" in s:
                        return True
                    if "no text" in s:
                        break
                except Exception:
                    pass

        if has_media:
            for pm in parse_modes:
                try:
                    await bot.edit_message_caption(
                        chat_id=chat_id, message_id=msg_id,
                        caption=text, reply_markup=reply_markup, parse_mode=pm
                    )
                    return True
                except BadRequest as e:
                    s = str(e).lower()
                    if "not modified" in s:
                        return True
                except Exception:
                    pass

        try:
            await bot.send_message(
                chat_id=chat_id, text=text,
                reply_markup=reply_markup, parse_mode=parse_mode
            )
            return True
        except Exception:
            return False

    except Exception as e:
        log.error(f"safe_edit fatal: {type(e).__name__}: {e}")
        return False

# ═══════════════════════════════════════════════════════════════════════
#   SUDO SYSTEM
# ═══════════════════════════════════════════════════════════════════════

SUDO_USERS: Set[int] = set()

def load_sudo():
    global SUDO_USERS
    try:
        if os.path.exists(SUDO_FILE):
            with open(SUDO_FILE, "r", encoding="utf-8") as f:
                SUDO_USERS = set(json.load(f).get("users", []))
    except Exception as e:
        log.warning(f"sudo load failed: {e}")
        SUDO_USERS = set()

def save_sudo():
    try:
        with open(SUDO_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": list(SUDO_USERS)}, f)
    except Exception as e:
        log.warning(f"sudo save failed: {e}")

load_sudo()

def is_authorized(uid: int) -> bool:
    return uid == OWNER_ID or uid in SUDO_USERS

# ═══════════════════════════════════════════════════════════════════════
#   STATE
# ═══════════════════════════════════════════════════════════════════════

ACTIVE_TASKS: Dict[int, str] = {}
TARGETS: Dict[int, str] = {}
TARGETS_REV: Dict[int, int] = {}
NAMED_TASKS: Dict[int, Dict[str, List[asyncio.Task]]] = defaultdict(lambda: defaultdict(list))
SLIDE_TRACKERS: Dict[int, List[Dict]] = defaultdict(list)
CHAT_LOCKS: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
LAST_MSG: Dict[Tuple[int, str], int] = {}

def _track(cid: int, name: str, task: asyncio.Task):
    NAMED_TASKS[cid][name.lower()].append(task)

def _cancel_named(cid: int, name: str) -> int:
    name = name.lower()
    tasks = NAMED_TASKS.get(cid, {}).get(name, [])
    n = 0
    for t in tasks:
        if not t.done():
            try:
                t.cancel()
                n += 1
            except Exception:
                pass
    NAMED_TASKS[cid][name] = []
    return n

def _cancel_all_named(cid: int) -> int:
    n = 0
    for name in list(NAMED_TASKS.get(cid, {}).keys()):
        n += _cancel_named(cid, name)
    return n

async def claim_once(cid: int, cmd: str, msg_id: int) -> bool:
    """Atomic dedup: only first bot to claim with >= msg_id wins."""
    lock = CHAT_LOCKS[cid]
    async with lock:
        prev = LAST_MSG.get((cid, cmd), 0)
        if msg_id <= prev:
            return False
        LAST_MSG[(cid, cmd)] = msg_id
        return True

async def claim_and_start_multi(cid: int, cmd: str, msg_id: int, task_factory) -> bool:
    """Atomic dedup + task creation for multi-bot loops."""
    lock = CHAT_LOCKS[cid]
    async with lock:
        prev = LAST_MSG.get((cid, cmd), 0)
        if msg_id <= prev:
            return False
        LAST_MSG[(cid, cmd)] = msg_id
        _cancel_named(cid, cmd)
        tasks = task_factory()
        for t in tasks:
            _track(cid, cmd, t)
        return True

# ═══════════════════════════════════════════════════════════════════════
#   TARGETS
# ═══════════════════════════════════════════════════════════════════════

def load_targets():
    global TARGETS, TARGETS_REV
    try:
        if os.path.exists(TARGETS_FILE):
            with open(TARGETS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            TARGETS = {int(k): v for k, v in d.get("by_id", {}).items()}
            TARGETS_REV = {int(k): v for k, v in d.get("by_label", {}).items()}
    except Exception as e:
        log.warning(f"targets load failed: {e}")

def save_targets():
    try:
        with open(TARGETS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "by_id": {str(k): v for k, v in TARGETS.items()},
                "by_label": {str(k): v for k, v in TARGETS_REV.items()},
            }, f)
    except Exception as e:
        log.warning(f"targets save failed: {e}")

load_targets()

def _label_to_uid(label: str) -> Optional[int]:
    if not label:
        return None
    try:
        return int(label)
    except ValueError:
        pass
    label_lower = label.lower()
    for uid, lbl in TARGETS.items():
        if lbl.lower() == label_lower:
            return uid
    return None

async def _resolve_target(chat_id: int, bot: Bot, args: List[str]) -> str:
    if not args:
        return ""
    uid = _label_to_uid(args[0])
    if uid is None:
        return " ".join(args)
    try:
        member = await bot.get_chat_member(chat_id, uid)
        u = member.user
        mention = f"@{u.username}" if u.username else u.first_name
        rest = " ".join(args[1:])
        return (mention + (" " + rest if rest else "")).strip()
    except Exception:
        return " ".join(args)

# ═══════════════════════════════════════════════════════════════════════
#   PFP STATE
# ═══════════════════════════════════════════════════════════════════════

PFP_LOOP_STATE: Dict[int, bool] = {}
PFP_IMAGES: Dict[int, List[str]] = defaultdict(list)

def load_pfp():
    global PFP_LOOP_STATE, PFP_IMAGES
    try:
        if os.path.exists(PFP_FILE):
            with open(PFP_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            PFP_LOOP_STATE = {int(k): v for k, v in d.get("state", {}).items()}
            PFP_IMAGES = defaultdict(list, {int(k): list(v) for k, v in d.get("images", {}).items()})
    except Exception as e:
        log.warning(f"pfp load failed: {e}")

def save_pfp():
    try:
        with open(PFP_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "state": {str(k): v for k, v in PFP_LOOP_STATE.items()},
                "images": {str(k): list(v) for k, v in PFP_IMAGES.items() if v},
            }, f)
    except Exception as e:
        log.warning(f"pfp save failed: {e}")

load_pfp()

# ═══════════════════════════════════════════════════════════════════════
#   TEMPLATES — 100% PRESERVED
# ═══════════════════════════════════════════════════════════════════════

LUFFY_EMOJI = [
    ["🌑","🌒","🌓","🌔","🌕","🌖","🌗","🌘","🌙","🌚","🌝","🌛","🌜"],
    ["☠️","👾","🫐","✨","🖤","🤍","💖","❤️‍🔥","🌺","🌷","🌸","🛸","🧃","🍌","🍁","🌿","🍀","🔥","🌋","🌊","❄️","🌈","🪐","🪼"],
    ["🥱","😱","🤨","😒","😡","🤬","😤","😮‍💨","🥵","🥶","🤢","🤮","🫩","😈","👿","👽","🧃","🧋","🗻","🃏","💠","🇦🇨","🇦🇩","🇦🇪"],
    ["🇦🇨","🇦🇩","🇦🇪","🇦🇫","🇦🇬","🇦🇮","🇦🇱","🇦🇲","🇦🇴","🇦🇶","🇦🇷","🇦🇸","🇦🇹","🇦🇺","🇦🇼","🇧🇦","🇧🇶","🇧🇱","🇧🇫","🇨🇮","🇨🇩","🇨🇦","🇨🇿","🇩🇯","🇨🇭","🇪🇬","🇨🇨","🇧🇯","🇧🇶","🇰🇿","🇰🇼","🇰🇳","🇲🇭","🇲🇪","🇲🇬","🇰🇳","🇮🇴","🇯🇵","🇷🇺","🇳🇺","🇵🇬","🇸🇩","🇵🇷","🇵🇳","🇵🇭","🇳🇫","🇳🇪","🇺🇾","🇺🇸","🇻🇪"],
    ["🌟","💫","✨","🌈","🦋","🌸","🎀","🕊️","🌺","🌷","🌠","☄️","👾","💢","🕸️","🗿","💸","🔮","📿","🚬"],
    ["❤️","🧡","💛","💚","💙","💜","🖤","🤍","🤎","🩷","🩵","💚","🩶","💔","❣️","💕","💞","💓","💗","💖","💘","💝"],
    ["🌬️","❄️","🌀","🌪️","⚡","☔","🌈","💧","☁️","🌨️","🌧️","🌩️","⛈️","🌦️","🌥️","⛅"],
    ["🐶","🐰","🐻‍❄️","🐮","🐵","🐒","🐤","🐱","🦊","🐭","🐻","🐹","🐼","🐸","🦁","🐯","🐥","🪿","🐦","🐣"],
    ["🦋⃟🌑","🦋⃟🌒","🦋⃟🌔","🦋⃟🌕","🦋⃟🌖","🦋⃟🌗","🦋⃟🌘","🦋⃟🪐","🦋⃟🌍","🦋⃟🌎","🦋⃟🌙","🦋⃟☄️","🦋⃟🫧"],
    ["🪠","🪒","🪫","🪸","🪷","🪹","🪺","🫧","🫘","🫚","🫛","🪮","🪭"],
]
LUFFY_WORDS = ["𝗧ᴍᴋʙ","𝗧ᴍᴋᴄ","𝗥ᴀɴᴅ","𝗕ᴋʟ","𝗧ᴍʀ","𝗟ᴜɴ𝗞ʜᴀ","𝗠ᴀᴅᴇʀᴄʜᴏᴅ","𝗕ꜱᴅᴋ",
               "𝗚ᴀɴᴅᴜ","𝗧ᴍᴋᴄ𝗠ᴀᴄᴄʜᴀʀ","𝗣ʟᴀʏ𝗚ɪʀʟ","𝗔ꜱꜱ𝗛ᴏʟᴇ","𝗡ɪɢɢᴀ",
               "𝗙ᴜᴄᴋ𝗬ᴏᴜ","𝗣ᴇʀᴠᴇʀᴛ","𝗦ᴛᴇᴘꜱɪꜱ","𝗠ᴏᴛʜᴇʀ𝗙ᴜᴄᴋᴇʀ","𝗕ᴏʙʙɪᴇ",
               "𝗕ᴀꜱᴛᴀʀᴅ","𝗣ɪᴇᴄᴇ𝗢ꜰ𝗦ʜɪᴛ"]

def _rep(s: str, n: int) -> str:
    return s * n

def build_luffy_nc(n: int, text: str) -> str:
    emj = random.choice(LUFFY_EMOJI[(n-1) % len(LUFFY_EMOJI)])
    if n == 1: return f"•{emj}• {text} {random.choice(LUFFY_WORDS)} " + _rep("𒈙🦋🌙⃤", 128)
    if n == 2: return f"≼ {emj} ≽ {text} ʟꪊꪀᴅ ᥴʜᴜડ " + _rep("🈲∿∿∿", 20) + "🈲∿∿∿"
    if n == 3: return f"⪻{emj}⪼ {text} ⪻{emj}⪼"
    if n == 4: return f"⊱{emj}⊰ {text} {_rep('ᥫ᭡.🌏', 20)} ⊱{emj}⊰"
    if n == 5: return f"𓆩{emj}𓆪 {text} MADARCH⭕️D {_rep('༻༺🩷', 40)} 𓆩{emj}𓆪"
    if n == 6: return f"«{emj}» {text} ᴛᴍᴋᴄ " + "".join(f"——({emj})" for _ in range(40)) + f" «{emj}»"
    if n == 7: return f"<<{emj}>> {text} <<{emj}>>"
    if n == 8: return f"{emj} {text} {_rep('ဪ🟪🟩🟪🟩🟡🔵ဪဪဪ', 8)} {emj}"
    if n == 9: return f"({emj}) {text} ———🌙"
    if n == 10: return f"[{emj}] {text} 𝐋ᴜғғʏ Bһᴀɢᴡᴀꪀ है ~//~  🦢💘"
    return text

VEGETA_EMOJI = [
    ["😀","😃","😄","😁","😂","😅","🥹","😆","🤣","🥲","☺️","😊"],
    ["🍏","🍋","🍎","🍐","🍊","🍈","🫐","🍉","🍓","🍇"],
    ["🪬","🧿","🪞","🪆","🪩","🗿","🪦","🪚","🪓","🪤","🪱","🪰"],
    ["😺","😸","😹","😻","😼","😽","🙀","😿","😾"],
    ["🕛","🕧","🕐","🕜","🕑","🕝","🕒","🕞","🕓","🕟","🕔","🕠","🕕","🕡","🕖","🕢","🕗","🕣","🕘","🕤"],
]

def build_vegeta_nc(n: int, text: str) -> str:
    if n == 1: return f"{text} 𝐓ᴇƦꞮ 𝐌ᴀᴀ 𝐊Ɪ 𝐂ʜᴜᴛ 𝐒ꞮʟᴀʏꞮ 𝐊Ʀ 𝐃ᴇɴɢᴇ 𝐇ᴜᴍ 𝐁ʜᴀꞮ " + _rep("𒈙👑", 18) + f"<{random.choice(VEGETA_EMOJI[0])}>"
    if n == 2: return f"{random.choice(VEGETA_EMOJI[1])} {text} 𝙇𝙐𝙉𝘿 𝘾𝙃⭕⭕𝙎𝙎 /- " + _rep("𒐫𒐫𒐫💚", 20) + "𒐫𒐫"
    if n == 3: return f"{text} 匚卄ㄩ卩 ᥅ꪖꪀᦔﺃᛕꫀ ᥇ꪖᥴᥴ𝙃ꫀ " + "".join(f"𒈙⸻{e}" for e in ["🩵","❤️","🩷","🧡","💛","💚","💙","💜","🖤","🩶","🤍","❣️"])
    if n == 4: return f"{text} 𝐏𝐈𝐋𝐋𝐄 😩 𝐒ᴀʏ 𝗩𝗘𝗚𝗘𝗧𝗔 𝐃ᴀᴅʏ 𓆩💗𓆪x " + _rep("𒀱ꪳ💝", 25)
    if n == 5: return f"{text}  ƇӇƲƤ ƦƝƊƖƘЄ " + _rep("𒈙⸻🐬", 20)
    if n == 6: return f"{text} PILLA 😭 SAY VEGETA BAGWAN {random.choice(VEGETA_EMOJI[2])}" + _rep("𒈙", 80)
    if n == 7: return f"{text} ༆𝐇𝟖𝐑 𝐑𝐀𝐍𝐃𝐀𝐋 𝐍𝐎𝐑𝐈𝐌𝐄 𝐂𝐕𝐑 𝐊𝐑,᭄⫸{random.choice(VEGETA_EMOJI[3])}⫷🔥🤟࿐" + _rep("𒐫", 60)
    if n == 8: return f"{text} 𓆃𒁃🖤" + _rep("𒁃🖤", 40)
    if n == 9: return f"{text} 𝗧ᴍᴋᴄ 〄💜꧅🩵〄🩷꧅❤️〄💛꧅🤎" + _rep("〄💜꧅🩵〄🩷꧅❤️〄💛꧅🤎", 20)
    if n == 10: return f"{text}  𓆩{random.choice(VEGETA_EMOJI[4])}𓆪" + _rep("█", 150) + " TMKC"
    return text

SPAM_EMOJI = {2: ["❤️","🧡","💛","💚","💙","💜","🖤"],
              3: ["❄️","🥶","🧊","🌨️","☃️","⛄","🌬️","💨","🌫️"]}

def build_spam(n: int, text: str) -> str:
    if n == 1:
        block = (f"#{text} #𝗚𝗔𝗡𝗗𝗠𝗔𝗥𝗘 𝗧𝗘𝗥𝗜 𝗜𝗧𝗡𝗜 𝗛𝗜𝗠𝗠𝗔𝗧 𝗧𝗨 "
                 f"#𝗟𝗨𝗙𝗙𝗬 𝗕𝗔𝗔𝗣 𝗞𝗘 𝗦𝗔𝗠𝗡𝗘 #𝗔𝗪𝗔𝗭 𝗨𝗖𝗛𝗜 𝗞𝗥𝗘𝗚𝗔 ?? "
                 f"𝗠𝗔𝗗𝗥𝗖𝗛⭕️𝗗 🤍🌙🕊️_____________________/ ")
        return block * 20
    if n == 2:
        return f"{text} Tᴇʀɪ Mᴀᴀ Kᴇ Bʜᴏsᴅᴇ Mᴇ 𝟼𝟺ɢʙ rᴅᴘ ᴅᴀʟᴅᴜ <{random.choice(SPAM_EMOJI[2])}>\n\n\n" * 15
    if n == 3:
        return f"#{text}  ᴛᴇʀɪ  ᴍᴀᴀ  ᴄʜᴏᴅ  ᴋᴇ  ᴍᴀᴀʀ  ᴅᴜɴɢᴀ  ᴋᴜᴛᴛɪᴋᴇ  /-----------------------------‐--------{random.choice(SPAM_EMOJI[3])} " * 25
    if n == 4:
        return (f"─── ⋆⋅☆⋅⋆ ──{text} 𝙈𝘼𝘿𝘼𝙍𝘾𝙃 ⭕ 𝘿─── ⋆⋅☆⋅⋆ ───"
                f"── ⋆⋅☆⋅⋆ ── 🩵 𝗨𝗧𝗛 𝗚𝗨𝗟𝗔𝗠 𝗠𝗔𝗥𝗔 𝗞𝗘𝗦𝗘 ─── ⋆⋅☆⋅⋆ ───") * 10
    if n == 5:
        ems = ["🖤","❤️","🩶","🤍","🧡","💛","💚","🩵","💙","💜","🤎","🩷","💘","💝","💖","💗","💓","💞","💕","💌","💟","♥️","❣️","❤️‍🩹","💔","❤️‍🔥","🫀"]
        return "\n".join(f"⋆⋅☆⋅ {text}  रंडी पुत्र  ({e}) ⋆⋅☆⋅⋆" for e in ems)
    return text

RR_REPLIES = [
    "{text} textᴇʀɪ Dᴀᴅɪ  ᴋ ᴄʜᴍᴜᴛ ᴍᴀɪ ᴛᴀɴɢ ᴀᴛᴋᴀ ᴅᴜɴɢᴀ ғɪʀ ᴛᴇʀʏ ᴅᴀᴅᴜ sᴜsᴜ ᴋᴀɪsᴀ ᴋʀᴇɢɪ😍?",
    "{text} ᴛᴇʀʏ ᴍᴍʏ ᴋ ᴄʜᴜᴛᴀᴅᴏ ᴍᴀɪ 𝐃ɪɴᴏsᴀᴜʀ ᴋɪ ᴘᴏᴛʏʏ😁",
    "{text} ᴍᴀᴊᴅᴜʀɪ ᴋʀᴇɢᴀ ɢᴀʀᴇᴇʙ ᴛᴇʀʏ ᴍᴍʏ ᴋɪ ᴛᴀɴɢ ᴜᴛʜᴀᴋᴇ👻 ᴄʜᴜᴛ ᴍᴀᴊ ғɪᴋᴀʀɪ ᴊᴀʟᴀ ᴅᴜɴɢᴀ🙈",
    "{text} ᴇᴋ ʙᴀᴀᴛ ʙᴛᴀᴜ ᴛᴇʀᴀ ᴘᴀᴘᴀ ᴛᴇʀʏ ᴍᴍʏ ᴋᴏ ᴍᴇʀsᴀ ᴄʜᴜᴅᴠᴀ ᴋʀ ɢʜᴀʀ ᴄʜᴀʟᴀᴛᴇ ᴇʏ🤣👻",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋ ᴄʜᴜᴛᴀᴅ ᴘᴀʀ ᴊᴏ ᴘʜᴜɴsɪ ʜᴀ ᴜsᴋᴏ👻 ʟᴀᴀᴛ ᴍᴀʀᴋᴀ ᴘʜᴏᴅ ᴅᴜ ᴄʏ?",
    "{text} textᴇʀʏ ᴍᴍʏ ᴋᴀ england ᴡᴀʟᴇ ʙᴜs ᴍᴀɪ ɢᴀɴɢ ʙᴀɴɢ ᴋʀᴋᴇ ᴋʜɪᴅᴋɪ sᴀ ғᴇᴋ ᴅᴇɴɢᴇ😭🥺",
    "{text} ᴋᴀʟɪ ᴋᴜᴛᴛɪ ᴋɪ ᴄʜᴜᴛ sᴀ ɴɪᴋʟᴀ ᴋᴜᴛᴛᴀ ᴋᴀ ᴘɪʟʟᴀ👻 ᴛᴇʀʏ ᴍᴀᴀ ʜᴀᴄᴋʟᴀ ᴋʀ ᴍᴀʀ ᴊᴀʏᴇ🤣",
    "{text} ᴊʜᴀᴛᴜ ᴛᴇʀʏ ᴀᴜᴋᴀᴛ ʜᴀ? 𝐋ᴜꜰꜰʏ  sE ʟᴀᴅɴᴇ ᴋɪ? tᴇʀʏ ᴍᴍʏ ᴋɪ ᴘᴜsʏʏ ᴘʀ ᴀʙᴅᴜʟ ᴋɪ ᴄʜᴀᴘᴀʟ ᴍᴀʀᴅᴜɴɢᴀ😁🍃",
    "{text} ᴛᴇʀʏ ᴍᴍʏ ᴋᴏ 𝐋ᴜꜰꜰʏ ᴋ ᴀʟᴀᴠᴀ ᴋᴏɪ ᴏʀ ᴄʜᴏᴅ sᴀᴋᴛᴀ ᴇʏ ᴋᴛᴀ?😁",
    "{text} sᴜᴀʀ ᴛᴇʀʏ ᴍᴍʏ ᴋɪ ᴄʜᴜᴛ ᴋᴀɪsᴀ ʟᴀᴀᴅᴋʜᴀᴅᴀɪ?👻 textᴇʀᴀ 𝐋ᴜꜰꜰʏ𖤍 Pᴀᴘᴀ ᴋᴀ ʟᴜɴ ᴅᴇᴋʜ ᴋʀ??😍",
    "{text} ᴛᴇʀɪ ᴅᴀᴅɪ ᴋᴀ ʙʜᴏsᴅᴀ ᴍᴀ 𝐒ʟᴀᴛᴇ ᴋɪ ᴍɪssɪʟᴇ ᴅᴀʟᴋᴇ ᴜᴅᴀ ᴅᴜɴɢᴀ😍",
    "{text} ᴛᴇʀʏ ᴍᴍʏ ᴋᴏ miya ᴋ sᴀᴛʜ ᴄʜᴏᴅᴇɢᴀᴀ🙈",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴊᴀʙ ᴛʀᴀɪɴ ᴍᴀɪ sᴏʏᴇɢɪ ᴛᴀʙ ᴜsᴋɪ ᴘᴀɴᴛʏ ᴜᴛᴀʀ ᴋʀ sᴜᴘ sᴜᴘ ᴋʀᴅᴜɴɢᴀ😍🦈🦈🦈",
    "{text} ᴛᴇʀʏ ᴅᴀᴅɪ ᴋ ᴄʜᴜᴛᴀᴅ ᴍᴀ ᴀᴀᴍ ᴋᴀ ᴛʀᴇᴇ ʟɢᴀᴋᴇ 𝐋ᴜɴ ғᴇᴋ ᴍʀ ᴍᴀʀᴋᴇ ᴛᴏʀᴜɴɢᴀ😘🤩",
    "{text} ᴛᴇʀɪ ᴍᴍʏ 𝐋ᴜꜰꜰʏ ᴋ ᴛᴀᴛᴛᴇ ᴋ ɴɪᴄʜᴇ 👻👻 ᴍᴀsʟɪ ɢʏɪ ᴀᴀʙ ᴛᴇʀᴀ ᴘᴀᴘᴀ ʀᴏʏᴇɢᴀ😘",
    "{text} ᴛᴇʀɪ ᴋᴀʟᴀ ᴄʜᴜᴛᴀᴅ ᴡᴀʟɪ ʙʜᴇɴ ᴋ ɢᴀɴᴅ ᴍᴀɪ👻 ᴊᴀᴅᴜɪ ᴄʜᴀᴅɪ ᴅᴀʟᴅᴜɴɢᴀ😈😈😈",
    "textERI BRHEN KI KALI BURR ME textHOOK DOYA AB CHAAtext JAA USE 👽",
    "{text} ᴋɪ ᴍᴀᴀ ʜᴏʀɴᴇʏ ʜᴏ ᴋʀ ᴀᴘɴᴇ ᴋᴜᴛᴛᴀ ᴋ ᴍᴜʜ ᴍᴀɪ ʟᴇ ʟᴇᴛɪ ᴇʏ?😱",
    "{text} ᴋɪ ᴍᴀᴀ ᴀᴅɪᴠᴀsɪ ᴏɪʟ ʟɢᴀᴋᴇ ᴊᴜɴɢʟᴇ ᴍᴀ ɢᴀɴᴅ ᴅᴇᴛɪ ᴇʏ😭😭",
    "{text} ᴋɪ ᴍᴍʏ 𝐋ᴜꜰꜰʏ ᴋᴀ ʟᴏʀᴀ ʟᴇᴛᴀ ʜᴜ ᴘᴀᴀᴅ ᴍᴀʀᴛɪ ᴇʏ ᴄʜɪ🤬🤬🤬",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ʙɪᴊʟɪ ᴋ ᴋʜᴀᴍʙᴀ ᴘʀ ᴡɪʀᴇ ᴄʜᴜᴛᴀᴅ ᴍᴀ ʟᴇᴋʀ ᴛᴀᴅᴀᴘ ᴋʀ ᴍᴀʀ ɢᴀɪ😭👻",
    "{text} ᴊɪs sɪᴍ sᴀ ᴛᴜ ɴᴇᴛ ᴄʜᴀʟᴀ ʀᴀʜᴀ ᴠᴏ ᴠ ᴍᴇʀᴀ ʟᴏᴅᴀ ᴋɪ ᴋʀɪᴘᴀ ʜᴀ ᴇʏ ɢᴀʀᴇᴇʙ ᴛᴇʀʏ ᴍᴀᴀ sᴀ ᴘᴜᴄʜ😁💣",
    "{text} ʜᴀᴄᴋʟᴇ ᴍssɢ ᴍᴛ ᴋʀ ᴡᴀʀɴᴀ ᴛᴇʀᴀ ᴋʜᴀɴᴅᴀɴ ᴋᴏ ʀᴀᴏᴅ ᴘʀ ɴᴀɴɢᴀ ᴋʀᴋʀ ᴍᴜʜ ᴘʀ ɢᴀʀᴀᴍ ᴍᴜᴛ ᴅᴜɴɢᴀ😍🦈",
    "{text} ᴋɪ ᴍᴀᴀ 𝐋ᴜꜰꜰʏ ᴋ ʟᴜɴ ᴋɪ ᴘʜᴏᴛᴏ ᴅᴇᴋʜ ᴋʀ ғɪɴɢᴇʀɪɴɢ ᴋʀᴛɪ ᴇʏ🦈😭",
    "{text} ᴛᴇʀʏ ᴍᴍʏ ᴋᴀʟᴀ ᴄʜᴜᴛᴀᴅ ᴡᴀʟɪ ᴄʜᴜᴅᴀᴋʀ😈💋",
    "{text} ᴋɪ ᴍᴜᴍᴍʏ ᴍᴜᴛʜɪ ᴍᴀʀ ᴛɪ ᴇʏ?😭????",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋ ᴄʜᴜᴛᴀᴅ 😘 ᴘʀ 𝐋ᴜꜰꜰʏ ᴀᴘɴᴀ ʟᴜɴ sᴀ ᴛᴀʟɪʏᴀ ʙᴀᴊᴀʏᴇɢᴀ😈😈💋",
    "{text} ᴋɪ ᴍᴜᴍᴍʏ ᴀᴘɴɪ ᴄʜᴜᴄʜɪʏᴀ ɢᴀᴛᴇ ᴋ ʙɪᴄʜ ᴅᴀʙᴀ ᴋʀ ᴍᴀʀ ɢᴀɪ?😭😭",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ʜɪᴢʀᴇ ʙᴀɴᴋʀ ᴛʀᴀɪɴ ᴍᴀ ᴀᴛɪ ᴛᴇʀᴀ ᴘᴀᴘᴀ sᴜsᴜ ᴄʜᴀᴛɴᴇ ᴋɪ ᴅᴜᴋᴀɴ ᴋʀᴛᴀ ᴇʏ ʙᴛᴀ ᴅʏ ᴄʏᴀ sᴀʙᴋᴏ👻👻👻💣💣",
    "ᴋʏᴀᴀ?😱 {text} ᴋɪ ᴍᴍʏ ᴊᴀʙ sᴜsᴜ ᴋʀ ʀɪ ᴛʜɪ textᴀʙ ᴄʜᴜᴛ ᴍᴀɪ sᴀᴀᴘ ɢʜᴜs ɢʏᴀ ᴠᴏ ʙʜɪ ᴄᴏʙʀᴀ?😱😱",
    "{text} ᴋɪ ʙᴇʜᴇɴ ᴋʜᴀᴅɪ ʜᴏ ᴋʀ ᴍᴜᴛ ᴛɪ ᴇʏ?😱😱😱",
    "{text} ᴛᴇʀʏ ᴍᴍʏ ᴋᴏ 𝐋ᴜꜰꜰʏ ɴᴀ ɴᴀsʜᴇ ᴍᴀɪ sᴏғᴀ ᴘʀ ᴛᴀɴɢ ᴜᴛʜᴀ ᴋʀ ᴄʜᴏᴅ ᴅɪʏᴀ😁😁",
    "{text} ᴛᴇʀɪ ᴍᴍʏ 𝐋ᴜꜰꜰʏ ᴋ ᴛᴀᴛᴛᴇ ᴋ ɴɪᴄʜᴇ 👻👻 ᴍᴀsʟɪ ɢʏɪ ᴀᴀʙ ᴛᴇʀᴀ ᴘᴀᴘᴀ ʀᴏʏᴇɢᴀ😘",
    "{text} ᴛᴇʀɪ ᴍᴀᴀ ᴋɪ ᴄʜᴜᴛ ᴍᴀ ᴀᴀɢ ʟɢᴀ ᴋᴇ ʀᴀᴋʜ ᴅᴜɴɢᴀ🔥🥵",
    "{text} ᴛᴇʀᴀ ᴘᴀᴘᴀ ʀᴀɴᴅɪ ᴋʜᴀɴᴀ ᴍᴀ ɢᴀɴᴅ ᴍᴀʀ ᴋʀ ᴋᴀᴍᴀᴛᴀ ʜᴀ🩸💔",
    "{text} ᴛᴇʀɪ ʙʜᴇɴ ᴋᴏ ʀᴇᴅ ʟɪɢʜᴛ ᴍᴀ ᴄʜᴏᴅ ᴋᴇ ʙʜᴀɢᴀ ᴅᴜɴɢᴀ🚨🩸",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋɪ ɢᴀɴᴅ ᴍᴇ sᴀᴘ ᴅᴀʟ ᴋᴇ ɴᴀᴄʜᴡᴀᴜɴɢᴀ🐍💃",
    "{text} ᴛᴇʀᴀ ᴘᴜʀᴀ ᴋʜᴀɴᴅᴀɴ ʀᴀɴᴅɪ ᴋʜᴀɴᴀ ᴍᴇ ɴᴀᴄʜᴛᴀ ʜᴀ🎭🍺",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋᴏ ʟᴜғғʏ ᴋᴇ ʟᴜɴ sᴇ ɢᴀʀᴍɪ ᴅᴇᴛᴀ ʜᴜ🔥💦",
    "{text} ᴛᴇʀɪ ᴅᴀᴅɪ ʙʜᴇɴ ᴅᴏɴᴏ ᴋᴏ ᴇᴋ sᴀᴛʜ ᴄʜᴏᴅ ᴋᴇ ɴᴀᴄʜᴀᴜɴɢᴀ🎉🩸",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋɪ ᴄʜᴜᴛ ᴋɪ ʜᴏᴛᴇʟ ᴋʜᴏʟ ᴋᴇ ʀᴀᴋʜ ᴅᴜɴɢᴀ🏨🩵",
    "{text} ᴛᴇʀᴀ ʙᴀᴀᴘ ᴄʜᴀᴜᴋɪᴅᴀʀ ʜᴀ textERI MAKI ɢᴀɴᴅ ᴋᴀ👻🚔",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋᴏ ɢᴀɴɢ ʙᴀɴɢ ᴋʀᴋᴇ ᴛʀᴀɪɴ sᴇ ᴜᴛᴀʀᴡᴀᴜɴɢᴀ🚂🩸",
    "{text} ᴛᴇʀɪ ʙʜᴇɴ ᴋɪ ɢᴀɴᴅ ᴍᴇ ʟᴜғғʏ ᴋᴀ ʟᴏɢᴏ ᴛᴀᴛᴛᴏᴏ ᴋᴀʀᴀ ᴅᴜɴɢᴀ🕸️🔱",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋɪ ᴄʜᴜᴛ ᴍᴀ ᴛʀɪᴘʟᴇ x ᴠɪᴅᴇᴏ ʙᴀɴᴀᴋᴇ ᴠɪʀᴀʟ ᴋᴀʀ ᴅᴜɴɢᴀ📸🔥",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋᴏ ᴅᴏɢɢʏ sᴛʏʟᴇ ᴍᴀ ᴄʜᴏᴅ ᴋᴇ ɴᴀᴄʜᴇ ɢɪʀᴀ ᴅᴜɴɢᴀ🐕🩸",
    "{text} ᴛᴇʀɪ ʙʜᴇɴ ᴋɪ ᴄʜᴜᴛ ᴍᴀ ʟᴜғғʏ ɢᴀɴɢ ᴋᴀ ʀᴀᴠᴀ ʟɢᴀ ᴅᴜɴɢᴀ🔊🩵",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋɪ ɢᴀɴᴅ ᴍᴀ ᴛᴀʟᴀʙ ᴋᴀ ᴘᴀɴɪ ʙʜᴀʀ ᴋᴇ ɴᴀᴄʜᴀᴜɴɢᴀ🌊🩸",
    "{text} ᴛᴇʀᴀ ᴘᴀᴘᴀ ʀᴀɴᴅɪ ᴋʜᴀɴᴀ ᴍᴀ ᴍᴜᴛ ᴋᴇ ʙᴇᴄʜ ᴅᴜɴɢᴀ🍺🩸",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋᴏ ɢᴀʏ sᴛʏʟᴇ ᴍᴀ ᴄʜᴏᴅ ᴋᴇ ᴠɪʀᴀʟ ᴋᴀʀ ᴅᴜɴɢᴀ📱🔥",
    "{text} ᴛᴇʀɪ ᴅᴀᴅɪ ᴋɪ ᴄʜᴜᴛ ᴍᴀ ᴄᴏᴋᴇ sᴛᴜᴅɪᴏ ᴋʜᴏʟ ᴅᴜɴɢᴀ🥤🩸",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋɪ ɢᴀɴᴅ ᴍᴀ sᴛᴀᴅɪᴜᴍ ᴍᴀ ᴍᴀᴛᴄʜ ᴋᴀʀᴀ ᴅᴜɴɢᴀ🏟️🩸",
    "{text} ᴛᴇʀɪ ʙʜᴇɴ ᴋɪ ᴄʜᴜᴛ ᴍᴀ ʟᴜғғʏ ɢᴀɴɢ ᴋᴀ ᴛᴀᴛᴛᴏᴏ ʙᴀɴᴡᴀ ᴅᴜɴɢᴀ🕸️🩵",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋᴏ ᴘᴜʙʟɪᴄ ᴍᴀ ᴄʜᴏᴅ ᴋᴇ ᴠɪʀᴀʟ ᴋᴀʀ ᴅᴜɴɢᴀ📢🩸",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋɪ ɢᴀɴᴅ ᴍᴀ ᴅᴇᴇᴘғᴀᴋᴇ ʙᴀɴᴀᴋᴇ ᴘᴏsᴛ ᴋᴀʀ ᴅᴜɴɢᴀ📸🔥",
    "{text} ᴛᴇʀᴇ ᴋʜᴀɴᴅᴀɴ ᴋɪ ᴄʜᴜᴛ ᴍᴀ ᴅʀᴏɴᴇ ᴄᴀᴍᴇʀᴀ ʟᴀɢᴀ ᴅᴜɴɢᴀ🚁🩸",
    "{text} ᴛᴇʀɪ ᴍᴍʏ ᴋᴏ ʟᴜғғʏ ɢᴀɴɢ ᴋᴇ ʜᴀᴡᴀʟᴇ ᴋᴀʀ ᴅᴜɴɢᴀ🏴‍☠️🩸",
    "{text} ᴛᴇʀɪ ʙʜᴇɴ ᴋɪ ᴄʜᴜᴛ ᴍᴀ ʀᴀᴘ ʙᴀᴛᴛʟᴇ ᴋᴀʀᴡᴀ ᴅᴜɴɢᴀ🎤🩸",
]

PILLE_TEXT = "{user} 𝗕𝗛𝗔𝗡𝗚𝗜 𝗠𝗔𝗗𝗔𝗥𝗖𝗛⭕️𝗗 𓂃𓂃𓂃𓂃〉〈{emojie}〉〈𓂃𓂃𓂃𓂃𓂃𓂃..!¡"
PILLE_EMOJIS = ["❄️","🧊","🥶","🌨️","☃️","⛄","⛷️","🏂","⛸️","🏔️","🍧","🍨","🍦","🛷"]

CHUD_REPLIES = [
    "TERY MA RAND BTT KHTMM",
    "TERI MA KI KACCHI ME LAWDA MERA OK?",
    "AWW ACHA TMKC",
    "CHLNA TMKC TUJHE BHAWW DUN? HTT CHMR",
    "EK KAAM TU CHHA KRTA HAI AUR WO KAAM HAI LUFFY KA LAWDA SEHLANA 😉",
    "TERI MA NALI M CHODU",
    "MA KE LODE LUN TE VAJJ",
    "TMKC PE MUKKE MAARU",
    "ACHA RUNDYKE ?",
    "OYE GULAM CHUPP",
    "TMKC PE THOOK DIYA MENE ROO AB",
    "(MEHKA LADLE MEOWW) TMKC ME MUH DEKE YHI BOLUNGA 😉",
    "TERA REAL FATHER LUFFY",
    "TERI MAA KO NANGI KRKE BAZAR ME CHODU",
    "GAREEB MAA KI GREEB CHUT SE NIKLE HUE GAREEB LADKE AWAZ NICHE KRR 😂",
    "HURRRREE TERI MAA TO MARR GYI REHH",
    "CHUDEGA KYA REHHHH??",
    "JALDI TYPE KRR REE MAA K LUND",
    "TERI BEHEN K GALE PE PATTA BANDH KRR CHODU 😂",
    "KYA RE DALIT MADARCHOD HAWA ME UDEGA ?",
    "CHOTE ABHI TU ITNA BADA NHI HUA JO LUFFY K SAMNE AWAZ UCHI KREGA",
    "TMKC KO I LOVE UHH LUND SE 😂",
    "𝐂ʜʟ 𝐇ᴀʀᴍᴢᴀᴅ𝐈 𝐊ᴇ लड़के",
    "oi 𝐓ᴇʀɪ 𝐌‌ᴀᴀ गुलाम",
    "chl rndyce chud ke dikha",
    "TERI 𝐌ᴀᴀ 𝐌ᴀʀʀ 𝐆ᴀʏɪ naacho  !",
    "tera baap bass LUFFY hai 😂🎀",
    " CHUDAI FEEL KRR RUNDYKE",
    "ROO MTT TERI MAA ME HI CHODUNGA BSS KHUSH 😉",
]

HEARTRR = [
    "⤹𝀘🧡⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘🧡⤸",
    "⤹𝀘💛⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💛⤸",
    "⤹𝀘💚⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💚⤸",
    "⤹𝀘💙⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💙⤸",
    "⤹𝀘💜⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💜⤸",
    "⤹𝀘🖤⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘🖤⤸",
    "⤹𝀘🤍⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘🤍⤸",
    "⤹𝀘🤎⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘🤎⤸",
    "⤹𝀘💖⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💖⤸",
    "⤹𝀘💗⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💗⤸",
    "⤹𝀘💓⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💓⤸",
    "⤹𝀘💞⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💞⤸",
    "⤹𝀘💕⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💕⤸",
    "⤹𝀘💘⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💘⤸",
    "⤹𝀘💝⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💝⤸",
    "⤹𝀘💟⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘💟⤸",
    "⤹𝀘❣️⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘❣️⤸",
    "⤹𝀘❤️‍🔥⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘❤️‍🔥⤸",
    "⤹𝀘❤️‍🩹⤸ ⛧ 𝐒𝐋𝐀𝐕𝐄 ⛧ 𓊈 𝐓𝐌𝐊𝐂 𓊉 ⛧ ⤹𝀘❤️‍🩹⤸",
]

FLAGRR = [
    " ོ༘₊⁺🇮🇳 ₊⁺⋆.˚ TERI MA KO INDIA ME CHODU  ོ༘₊⁺🇮🇳 ₊⁺⋆.˚",
    " ོ༘₊⁺🇯🇵 ₊⁺⋆.˚ TERI MA KO JAPAN ME CHODU ོ༘₊⁺🇯🇵 ₊⁺⋆. ",
    " ₊⁺🇺🇸 ₊⁺⋆.˚ TERI MA KO USA ME CHODU ོ༘₊⁺🇺🇸 ₊⁺⋆.˚",
    " ོ༘₊⁺🇬🇧 ₊⁺⋆.˚ TERI MA KO UK ME CHODU ོ༘₊⁺🇬🇧 ₊⁺⋆.˚",
    " ོ༘₊⁺🇰🇷 ₊⁺⋆.˚TERI MA KO KOREA ME CHODU ོ༘₊⁺🇰🇷 ₊⁺⋆.˚",
    " ོ༘₊⁺🇩🇪 ₊⁺⋆.˚ TERI MA KO GERMANY ME CHODU ོ༘₊⁺🇩🇪 ₊⁺⋆.˚",
    " ོ༘₊⁺🇫🇷 ₊⁺⋆.˚TERI MA KO FRANCE ME CHODU ོ༘₊⁺🇫🇷 ₊⁺⋆.˚",
    " ོ༘₊⁺🇮🇹 ₊⁺⋆.˚ TERI MA KO ITALY ME CHODU ོ༘₊⁺🇮🇹 ₊⁺⋆.˚",
    " ོ༘₊⁺🇧🇷 ₊⁺⋆.˚TERI MA KO BRAZIL ME CHODU ོ༘₊⁺🇧🇷 ₊⁺⋆.˚",
    " ོ༘₊⁺🇨🇦 ₊⁺⋆.˚TERI MA KO CANADA ME CHODU ོ༘₊⁺🇨🇦 ₊⁺⋆.˚",
]

# ═══════════════════════════════════════════════════════════════════════
#   KEYBOARDS
# ═══════════════════════════════════════════════════════════════════════

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ 𝐀𝐃𝐃 𝐓𝐎𝐊𝐄𝐍 / 𝐁𝐎𝐓", callback_data="menu_addbot")],
        [InlineKeyboardButton("🏴‍☠️ 𝗟𝗨𝗙𝗙𝗬 𝗡𝗖", callback_data="menu_luffy"),
         InlineKeyboardButton("👑 𝗩𝗘𝗚𝗘𝗧𝗔 𝗡𝗖", callback_data="menu_vegeta")],
        [InlineKeyboardButton("💥 𝗦𝗣𝗔𝗠", callback_data="menu_spam"),
         InlineKeyboardButton("🔥 𝗥𝗔𝗜𝗗", callback_data="menu_raid")],
        [InlineKeyboardButton("⚙️ 𝗕𝗢𝗧 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦", callback_data="menu_botsettings"),
         InlineKeyboardButton("🎯 𝗧𝗔𝗥𝗚𝗘𝗧𝗦", callback_data="menu_targets")],
        [InlineKeyboardButton("🖼️ 𝗣𝗙𝗣 𝗟𝗢𝗢𝗣", callback_data="menu_pfp"),
         InlineKeyboardButton("🎮 𝗙𝗨𝗡", callback_data="menu_fun")],
        [InlineKeyboardButton("🛡️ 𝗚𝗥𝗢𝗨𝗣 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦", callback_data="menu_group"),
         InlineKeyboardButton("🛑 𝗦𝗧𝗢𝗣 𝗧𝗔𝗦𝗞", callback_data="menu_stop")],
        [InlineKeyboardButton("⚡ 𝗦𝗣𝗘𝗘𝗗 𝗖𝗢𝗡𝗧𝗥𝗢𝗟", callback_data="menu_speed")],
        [InlineKeyboardButton("✏️ 𝗘𝗗𝗜𝗧𝗦", callback_data="menu_edits")],
    ])

def back_button(target: str = "menu_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data=target)]])

# ═══════════════════════════════════════════════════════════════════════
#   CHILD BOT MANAGER
# ═══════════════════════════════════════════════════════════════════════

class ChildBotManager:
    def __init__(self):
        self.bots: Dict[int, Dict] = {}
        self._lock = asyncio.Lock()

    def save(self):
        try:
            data = [
                {"token": e["token"], "username": e["username"], "id": e["id"]}
                for e in self.bots.values()
            ]
            with open(BOTS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.warning(f"bots save failed: {e}")

    def load_tokens(self) -> List[Dict]:
        try:
            if os.path.exists(BOTS_FILE):
                with open(BOTS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            log.warning(f"bots load failed: {e}")
        return []

    async def add_and_start(self, token: str) -> Dict:
        token = token.strip()
        if not token or ":" not in token:
            raise ValueError("Invalid token format (missing ':')")
        async with self._lock:
            probe = Bot(token=token)
            me = await probe.get_me()
            if me.id in self.bots:
                return {**self.bots[me.id], "_existed": True}
            app = ApplicationBuilder().token(token).build()
            register_child_handlers(app)
            try:
                await app.initialize()
                await app.start()
                await app.updater.start_polling(drop_pending_updates=True)
            except Exception:
                try:
                    await app.shutdown()
                except Exception:
                    pass
                raise
            entry = {
                "token": token,
                "username": me.username,
                "id": me.id,
                "bot": app.bot,
                "app": app,
            }
            self.bots[me.id] = entry
            self.save()
            log.info(f"✅ Child bot @{me.username} (id={me.id}) started")
            return {**entry, "_existed": False}

    async def stop_and_remove(self, identifier) -> Optional[str]:
        async with self._lock:
            entry = None
            if isinstance(identifier, int):
                entry = self.bots.get(identifier)
            else:
                target = str(identifier).lower().lstrip("@")
                for b in self.bots.values():
                    if b["username"].lower() == target or str(b["id"]) == target:
                        entry = b
                        break
            if not entry:
                return None
            uname = entry["username"]
            app = entry["app"]
            try:
                await app.updater.stop()
            except Exception:
                pass
            try:
                await app.stop()
            except Exception:
                pass
            try:
                await app.shutdown()
            except Exception:
                pass
            del self.bots[entry["id"]]
            self.save()
            log.info(f"🗑️ Child bot @{uname} stopped")
            return uname

    async def start_all_from_disk(self):
        for entry in self.load_tokens():
            try:
                await self.add_and_start(entry["token"])
            except Exception as e:
                log.warning(f"❌ Failed to start @{entry.get('username', '?')}: {e}")

    async def stop_all(self):
        apps = [e["app"] for e in self.bots.values()]
        for app in apps:
            try:
                await app.updater.stop()
            except Exception:
                pass
        for app in apps:
            try:
                await app.stop()
            except Exception:
                pass
        for app in apps:
            try:
                await app.shutdown()
            except Exception:
                pass
        self.bots.clear()

    def get_all(self) -> List[Dict]:
        return list(self.bots.values())

CHILD_MGR = ChildBotManager()

def all_bots() -> List[Dict]:
    return CHILD_MGR.get_all()

# ═══════════════════════════════════════════════════════════════════════
#   PER-BOT WORKERS
# ═══════════════════════════════════════════════════════════════════════

async def _per_bot_title_worker(bot_entry: Dict, chat_id: int, title_builder: Callable,
                                 stop_ref: Dict, interval: float):
    bot = bot_entry["bot"]
    bid = bot_entry["id"]
    while not stop_ref.get("stop"):
        if not _cooldown_ok(bid):
            await asyncio.sleep(0.05)
            continue
        try:
            title = title_builder()[:128]
            await asyncio.wait_for(bot.set_chat_title(chat_id, title), timeout=2.0)
            get_guard(bid)._successes += 1
        except RetryAfter as e:
            _set_cooldown(bid, float(e.retry_after))
        except asyncio.TimeoutError:
            _set_cooldown(bid, 2.0)
        except (Forbidden, BadRequest):
            pass
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(interval)

async def _per_bot_send_worker(bot_entry: Dict, chat_id: int, text_builder: Callable,
                                stop_ref: Dict, interval: float, reply_to: Optional[int] = None):
    bot = bot_entry["bot"]
    bid = bot_entry["id"]
    while not stop_ref.get("stop"):
        if not _cooldown_ok(bid):
            await asyncio.sleep(0.05)
            continue
        try:
            text = text_builder() if callable(text_builder) else text_builder
            await asyncio.wait_for(
                bot.send_message(chat_id, text, reply_to_message_id=reply_to),
                timeout=2.0
            )
            get_guard(bid)._successes += 1
        except RetryAfter as e:
            _set_cooldown(bid, float(e.retry_after))
        except asyncio.TimeoutError:
            _set_cooldown(bid, 2.0)
        except (Forbidden, BadRequest):
            pass
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(interval)

async def _per_bot_raid_worker(bot_entry: Dict, chat_id: int, reply_to: int,
                                target_name: str, templates: List[str], react: bool,
                                stop_ref: Dict, interval: float):
    bot = bot_entry["bot"]
    bid = bot_entry["id"]
    while not stop_ref.get("stop"):
        if not _cooldown_ok(bid):
            await asyncio.sleep(0.05)
            continue
        try:
            tpl = random.choice(templates)
            text = tpl.format(text=target_name)
            sent = await asyncio.wait_for(
                bot.send_message(chat_id, text, reply_to_message_id=reply_to),
                timeout=2.0
            )
            get_guard(bid)._successes += 1
            if react and sent and HAS_REACTIONS:
                try:
                    await asyncio.wait_for(
                        bot.set_message_reaction(
                            chat_id=chat_id, message_id=sent.message_id,
                            reaction=[ReactionTypeEmoji(emoji="🤣")]
                        ), timeout=1.0
                    )
                except Exception:
                    pass
        except RetryAfter as e:
            _set_cooldown(bid, float(e.retry_after))
        except asyncio.TimeoutError:
            _set_cooldown(bid, 2.0)
        except (Forbidden, BadRequest):
            pass
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(interval)

async def _per_bot_pfp_worker(bot_entry: Dict, chat_id: int, images: List[str],
                               stop_ref: Dict, interval: float):
    bot = bot_entry["bot"]
    bid = bot_entry["id"]
    if not images:
        return
    idx = random.randint(0, len(images) - 1)
    while not stop_ref.get("stop"):
        if not _cooldown_ok(bid):
            await asyncio.sleep(0.05)
            continue
        try:
            img = images[idx % len(images)]
            await asyncio.wait_for(
                bot.set_chat_photo(chat_id=chat_id, photo=img),
                timeout=3.0
            )
            get_guard(bid)._successes += 1
            idx += 1
        except RetryAfter as e:
            _set_cooldown(bid, float(e.retry_after))
        except asyncio.TimeoutError:
            _set_cooldown(bid, 2.0)
        except (Forbidden, BadRequest):
            pass
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(interval)

# ═══════════════════════════════════════════════════════════════════════
#   DOT COMMAND DISPATCHER — single handler, universal routing
# ═══════════════════════════════════════════════════════════════════════

DOT_COMMANDS: Dict[str, Callable] = {}

def dot_command(name: str):
    """Register a handler for a specific dot-command."""
    def decorator(fn):
        DOT_COMMANDS[name.lower()] = fn
        return fn
    return decorator

async def dot_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Single dispatcher — routes ALL dot commands."""
    msg = update.effective_message
    if not msg or not msg.text:
        return
    if not msg.text.startswith("."):
        return
    parts = msg.text.split()
    if not parts:
        return
    cmd = parts[0][1:].lower().split("@")[0]
    if not cmd:
        return
    args = parts[1:]
    handler = DOT_COMMANDS.get(cmd)
    if handler is None:
        return
    context.args = args
    try:
        await handler(update, context)
    except Exception as e:
        log.exception(f"❌ dot command .{cmd} crashed: {type(e).__name__}: {e}")
        try:
            await msg.reply_text(
                f"❌ `.{cmd}` error: `{type(e).__name__}: {str(e)[:150]}`",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════════════
#   AUTH DECORATORS
# ═══════════════════════════════════════════════════════════════════════

def sudo_cmd(name: Optional[str] = None):
    """Auth + optional dedup for sudo/owner-only commands."""
    def decorator(fn):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            if not user or not is_authorized(user.id):
                try:
                    m = update.effective_message
                    if m:
                        await m.reply_text(AUTHORIZATION_MSG)
                except Exception:
                    pass
                return
            if name:
                chat = update.effective_chat
                msg = update.effective_message
                if chat and msg:
                    if not await claim_once(chat.id, name, msg.message_id):
                        return
            return await fn(update, context)
        return wrapper
    return decorator

def owner_cmd(name: Optional[str] = None):
    """Owner-only + optional dedup."""
    def decorator(fn):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            if not user or user.id != OWNER_ID:
                try:
                    m = update.effective_message
                    if m:
                        await m.reply_text("🚫 ᴏɴʟʏ ꜱᴇʀᴠᴇʀ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜꜱᴇ ᴛꜱ ꜱʜʏᴛ ¡!")
                except Exception:
                    pass
                return
            if name:
                chat = update.effective_chat
                msg = update.effective_message
                if chat and msg:
                    if not await claim_once(chat.id, name, msg.message_id):
                        return
            return await fn(update, context)
        return wrapper
    return decorator

def auth_only(fn):
    """Auth-only (no dedup) — for NC/spam/raid that handle claim internally."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_authorized(user.id):
            try:
                m = update.effective_message
                if m:
                    await m.reply_text(AUTHORIZATION_MSG)
            except Exception:
                pass
            return
        return await fn(update, context)
    return wrapper

# ═══════════════════════════════════════════════════════════════════════
#   MASTER-ONLY COMMANDS
# ═══════════════════════════════════════════════════════════════════════

@dot_command("start")
@dot_command("menu")
@sudo_cmd(name="start")
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    media_type = CFG.get("start_media_type")
    media_id = CFG.get("start_media_file_id")
    text = CFG["start_text"]
    kb = main_menu_kb()
    msg = update.effective_message
    if not msg:
        return
    if media_type and media_id:
        try:
            if media_type == "photo":
                await msg.reply_photo(photo=media_id, caption=text, reply_markup=kb)
                return
            if media_type == "video":
                await msg.reply_video(video=media_id, caption=text, reply_markup=kb)
                return
            if media_type == "animation":
                await msg.reply_animation(animation=media_id, caption=text, reply_markup=kb)
                return
        except Exception:
            pass
    try:
        await msg.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    except BadRequest:
        try:
            await msg.reply_text(text, reply_markup=kb)
        except Exception:
            pass

@dot_command("add")
@owner_cmd(name="add")
async def add_bot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not context.args:
        await msg.reply_text(
            "Usage:\n`.add <TOKEN>`\n`.add <TOKEN1>,<TOKEN2>,<TOKEN3>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    raw = " ".join(context.args)
    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    if not tokens:
        await msg.reply_text("❌ No tokens found")
        return
    status = await msg.reply_text(f"⏳ Adding {len(tokens)} bot(s)...")
    results = []
    for tok in tokens:
        try:
            e = await CHILD_MGR.add_and_start(tok)
            tag = "already running" if e.get("_existed") else "started"
            results.append(f"✅ @{e['username']} (`{e['id']}`) — {tag}")
        except Exception as ex:
            short = tok[:20] + "..." if len(tok) > 20 else tok
            results.append(f"❌ `{short}` — {str(ex)[:80]}")
    try:
        await status.edit_text(
            f"*BOT ADD RESULTS ({len(tokens)}):*\n\n" + "\n".join(results) +
            f"\n\n*Total active:* `{len(all_bots())}`",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        try:
            await msg.reply_text("\n".join(results), parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await msg.reply_text("\n".join(results))

@dot_command("delbot")
@owner_cmd(name="delbot")
async def del_bot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not context.args:
        await msg.reply_text(
            "Usage:\n`.delbot <username>`\n`.delbot <username1>,<username2>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    raw = " ".join(context.args)
    targets = [t.strip().lstrip("@") for t in raw.split(",") if t.strip()]
    results = []
    for t in targets:
        uname = await CHILD_MGR.stop_and_remove(t)
        if uname:
            results.append(f"✅ Removed @{uname}")
        else:
            results.append(f"❌ Not found: `{t}`")
    await msg.reply_text("\n".join(results), parse_mode=ParseMode.MARKDOWN)

@dot_command("ok")
@owner_cmd(name="ok")
async def add_sudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    uid = None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        uid = msg.reply_to_message.from_user.id
    elif context.args:
        try:
            uid = int(context.args[0])
        except ValueError:
            pass
    if not uid:
        await msg.reply_text("Reply to a user or `.ok <user_id>`")
        return
    SUDO_USERS.add(uid)
    save_sudo()
    await msg.reply_text(f"✅ Added `{uid}` to sudo.", parse_mode=ParseMode.MARKDOWN)

@dot_command("delok")
@owner_cmd(name="delok")
async def del_sudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    uid = None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        uid = msg.reply_to_message.from_user.id
    elif context.args:
        try:
            uid = int(context.args[0])
        except ValueError:
            pass
    if not uid:
        await msg.reply_text("Reply to a user or `.delok <id>`")
        return
    SUDO_USERS.discard(uid)
    save_sudo()
    await msg.reply_text(f"✅ Removed `{uid}` from sudo.", parse_mode=ParseMode.MARKDOWN)

@dot_command("sudo")
@owner_cmd()
async def list_sudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not SUDO_USERS:
        await update.effective_message.reply_text("❌ No sudo users.")
        return
    await update.effective_message.reply_text(
        "👑 *𝐒𝐔𝐃𝐎*\n\n" + "\n".join(f"• `{u}`" for u in SUDO_USERS),
        parse_mode=ParseMode.MARKDOWN
    )

@dot_command("setstarttext")
@owner_cmd(name="setstarttext")
async def setstarttext_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not context.args:
        await msg.reply_text(
            "Usage: `.setstarttext <new text>`\n"
            "Or reply to a message with `.setstarttext` (uses replied text)"
        )
        return
    CFG["start_text"] = " ".join(context.args)
    save_config()
    await msg.reply_text("✅ Start menu text updated.")

@dot_command("resetstart")
@owner_cmd(name="resetstart")
async def resetstart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    CFG["start_text"] = DEFAULT_MENU_HEADER
    CFG["start_media_type"] = None
    CFG["start_media_file_id"] = None
    save_config()
    await update.effective_message.reply_text("✅ Reverted to default branding.")

@dot_command("setstartmedia")
@owner_cmd(name="setstartmedia")
async def setstartmedia_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    r = msg.reply_to_message
    if not r:
        await msg.reply_text("❌ Reply to a photo/video/animation.")
        return
    if r.video:
        CFG["start_media_type"] = "video"
        CFG["start_media_file_id"] = r.video.file_id
    elif r.animation:
        CFG["start_media_type"] = "animation"
        CFG["start_media_file_id"] = r.animation.file_id
    elif r.photo:
        CFG["start_media_type"] = "photo"
        CFG["start_media_file_id"] = r.photo[-1].file_id
    else:
        await msg.reply_text("❌ Unsupported media type.")
        return
    save_config()
    await msg.reply_text(f"✅ Start media set as {CFG['start_media_type']}")

@dot_command("setgomedia")
@owner_cmd(name="setgomedia")
async def setgomedia_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    r = msg.reply_to_message
    if not r:
        await msg.reply_text("❌ Reply to a photo/video/animation.")
        return
    if r.video:
        CFG["game_over_media"] = r.video.file_id
        CFG["game_over_type"] = "video"
    elif r.animation:
        CFG["game_over_media"] = r.animation.file_id
        CFG["game_over_type"] = "animation"
    elif r.photo:
        CFG["game_over_media"] = r.photo[-1].file_id
        CFG["game_over_type"] = "photo"
    else:
        await msg.reply_text("❌ Unsupported media type.")
        return
    save_config()
    await msg.reply_text(f"✅ Game over media set as {CFG['game_over_type']}")

@dot_command("dfn")
@owner_cmd(name="dfn")
async def gameover_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not msg or not chat:
        return
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    user = update.effective_user
    name = f"@{user.username}" if user and user.username else (user.first_name if user else "UNKNOWN")
    gn = chat.title if chat.title else "UNKNOWN GROUP"
    text = (
        f"═════════════════════════\n"
        f"Ꮐᴀᴍᴇ ꪮᴠᴇʀ Ͳɪᴍᴇ - {now.strftime('%I:%M:%S %p')}\n"
        f"Ꭰᴀᴛᴇ - {now.strftime('%d %B %Y')} (IST)\n\n"
        f"Ꭺʙʙ Ᏼᴀᴀᴘ Ꮶᴇ Ꭺɢɢᴇ\nᎻᴀᴡᴀʙᴀᴢᴢɪ Ꮶᴀʀɴᴇ Ꮇᴛᴛ Ꭺɴᴀᴀ\n\n"
        f"Ꮐʀᴏᴜᴘ - {gn}\n\nͲᴇʀɪ Ꮇᴀᴀ Ꮯʜᴜᴅ Ꮶᴇ Ꭰꜰɴ Ᏼʏ - {name}\n"
        f"═════════════════════════"
    )
    try:
        await msg.reply_video(video=CFG["game_over_media"], caption=text)
    except Exception:
        try:
            await msg.reply_animation(animation=CFG["game_over_media"], caption=text)
        except Exception:
            try:
                await msg.reply_photo(photo=CFG["game_over_media"], caption=text)
            except Exception:
                pass

# ═══════════════════════════════════════════════════════════════════════
#   TARGETS COMMANDS
# ═══════════════════════════════════════════════════════════════════════

@dot_command("settarget")
@sudo_cmd(name="settarget")
async def set_target_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user with `.settarget <label>`")
        return
    if not context.args:
        await msg.reply_text("Usage: `.settarget <label>`")
        return
    label = context.args[0].lower()
    uid = msg.reply_to_message.from_user.id
    TARGETS[uid] = label
    TARGETS_REV[uid] = uid
    save_targets()
    await msg.reply_text(f"✅ Set target `{label}` → `{uid}`", parse_mode=ParseMode.MARKDOWN)

@dot_command("deltarget")
@sudo_cmd(name="deltarget")
async def del_target_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    uid = None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        uid = msg.reply_to_message.from_user.id
    elif context.args:
        try:
            uid = int(context.args[0])
        except ValueError:
            pass
    if not uid or uid not in TARGETS:
        await msg.reply_text("❌ Target not found.")
        return
    del TARGETS[uid]
    TARGETS_REV.pop(uid, None)
    save_targets()
    await msg.reply_text(f"✅ Removed target `{uid}`", parse_mode=ParseMode.MARKDOWN)

# ═══════════════════════════════════════════════════════════════════════
#   STOP / SPEED COMMANDS
# ═══════════════════════════════════════════════════════════════════════

@dot_command("s")
@sudo_cmd(name="s")
async def stop_task_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat or not context.args:
        await msg.reply_text("Usage: `.s <command_name>` or `.sall`")
        return
    name = context.args[0].lower()
    n = _cancel_named(chat.id, name)
    if name == "slide":
        SLIDE_TRACKERS[chat.id] = []
        n += 1
    await msg.reply_text(f"🛑 Stopped `{name}` ({n} tasks)")

@dot_command("sall")
@sudo_cmd(name="sall")
async def stop_all_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return
    total = 0
    for cid in list(NAMED_TASKS.keys()):
        total += _cancel_all_named(cid)
    ACTIVE_TASKS.clear()
    SLIDE_TRACKERS.clear()
    await msg.reply_text(f"🛑🛑 ALL TASKS STOPPED ({total})")

@dot_command("speed")
@sudo_cmd(name="speed")
async def speed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat:
        return
    if len(context.args) < 2:
        await msg.reply_text(
            "⚡ *SPEED CONTROL*\n\n"
            "Usage: `.speed <cat> <seconds>`\n"
            "Categories: `nc`, `spam`, `raid`, `pfp`, `slide`, `all`\n\n"
            "Example: `.speed all 0.01` (turbo)\n"
            "Default: nc=0.1, spam=0.02, raid=0.05, pfp=0.1",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    key = context.args[0].lower()
    try:
        val = max(0.0, float(context.args[1]))
    except ValueError:
        await msg.reply_text("❌ Invalid seconds value")
        return
    if key not in list(DEFAULT_INTERVALS.keys()) + ["all"]:
        await msg.reply_text("❌ Invalid category")
        return
    set_interval(chat.id, key, val)
    await msg.reply_text(f"⚡ Speed: `{key}` = `{val}s`", parse_mode=ParseMode.MARKDOWN)

# ═══════════════════════════════════════════════════════════════════════
#   NC COMMANDS
# ═══════════════════════════════════════════════════════════════════════

async def _nc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, kind: str):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await msg.reply_text("❌ Use this in a group.")
        return
    if not context.args:
        await msg.reply_text(f"Usage: `.{kind}nc{{1-10}} <text>`", parse_mode=ParseMode.MARKDOWN)
        return
    cmd = msg.text.split()[0].split("@")[0].lstrip(".")
    m = re.match(rf"{kind}nc(\d+)$", cmd)
    if not m:
        return
    n = int(m.group(1))
    if not (1 <= n <= 10):
        await msg.reply_text("❌ Number must be 1-10")
        return
    text = await _resolve_target(chat.id, context.bot, context.args)
    if not text and msg.reply_to_message and msg.reply_to_message.from_user:
        tu = msg.reply_to_message.from_user
        text = f"@{tu.username}" if tu.username else tu.first_name
    bots = all_bots()
    if not bots:
        await msg.reply_text("❌ No child bots. Use `.add <token>` on master.")
        return
    interval = get_interval(chat.id, "nc")
    stop_ref = {"stop": False}

    def title_builder() -> str:
        t = build_luffy_nc(n, text) if kind == "luffy" else build_vegeta_nc(n, text)
        return t + random.choice(INVIS_SUFFIXES)

    def factory() -> List[asyncio.Task]:
        return [
            asyncio.create_task(
                _per_bot_title_worker(b, chat.id, title_builder, stop_ref, interval)
            )
            for b in bots
        ]

    if not await claim_and_start_multi(chat.id, cmd, msg.message_id, factory):
        return
    ACTIVE_TASKS[chat.id] = cmd
    try:
        await msg.reply_text(
            f"⚡ 𝐍𝐂 {n} 𝐓𝐔𝐑𝐁𝐎 — {len(bots)} bots × interval `{interval}s` "
            f"(runs until `.s {cmd}` or `.sall`)",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        pass

@dot_command("luffync1")
@auth_only
async def luffync1(update, context): await _nc_handler(update, context, "luffy")

@dot_command("luffync2")
@auth_only
async def luffync2(update, context): await _nc_handler(update, context, "luffy")

@dot_command("luffync3")
@auth_only
async def luffync3(update, context): await _nc_handler(update, context, "luffy")

@dot_command("luffync4")
@auth_only
async def luffync4(update, context): await _nc_handler(update, context, "luffy")

@dot_command("luffync5")
@auth_only
async def luffync5(update, context): await _nc_handler(update, context, "luffy")

@dot_command("luffync6")
@auth_only
async def luffync6(update, context): await _nc_handler(update, context, "luffy")

@dot_command("luffync7")
@auth_only
async def luffync7(update, context): await _nc_handler(update, context, "luffy")

@dot_command("luffync8")
@auth_only
async def luffync8(update, context): await _nc_handler(update, context, "luffy")

@dot_command("luffync9")
@auth_only
async def luffync9(update, context): await _nc_handler(update, context, "luffy")

@dot_command("luffync10")
@auth_only
async def luffync10(update, context): await _nc_handler(update, context, "luffy")

@dot_command("vegetanc1")
@auth_only
async def vegetanc1(update, context): await _nc_handler(update, context, "vegeta")

@dot_command("vegetanc2")
@auth_only
async def vegetanc2(update, context): await _nc_handler(update, context, "vegeta")

@dot_command("vegetanc3")
@auth_only
async def vegetanc3(update, context): await _nc_handler(update, context, "vegeta")

@dot_command("vegetanc4")
@auth_only
async def vegetanc4(update, context): await _nc_handler(update, context, "vegeta")

@dot_command("vegetanc5")
@auth_only
async def vegetanc5(update, context): await _nc_handler(update, context, "vegeta")

@dot_command("vegetanc6")
@auth_only
async def vegetanc6(update, context): await _nc_handler(update, context, "vegeta")

@dot_command("vegetanc7")
@auth_only
async def vegetanc7(update, context): await _nc_handler(update, context, "vegeta")

@dot_command("vegetanc8")
@auth_only
async def vegetanc8(update, context): await _nc_handler(update, context, "vegeta")

@dot_command("vegetanc9")
@auth_only
async def vegetanc9(update, context): await _nc_handler(update, context, "vegeta")

@dot_command("vegetanc10")
@auth_only
async def vegetanc10(update, context): await _nc_handler(update, context, "vegeta")

# ═══════════════════════════════════════════════════════════════════════
#   SPAM COMMANDS
# ═══════════════════════════════════════════════════════════════════════

async def _spam_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, n: int):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await msg.reply_text("❌ Use in a group.")
        return
    if not context.args:
        await msg.reply_text(f"Usage: `.spam{n} <text>`", parse_mode=ParseMode.MARKDOWN)
        return
    cmd = f"spam{n}"
    body = build_spam(n, " ".join(context.args))
    bots = all_bots()
    if not bots:
        await msg.reply_text("❌ No child bots.")
        return
    interval = get_interval(chat.id, "spam")
    stop_ref = {"stop": False}

    def factory() -> List[asyncio.Task]:
        return [
            asyncio.create_task(
                _per_bot_send_worker(b, chat.id, body, stop_ref, interval)
            )
            for b in bots
        ]

    if not await claim_and_start_multi(chat.id, cmd, msg.message_id, factory):
        return
    ACTIVE_TASKS[chat.id] = cmd
    try:
        await msg.reply_text(f"⚡ 𝐒𝐏𝐀𝐌 {n} 𝐓𝐔𝐑𝐁𝐎 — {len(bots)} bots.")
    except Exception:
        pass

@dot_command("spam1")
@auth_only
async def spam1(update, context): await _spam_handler(update, context, 1)

@dot_command("spam2")
@auth_only
async def spam2(update, context): await _spam_handler(update, context, 2)

@dot_command("spam3")
@auth_only
async def spam3(update, context): await _spam_handler(update, context, 3)

@dot_command("spam4")
@auth_only
async def spam4(update, context): await _spam_handler(update, context, 4)

@dot_command("spam5")
@auth_only
async def spam5(update, context): await _spam_handler(update, context, 5)

# ═══════════════════════════════════════════════════════════════════════
#   RAID COMMANDS
# ═══════════════════════════════════════════════════════════════════════

async def _raid_generic(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        key: str, templates: List[str], react: bool):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    target_user = None
    target_msg_id = None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
        target_msg_id = msg.reply_to_message.message_id
    elif context.args:
        uid = _label_to_uid(context.args[0])
        if uid:
            try:
                target_user = (await context.bot.get_chat_member(chat.id, uid)).user
                target_msg_id = msg.message_id
            except Exception:
                pass
    if not target_user:
        await msg.reply_text(
            f"❌ Reply to a user or `.settarget` a label, then `.{key} t1`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    target_name = f"@{target_user.username}" if target_user.username else target_user.first_name
    bots = all_bots()
    if not bots:
        await msg.reply_text("❌ No child bots.")
        return
    interval = get_interval(chat.id, "raid")
    stop_ref = {"stop": False}

    def factory() -> List[asyncio.Task]:
        return [
            asyncio.create_task(
                _per_bot_raid_worker(b, chat.id, target_msg_id, target_name,
                                     templates, react, stop_ref, interval)
            )
            for b in bots
        ]

    if not await claim_and_start_multi(chat.id, key, msg.message_id, factory):
        return
    ACTIVE_TASKS[chat.id] = key
    await msg.reply_text(
        f"⚡ *{key.upper()}* 𝐓𝐔𝐑𝐁𝐎 on `{len(bots)}` bots",
        parse_mode=ParseMode.MARKDOWN
    )

@dot_command("rr")
@auth_only
async def rr_cmd(update, context): await _raid_generic(update, context, "rr", RR_REPLIES, True)

@dot_command("chud")
@auth_only
async def chud_cmd(update, context): await _raid_generic(update, context, "chud", CHUD_REPLIES, False)

@dot_command("heartrr")
@auth_only
async def heartrr_cmd(update, context): await _raid_generic(update, context, "heartrr", HEARTRR, False)

@dot_command("flagrr")
@auth_only
async def flagrr_cmd(update, context): await _raid_generic(update, context, "flagrr", FLAGRR, False)

@dot_command("pille")
@auth_only
async def pille_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user.")
        return
    target_user = msg.reply_to_message.from_user
    target_msg_id = msg.reply_to_message.message_id
    bots = all_bots()
    if not bots:
        await msg.reply_text("❌ No child bots.")
        return

    def _build() -> str:
        return PILLE_TEXT.format(
            user=target_user.first_name or "user",
            emojie=random.choice(PILLE_EMOJIS)
        )

    interval = get_interval(chat.id, "raid")
    stop_ref = {"stop": False}

    def factory() -> List[asyncio.Task]:
        return [
            asyncio.create_task(
                _per_bot_send_worker(b, chat.id, _build, stop_ref, interval,
                                     reply_to=target_msg_id)
            )
            for b in bots
        ]

    if not await claim_and_start_multi(chat.id, "pille", msg.message_id, factory):
        return
    ACTIVE_TASKS[chat.id] = "pille"
    await msg.reply_text("⚡ 𝐏𝐈𝐋𝐋𝐄 𝐓𝐔𝐑𝐁𝐎 𝐒𝐓𝐀𝐑𝐓𝐄𝐃")

@dot_command("slide")
@auth_only
async def slide_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    target_user = None
    args = list(context.args)
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target_user = msg.reply_to_message.from_user
    elif args:
        uid = _label_to_uid(args[0])
        if uid:
            args.pop(0)
            target_user = type("U", (), {
                "id": uid, "username": None, "first_name": str(uid)
            })()
    if not target_user:
        await msg.reply_text("❌ Reply to a user or `.slide t1 <text>`")
        return
    if not args:
        await msg.reply_text("Usage: `.slide <text>`")
        return
    text = " ".join(args)
    if not await claim_once(chat.id, "slide", msg.message_id):
        return
    SLIDE_TRACKERS[chat.id].append({
        "uid": target_user.id,
        "text": text,
        "owner_bot_id": context.bot.id,
    })
    ACTIVE_TASKS[chat.id] = "slide"
    await msg.reply_text(
        f"⚡ Sliding `{target_user.id}` with: `{text}`",
        parse_mode=ParseMode.MARKDOWN
    )

async def slide_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not msg or not chat or not user:
        return
    if msg.text and msg.text.startswith("."):
        return
    trackers = SLIDE_TRACKERS.get(chat.id, [])
    if not trackers:
        return
    for tr in list(trackers):
        if tr["uid"] == user.id:
            if context.bot.id != tr["owner_bot_id"]:
                continue
            await safe_call(
                context.bot.send_message, chat.id, tr["text"],
                reply_to_message_id=msg.message_id,
                bot_id=context.bot.id, timeout=1.0
            )

# ═══════════════════════════════════════════════════════════════════════
#   GROUP MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════

@dot_command("lock")
@sudo_cmd(name="lock")
async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    perms = ChatPermissions(can_send_messages=False)
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].set_chat_permissions, chat.id, perms,
                            bot_id=b["id"], timeout=3.0)
            n += 1
        except Exception:
            pass
    await update.effective_message.reply_text(f"🔒 Group locked. {n} bots applied.")

@dot_command("unlock")
@sudo_cmd(name="unlock")
async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    perms = ChatPermissions(
        can_send_messages=True, can_send_media_messages=True,
        can_send_polls=True, can_send_other_messages=True,
        can_add_web_page_previews=True, can_change_info=True,
        can_invite_users=True, can_pin_messages=True
    )
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].set_chat_permissions, chat.id, perms,
                            bot_id=b["id"], timeout=3.0)
            n += 1
        except Exception:
            pass
    await update.effective_message.reply_text(f"🔓 Group unlocked. {n} bots applied.")

@dot_command("promote")
@sudo_cmd(name="promote")
async def promote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user.")
        return
    uid = msg.reply_to_message.from_user.id
    n = 0
    for b in all_bots():
        try:
            await safe_call(
                b["bot"].promote_chat_member, chat.id, uid,
                bot_id=b["id"], timeout=3.0,
                can_change_info=True, can_delete_messages=True,
                can_invite_users=True, can_restrict_members=True,
                can_pin_messages=True, can_promote_members=True,
                can_manage_video_chats=True, can_manage_chat=True
            )
            n += 1
        except Exception:
            pass
    await msg.reply_text(f"⬆️ Promoted `{uid}` using {n} bots.", parse_mode=ParseMode.MARKDOWN)

@dot_command("demote")
@sudo_cmd(name="demote")
async def demote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user.")
        return
    uid = msg.reply_to_message.from_user.id
    n = 0
    for b in all_bots():
        try:
            await safe_call(
                b["bot"].promote_chat_member, chat.id, uid,
                bot_id=b["id"], timeout=3.0,
                can_change_info=False, can_delete_messages=False,
                can_invite_users=False, can_restrict_members=False,
                can_pin_messages=False, can_promote_members=False,
                can_manage_video_chats=False, can_manage_chat=False
            )
            n += 1
        except Exception:
            pass
    await msg.reply_text(f"⬇️ Demoted `{uid}` using {n} bots.", parse_mode=ParseMode.MARKDOWN)

@dot_command("admin")
@sudo_cmd(name="admin")
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    n = 0
    for b in all_bots():
        try:
            await safe_call(
                b["bot"].promote_chat_member, chat.id, b["id"],
                bot_id=b["id"], timeout=3.0,
                can_change_info=True, can_delete_messages=True,
                can_invite_users=True, can_restrict_members=True,
                can_pin_messages=True, can_promote_members=True,
                can_manage_video_chats=True, can_manage_chat=True
            )
            n += 1
        except Exception:
            pass
    await msg.reply_text(f"👑 Admin ({n}/{len(all_bots())})")

@dot_command("mute")
@sudo_cmd(name="mute")
async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user.")
        return
    uid = msg.reply_to_message.from_user.id
    perms = ChatPermissions(can_send_messages=False)
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].restrict_chat_member, chat.id, uid, perms,
                            bot_id=b["id"], timeout=3.0)
            n += 1
        except Exception:
            pass
    await msg.reply_text(f"🔇 Muted `{uid}` ({n} bots)")

@dot_command("unmute")
@sudo_cmd(name="unmute")
async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user.")
        return
    uid = msg.reply_to_message.from_user.id
    perms = ChatPermissions(
        can_send_messages=True, can_send_media_messages=True,
        can_send_polls=True, can_send_other_messages=True,
        can_add_web_page_previews=True, can_invite_users=True
    )
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].restrict_chat_member, chat.id, uid, perms,
                            bot_id=b["id"], timeout=3.0)
            n += 1
        except Exception:
            pass
    await msg.reply_text(f"🔊 Unmuted `{uid}` ({n} bots)")

@dot_command("kick")
@sudo_cmd(name="kick")
async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user.")
        return
    uid = msg.reply_to_message.from_user.id
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].ban_chat_member, chat.id, uid,
                            bot_id=b["id"], timeout=3.0)
            await safe_call(b["bot"].unban_chat_member, chat.id, uid,
                            bot_id=b["id"], timeout=3.0)
            n += 1
        except Exception:
            pass
    await msg.reply_text(f"👢 Kicked `{uid}` ({n} bots)")

@dot_command("ban")
@sudo_cmd(name="ban")
async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user.")
        return
    uid = msg.reply_to_message.from_user.id
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].ban_chat_member, chat.id, uid,
                            bot_id=b["id"], timeout=3.0)
            n += 1
        except Exception:
            pass
    await msg.reply_text(f"🚫 Banned `{uid}` ({n} bots)")

@dot_command("unban")
@sudo_cmd(name="unban")
async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❌ Reply to a user.")
        return
    uid = msg.reply_to_message.from_user.id
    n = 0
    for b in all_bots():
        try:
            await safe_call(b["bot"].unban_chat_member, chat.id, uid,
                            bot_id=b["id"], timeout=3.0)
            n += 1
        except Exception:
            pass
    await msg.reply_text(f"✅ Unbanned `{uid}` ({n} bots)")

# ═══════════════════════════════════════════════════════════════════════
#   FUN COMMANDS
# ═══════════════════════════════════════════════════════════════════════

@dot_command("cat")
@sudo_cmd(name="cat")
async def cat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://api.thecatapi.com/v1/images/search", timeout=aiohttp.ClientTimeout(total=10)) as r:
                url = (await r.json())[0]["url"]
        await msg.reply_photo(url)
    except Exception as e:
        await msg.reply_text(f"❌ {e}")

@dot_command("dog")
@sudo_cmd(name="dog")
async def dog_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://dog.ceo/api/breeds/image/random", timeout=aiohttp.ClientTimeout(total=10)) as r:
                url = (await r.json())["message"]
        await msg.reply_photo(url)
    except Exception as e:
        await msg.reply_text(f"❌ {e}")

@dot_command("dice")
@sudo_cmd(name="dice")
async def dice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_dice(emoji="🎲")

@dot_command("quotes")
@sudo_cmd(name="quotes")
async def quotes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://zenquotes.io/api/random", timeout=aiohttp.ClientTimeout(total=10)) as r:
                q = (await r.json())[0]
        await msg.reply_text(f"💭 \"{q['q']}\"\n\n— *{q['a']}*", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.reply_text(f"❌ {e}")

@dot_command("jokes")
@sudo_cmd(name="jokes")
async def jokes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://official-joke-api.appspot.com/random_joke", timeout=aiohttp.ClientTimeout(total=10)) as r:
                d = await r.json()
        await msg.reply_text(f"😂 {d['setup']}\n\n{d['punchline']}")
    except Exception as e:
        await msg.reply_text(f"❌ {e}")

@dot_command("ai")
@sudo_cmd(name="ai")
async def ai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not context.args:
        await msg.reply_text("Usage: `.ai <prompt>`")
        return
    prompt = " ".join(context.args)
    status = await msg.reply_text("🎨 *Generating...* 0%", parse_mode=ParseMode.MARKDOWN)
    try:
        for pct in (25, 50, 75):
            await asyncio.sleep(0.4)
            try:
                await status.edit_text(f"🎨 *Generating...* {pct}%", parse_mode=ParseMode.MARKDOWN)
            except Exception:
                pass
        url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=1024&height=1024&nologo=true"
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
                data = await r.read()
        try:
            await status.delete()
        except Exception:
            pass
        await msg.reply_photo(photo=data, caption=f"🎨 *{prompt}*", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        try:
            await status.edit_text(f"❌ {e}")
        except Exception:
            pass

@dot_command("find")
@sudo_cmd(name="find")
async def find_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not context.args:
        await msg.reply_text("Usage: `.find <music>`")
        return
    q = " ".join(context.args)
    try:
        url = f"https://itunes.apple.com/search?term={quote(q)}&media=music&limit=3"
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
        results = data.get("results", [])
        if results:
            lines = [f"🎵 *{q}*", ""]
            for r0 in results[:3]:
                lines.append(
                    f"• *{r0.get('trackName', '?')}* — {r0.get('artistName', '?')}\n"
                    f"  {r0.get('trackViewUrl', '')}"
                )
            txt = "\n".join(lines)
        else:
            txt = f"🎵 Found: `{q}`"
        await msg.reply_text(txt, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    except Exception as e:
        await msg.reply_text(f"❌ {e}")

@dot_command("play")
@sudo_cmd(name="play")
async def play_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not context.args:
        await msg.reply_text("Usage: `.play <song>`")
        return
    await msg.reply_text(
        f"🎵 *Searching:* {' '.join(context.args)}\n\n"
        f"⚠️ Voice chat streaming requires PyTgCalls installed.",
        parse_mode=ParseMode.MARKDOWN
    )

# ═══════════════════════════════════════════════════════════════════════
#   PFP COMMANDS
# ═══════════════════════════════════════════════════════════════════════

@dot_command("savepfp")
@sudo_cmd(name="savepfp")
async def savepfp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat:
        return
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        await msg.reply_text("❌ Reply to a photo with `.savepfp`")
        return
    PFP_IMAGES[chat.id].append(msg.reply_to_message.photo[-1].file_id)
    save_pfp()
    await msg.reply_text(f"✅ Saved pfp #{len(PFP_IMAGES[chat.id])}")

@dot_command("allpfp")
@sudo_cmd(name="allpfp")
async def allpfp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat:
        return
    imgs = PFP_IMAGES.get(chat.id, [])
    if not imgs:
        await msg.reply_text("❌ No pfps saved.")
        return
    img = imgs[0]
    coros = [
        safe_call(b["bot"].set_chat_photo, chat.id, photo=img,
                  bot_id=b["id"], timeout=2.0)
        for b in all_bots()
    ]
    results = await asyncio.gather(*coros, return_exceptions=True)
    n = sum(1 for r in results if r is not None and not isinstance(r, Exception))
    await msg.reply_text(f"✅ Set pfp on {n}/{len(all_bots())} bots")

@dot_command("pfplock")
@sudo_cmd(name="pfplock")
async def pfplock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat:
        return
    PFP_LOOP_STATE[chat.id] = False
    save_pfp()
    n = _cancel_named(chat.id, "pfploop")
    await msg.reply_text(f"🔒 PFP locked ({n} tasks).")

@dot_command("pfploop")
@sudo_cmd(name="pfploop")
async def pfploop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat:
        return
    imgs = PFP_IMAGES.get(chat.id, [])
    if not imgs:
        await msg.reply_text("❌ No pfps saved. Use `.savepfp`.")
        return
    bots = all_bots()
    if not bots:
        await msg.reply_text("❌ No child bots.")
        return
    PFP_LOOP_STATE[chat.id] = True
    save_pfp()
    interval = get_interval(chat.id, "pfp")
    stop_ref = {"stop": False}

    def factory() -> List[asyncio.Task]:
        return [
            asyncio.create_task(
                _per_bot_pfp_worker(b, chat.id, imgs, stop_ref, interval)
            )
            for b in bots
        ]

    if not await claim_and_start_multi(chat.id, "pfploop", msg.message_id, factory):
        return
    await msg.reply_text(f"⚡ PFP TURBO LOOP started (interval {interval}s).")

@dot_command("deletepfp")
@sudo_cmd(name="deletepfp")
async def deletepfp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    if not chat:
        return
    PFP_IMAGES[chat.id] = []
    PFP_LOOP_STATE[chat.id] = False
    save_pfp()
    await msg.reply_text("🗑️ All saved pfps deleted.")

# ═══════════════════════════════════════════════════════════════════════
#   CALLBACK ROUTER — bulletproof
# ═══════════════════════════════════════════════════════════════════════

async def _cb_show_bots_list(q, context):
    """Shared logic for showing bots list with inline remove buttons."""
    bots = all_bots()
    lines = [f"🤖 *𝐀𝐋𝐋 𝐁𝐎𝐓𝐒* ({len(bots)})", ""]
    kb_rows = []
    if bots:
        for i, b in enumerate(bots, 1):
            lines.append(f"{i}. @{b['username']} (`{b['id']}`)")
            kb_rows.append([
                InlineKeyboardButton(
                    f"🗑️ Remove @{b['username']}",
                    callback_data=f"delbot_{b['username']}"
                )
            ])
    else:
        lines.append("❌ No child bots.")
    kb_rows.append([InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_botsettings")])
    await safe_edit(q, "\n".join(lines),
                    reply_markup=InlineKeyboardMarkup(kb_rows),
                    parse_mode=ParseMode.MARKDOWN)

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = getattr(update, "callback_query", None)
    if not q:
        return

    answered = [False]

    async def ans(text=None, alert=False):
        if answered[0]:
            return
        try:
            await q.answer(text=text, show_alert=alert)
        except Exception:
            pass
        answered[0] = True

    try:
        user = getattr(update, "effective_user", None)
        if not user or not is_authorized(user.id):
            await ans("🚫 Unauthorized", alert=True)
            return

        data = getattr(q, "data", None) or ""
        await _process_callback(q, data, update, context, ans)

    except Exception as e:
        log.exception(f"callback_router failed: data={getattr(q, 'data', '?')} error={type(e).__name__}: {e}")
        await ans(f"❌ {type(e).__name__}: {str(e)[:100]}", alert=True)
    finally:
        await ans()

async def _process_callback(q, data: str, update: Update, context: ContextTypes.DEFAULT_TYPE, ans):
    # ═══════════ MAIN MENU ═══════════
    if data == "menu_main":
        await safe_edit(q, CFG["start_text"], reply_markup=main_menu_kb())
        return

    # ═══════════ ADD BOT ═══════════
    if data == "menu_addbot":
        await safe_edit(q,
            "📥 *𝐀𝐃𝐃 𝐓𝐎𝐊𝐄𝐍 / 𝐁𝐎𝐓*\n\n"
            "Send the bot token as a message.\n"
            "Format: `.add <TOKEN>` — or bulk: `.add <TOKEN1>,<TOKEN2>,<TOKEN3>`\n\n"
            "Example:\n`.add 123456:ABCDEF...`\n\n"
            "You can add *unlimited* bots.",
            reply_markup=back_button(), parse_mode=ParseMode.MARKDOWN)
        return

    # ═══════════ LUFFY NC ═══════════
    if data == "menu_luffy":
        kb = [
            [InlineKeyboardButton(f".luffync{i}", callback_data=f"cmd_luffync_{i}")
             for i in range(j, min(j+5, 11))]
            for j in (1, 6)
        ]
        kb.append([InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")])
        await safe_edit(q,
            "🏴‍☠️ *𝐋𝐔𝐅𝐅𝐘 𝐍𝐂 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒*\n\n"
            "Usage: `.luffync<1-10> <text>`\n"
            "Example: `.luffync1 gali de`",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        return

    # ═══════════ VEGETA NC ═══════════
    if data == "menu_vegeta":
        kb = [
            [InlineKeyboardButton(f".vegetanc{i}", callback_data=f"cmd_vegetanc_{i}")
             for i in range(j, min(j+5, 11))]
            for j in (1, 6)
        ]
        kb.append([InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")])
        await safe_edit(q,
            "👑 *𝐕𝐄𝐆𝐄𝐓𝐀 𝐍𝐂 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒*\n\n"
            "Usage: `.vegetanc<1-10> <text>`",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        return

    # ═══════════ SPAM ═══════════
    if data == "menu_spam":
        kb = [
            [InlineKeyboardButton(f".spam{i}", callback_data=f"cmd_spam_{i}")
             for i in range(j, min(j+3, 6))]
            for j in (1, 4)
        ]
        kb.append([InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")])
        await safe_edit(q,
            "💥 *𝐒𝐏𝐀𝐌 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒*\n\n"
            "Usage: `.spam<1-5> <text>`",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        return

    # ═══════════ RAID ═══════════
    if data == "menu_raid":
        kb = [
            [InlineKeyboardButton(".rr", callback_data="menu_raid_rr"),
             InlineKeyboardButton(".chud", callback_data="menu_raid_chud")],
            [InlineKeyboardButton(".heartrr", callback_data="menu_raid_heart"),
             InlineKeyboardButton(".flagrr", callback_data="menu_raid_flag")],
            [InlineKeyboardButton(".pille", callback_data="menu_raid_pille"),
             InlineKeyboardButton(".slide", callback_data="menu_raid_slide")],
            [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")],
        ]
        await safe_edit(q,
            "🔥 *𝐑𝐀𝐈𝐃 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒*\n\n"
            "Reply to a user with the command.",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        return

    if data.startswith("menu_raid_"):
        key = data.replace("menu_raid_", "")
        mp = {
            "rr": ".rr", "chud": ".chud", "heart": ".heartrr",
            "flag": ".flagrr", "pille": ".pille", "slide": ".slide <text>",
        }
        cmd = mp.get(key, f".{key}")
        await safe_edit(q,
            f"🔥 *{cmd}*\n\nReply to a user with `{cmd.split()[0]}`.",
            reply_markup=back_button("menu_raid"), parse_mode=ParseMode.MARKDOWN)
        return

    # ═══════════ BOT SETTINGS ═══════════
    if data == "menu_botsettings":
        kb = [
            [InlineKeyboardButton("📊 𝗕𝗢𝗧 𝗦𝗧𝗔𝗧𝗨𝗦", callback_data="bs_status")],
            [InlineKeyboardButton("🤖 𝗔𝗟𝗟 𝗕𝗢𝗧𝗦", callback_data="bs_bots")],
            [InlineKeyboardButton("⏱️ 𝗗𝗘𝗟𝗔𝗬 𝗣𝗘𝗥 𝗕𝗢𝗧", callback_data="bs_delay")],
            [InlineKeyboardButton("🏓 𝗣𝗜𝗡𝗚", callback_data="bs_ping")],
            [InlineKeyboardButton("🔄 𝗥𝗘𝗙𝗥𝗘𝗦𝗛 𝗟𝗔𝗧𝗘𝗡𝗖𝗬", callback_data="bs_refresh")],
            [InlineKeyboardButton("🧠 𝗣𝗥𝗢𝗖𝗘𝗦𝗦𝗢𝗥", callback_data="bs_proc")],
            [InlineKeyboardButton("💻 𝗖𝗣𝗨", callback_data="bs_cpu")],
            [InlineKeyboardButton("📈 𝗣𝗘𝗥𝗙𝗢𝗥𝗠𝗔𝗡𝗖𝗘", callback_data="bs_perf")],
            [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")],
        ]
        await safe_edit(q, "⚙️ *𝐁𝐎𝐓 𝐒𝐄𝐓𝐓𝐈𝐍𝐆𝐒*",
                        reply_markup=InlineKeyboardMarkup(kb),
                        parse_mode=ParseMode.MARKDOWN)
        return

    if data == "bs_status":
        lines = ["🟢 *𝐁𝐎𝐓 𝐒𝐓𝐀𝐓𝐔𝐒*", ""]
        for b in all_bots():
            st = get_guard(b["id"]).stats()
            cd = max(0, _bot_cooldown.get(b["id"], 0) - time.monotonic())
            cd_str = f" | cool {cd:.1f}s" if cd > 0 else ""
            lines.append(f"• @{b['username']} — ok={st['successes']} fail={st['failures']}{cd_str}")
        if not all_bots():
            lines.append("❌ No child bots.")
        await safe_edit(q, "\n".join(lines),
                        reply_markup=back_button("menu_botsettings"),
                        parse_mode=ParseMode.MARKDOWN)
        return

    if data == "bs_bots":
        await _cb_show_bots_list(q, context)
        return

    if data.startswith("delbot_"):
        if update.effective_user.id != OWNER_ID:
            await ans("🚫 Only owner can remove bots", alert=True)
            return
        username = data[len("delbot_"):]
        uname = await CHILD_MGR.stop_and_remove(username)
        if uname:
            await ans(f"✅ Removed @{uname}", alert=True)
        else:
            await ans(f"❌ Not found: @{username}", alert=True)
        await _cb_show_bots_list(q, context)
        return

    if data == "bs_delay":
        lines = ["⏱️ *𝐃𝐄𝐋𝐀𝐘 𝐏𝐄𝐑 𝐁𝐎𝐓*", ""]
        for b in all_bots():
            lines.append(f"• @{b['username']}: {get_guard(b['id']).delay:.2f}s")
        if not all_bots():
            lines.append("❌ No bots.")
        await safe_edit(q, "\n".join(lines),
                        reply_markup=back_button("menu_botsettings"),
                        parse_mode=ParseMode.MARKDOWN)
        return

    if data == "bs_ping":
        t0 = time.time()
        await safe_edit(q, "🏓 Pinging...", reply_markup=back_button("menu_botsettings"))
        ms = (time.time() - t0) * 1000
        await safe_edit(q, f"🏓 *𝐏𝐈𝐍𝐆:* `{ms:.2f} ms`",
                        reply_markup=back_button("menu_botsettings"),
                        parse_mode=ParseMode.MARKDOWN)
        return

    if data == "bs_refresh":
        for b in all_bots():
            try:
                await b["bot"].get_me()
            except Exception:
                pass
        await safe_edit(q, "🔄 Refreshed.", reply_markup=back_button("menu_botsettings"))
        return

    if data == "bs_proc":
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        await safe_edit(q,
            f"🧠 *𝐏𝐑𝐎𝐂𝐄𝐒𝐒𝐎𝐑*\n\n"
            f"• Cores: `{psutil.cpu_count()}`\n"
            f"• Usage: `{cpu:.1f}%`\n"
            f"• RAM: `{mem.percent:.1f}%` "
            f"({mem.used//1024//1024}MB / {mem.total//1024//1024}MB)",
            reply_markup=back_button("menu_botsettings"),
            parse_mode=ParseMode.MARKDOWN)
        return

    if data == "bs_cpu":
        cpu = psutil.cpu_percent(interval=None, percpu=True)
        txt = "💻 *𝐂𝐏𝐔*\n\n" + "\n".join(
            f"• Core {i+1}: `{c:.1f}%`" for i, c in enumerate(cpu)
        )
        await safe_edit(q, txt, reply_markup=back_button("menu_botsettings"),
                        parse_mode=ParseMode.MARKDOWN)
        return

    if data == "bs_perf":
        ts = tf = 0
        for b in all_bots():
            s = get_guard(b["id"]).stats()
            ts += s["successes"]
            tf += s["failures"]
        pct = (ts / (ts + tf) * 100) if (ts + tf) else 100.0
        await safe_edit(q,
            f"📈 *𝐏𝐄𝐑𝐅𝐎𝐑𝐌𝐀𝐍𝐂𝐄*\n\n"
            f"• Successes: `{ts}`\n"
            f"• Failures: `{tf}`\n"
            f"• Rate: `{pct:.1f}%`",
            reply_markup=back_button("menu_botsettings"),
            parse_mode=ParseMode.MARKDOWN)
        return

    # ═══════════ TARGETS ═══════════
    if data == "menu_targets":
        kb = [
            [InlineKeyboardButton("🎯 𝗦𝗘𝗧 𝗧𝗔𝗥𝗚𝗘𝗧", callback_data="tg_set")],
            [InlineKeyboardButton("🗑️ 𝗗𝗘𝗟𝗘𝗧𝗘 𝗧𝗔𝗥𝗚𝗘𝗧", callback_data="tg_del")],
            [InlineKeyboardButton("📋 𝗟𝗜𝗦𝗧 𝗧𝗔𝗥𝗚𝗘𝗧𝗦", callback_data="tg_list")],
            [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")],
        ]
        await safe_edit(q,
            "🎯 *𝐓𝐀𝐑𝐆𝐄𝐓𝐒*\n\n"
            "Set target users with labels (t1, t2...)\n"
            "Use as `.luffync1 t1`.",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN)
        return

    if data == "tg_set":
        await safe_edit(q, "🎯 Reply to a user with `.settarget <label>`.",
                        reply_markup=back_button("menu_targets"))
        return

    if data == "tg_del":
        await safe_edit(q, "🗑️ Reply to a user with `.deltarget`.",
                        reply_markup=back_button("menu_targets"))
        return

    if data == "tg_list":
        if not TARGETS:
            txt = "❌ No targets."
        else:
            txt = "📋 *𝐓𝐀𝐑𝐆𝐄𝐓𝐒*\n\n" + "\n".join(
                f"• `{lbl}` → `{uid}`" for uid, lbl in TARGETS.items()
            )
        await safe_edit(q, txt, reply_markup=back_button("menu_targets"),
                        parse_mode=ParseMode.MARKDOWN)
        return

    # ═══════════ PFP ═══════════
    if data == "menu_pfp":
        kb = [
            [InlineKeyboardButton(".pfplock", callback_data="pfplock")],
            [InlineKeyboardButton(".pfploop", callback_data="pfploop")],
            [InlineKeyboardButton(".savepfp", callback_data="savepfp")],
            [InlineKeyboardButton(".allpfp", callback_data="allpfp")],
            [InlineKeyboardButton(".deletepfp", callback_data="deletepfp")],
            [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")],
        ]
        await safe_edit(q,
            "🖼️ *𝐏𝐅𝐏 𝐋𝐎𝐎𝐏*\n\n"
            "• `.pfplock` — stop\n"
            "• `.pfploop` — turbo loop\n"
            "• `.savepfp` — save image\n"
            "• `.allpfp` — set once\n"
            "• `.deletepfp` — clear",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN)
        return

    if data == "pfplock":
        cid = q.message.chat.id if q.message else q.from_user.id
        PFP_LOOP_STATE[cid] = False
        save_pfp()
        n = _cancel_named(cid, "pfploop")
        await ans(f"🔒 Locked ({n} tasks).", alert=True)
        return

    if data == "pfploop":
        cid = q.message.chat.id if q.message else q.from_user.id
        if not PFP_IMAGES.get(cid):
            await ans("❌ No pfps. Use .savepfp.", alert=True)
            return
        PFP_LOOP_STATE[cid] = True
        save_pfp()
        interval = get_interval(cid, "pfp")
        stop_ref = {"stop": False}
        _cancel_named(cid, "pfploop")
        tasks = [
            asyncio.create_task(_per_bot_pfp_worker(b, cid, PFP_IMAGES[cid], stop_ref, interval))
            for b in all_bots()
        ]
        for t in tasks:
            _track(cid, "pfploop", t)
        await ans(f"⚡ Loop started (interval {interval}s).", alert=True)
        return

    if data == "savepfp":
        await safe_edit(q, "📸 Reply to a *photo* with `.savepfp`.",
                        reply_markup=back_button("menu_pfp"),
                        parse_mode=ParseMode.MARKDOWN)
        return

    if data == "allpfp":
        cid = q.message.chat.id if q.message else q.from_user.id
        if not PFP_IMAGES.get(cid):
            await ans("❌ No pfps.", alert=True)
            return
        img = PFP_IMAGES[cid][0]
        coros = [
            safe_call(b["bot"].set_chat_photo, cid, photo=img,
                      bot_id=b["id"], timeout=2.0)
            for b in all_bots()
        ]
        await asyncio.gather(*coros, return_exceptions=True)
        await ans("✅ Done.", alert=True)
        return

    if data == "deletepfp":
        cid = q.message.chat.id if q.message else q.from_user.id
        PFP_IMAGES[cid] = []
        PFP_LOOP_STATE[cid] = False
        save_pfp()
        await ans("🗑️ Deleted.", alert=True)
        return

    # ═══════════ FUN ═══════════
    if data == "menu_fun":
        kb = [
            [InlineKeyboardButton(".play", callback_data="cmd_play"),
             InlineKeyboardButton(".ai", callback_data="cmd_ai")],
            [InlineKeyboardButton(".cat", callback_data="cmd_cat"),
             InlineKeyboardButton(".dog", callback_data="cmd_dog")],
            [InlineKeyboardButton(".dice", callback_data="cmd_dice"),
             InlineKeyboardButton(".quotes", callback_data="cmd_quotes")],
            [InlineKeyboardButton(".jokes", callback_data="cmd_jokes"),
             InlineKeyboardButton(".find", callback_data="cmd_find")],
            [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")],
        ]
        await safe_edit(q,
            "🎮 *𝐅𝐔𝐍 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒*\n\n"
            "• `.play <song>` — play music\n"
            "• `.ai <prompt>` — generate image\n"
            "• `.cat` — random cat\n"
            "• `.dog` — random dog\n"
            "• `.dice` — roll dice\n"
            "• `.quotes` — quote\n"
            "• `.jokes` — joke\n"
            "• `.find <music>` — find",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN)
        return

    if data == "cmd_cat":
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://api.thecatapi.com/v1/images/search",
                                 timeout=aiohttp.ClientTimeout(total=10)) as r:
                    url = (await r.json())[0]["url"]
            await q.bot.send_photo(q.message.chat.id, url)
            await ans("🐱")
        except Exception as e:
            await ans(f"❌ {e}", alert=True)
        return

    if data == "cmd_dog":
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://dog.ceo/api/breeds/image/random",
                                 timeout=aiohttp.ClientTimeout(total=10)) as r:
                    url = (await r.json())["message"]
            await q.bot.send_photo(q.message.chat.id, url)
            await ans("🐶")
        except Exception as e:
            await ans(f"❌ {e}", alert=True)
        return

    if data == "cmd_dice":
        try:
            await q.bot.send_dice(chat_id=q.message.chat.id, emoji="🎲")
            await ans("🎲")
        except Exception as e:
            await ans(f"❌ {e}", alert=True)
        return

    if data == "cmd_quotes":
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://zenquotes.io/api/random",
                                 timeout=aiohttp.ClientTimeout(total=10)) as r:
                    qq = (await r.json())[0]
            await q.bot.send_message(
                q.message.chat.id,
                f"💭 \"{qq['q']}\"\n\n— *{qq['a']}*",
                parse_mode=ParseMode.MARKDOWN
            )
            await ans("💭")
        except Exception as e:
            await ans(f"❌ {e}", alert=True)
        return

    if data == "cmd_jokes":
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://official-joke-api.appspot.com/random_joke",
                                 timeout=aiohttp.ClientTimeout(total=10)) as r:
                    d = await r.json()
            await q.bot.send_message(q.message.chat.id, f"😂 {d['setup']}\n\n{d['punchline']}")
            await ans("😂")
        except Exception as e:
            await ans(f"❌ {e}", alert=True)
        return

    if data in ("cmd_play", "cmd_ai", "cmd_find"):
        cm = {
            "cmd_play": ".play <song>",
            "cmd_ai": ".ai <prompt>",
            "cmd_find": ".find <music>",
        }
        await safe_edit(q, f"🎮 *{cm[data]}*\n\nType `{cm[data]}` in chat.",
                        reply_markup=back_button("menu_fun"),
                        parse_mode=ParseMode.MARKDOWN)
        return

    # ═══════════ GROUP SETTINGS ═══════════
    if data == "menu_group":
        kb = [
            [InlineKeyboardButton(".lock", callback_data="gc_lock"),
             InlineKeyboardButton(".unlock", callback_data="gc_unlock")],
            [InlineKeyboardButton(".promote", callback_data="gc_promote"),
             InlineKeyboardButton(".demote", callback_data="gc_demote")],
            [InlineKeyboardButton(".admin", callback_data="gc_admin"),
             InlineKeyboardButton(".mute", callback_data="gc_mute")],
            [InlineKeyboardButton(".unmute", callback_data="gc_unmute"),
             InlineKeyboardButton(".kick", callback_data="gc_kick")],
            [InlineKeyboardButton(".ban", callback_data="gc_ban"),
             InlineKeyboardButton(".unban", callback_data="gc_unban")],
            [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")],
        ]
        await safe_edit(q,
            "🛡️ *𝐆𝐑𝐎𝐔𝐏 𝐒𝐄𝐓𝐓𝐈𝐍𝐆𝐒*\n\n"
            "All commands work 100%.",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN)
        return

    if data == "gc_lock":
        chat = q.message.chat
        if chat.type not in ("group", "supergroup"):
            await ans("❌ Use in group.", alert=True)
            return
        perms = ChatPermissions(can_send_messages=False)
        n = 0
        for b in all_bots():
            try:
                await b["bot"].set_chat_permissions(chat.id, perms)
                n += 1
            except Exception:
                pass
        await ans(f"🔒 Locked ({n} bots).", alert=True)
        return

    if data == "gc_unlock":
        chat = q.message.chat
        if chat.type not in ("group", "supergroup"):
            await ans("❌ Use in group.", alert=True)
            return
        perms = ChatPermissions(
            can_send_messages=True, can_send_media_messages=True,
            can_send_polls=True, can_send_other_messages=True,
            can_add_web_page_previews=True, can_change_info=True,
            can_invite_users=True, can_pin_messages=True
        )
        n = 0
        for b in all_bots():
            try:
                await b["bot"].set_chat_permissions(chat.id, perms)
                n += 1
            except Exception:
                pass
        await ans(f"🔓 Unlocked ({n} bots).", alert=True)
        return

    if data == "gc_admin":
        chat = q.message.chat
        if chat.type not in ("group", "supergroup"):
            await ans("❌ Use in group.", alert=True)
            return
        n = 0
        for b in all_bots():
            try:
                await b["bot"].promote_chat_member(
                    chat.id, b["id"],
                    can_change_info=True, can_delete_messages=True,
                    can_invite_users=True, can_restrict_members=True,
                    can_pin_messages=True, can_promote_members=True,
                    can_manage_video_chats=True, can_manage_chat=True
                )
                n += 1
            except Exception:
                pass
        await ans(f"👑 Promoted {n}/{len(all_bots())} bots.", alert=True)
        return

    if data in ("gc_promote", "gc_demote", "gc_mute", "gc_unmute",
                "gc_kick", "gc_ban", "gc_unban"):
        mp = {
            "gc_promote": ".promote",
            "gc_demote": ".demote",
            "gc_mute": ".mute",
            "gc_unmute": ".unmute",
            "gc_kick": ".kick",
            "gc_ban": ".ban",
            "gc_unban": ".unban",
        }
        cmd = mp[data]
        await safe_edit(q, f"🛡️ *{cmd}*\n\nReply to a user with `{cmd}`.",
                        reply_markup=back_button("menu_group"),
                        parse_mode=ParseMode.MARKDOWN)
        return

    # ═══════════ STOP ═══════════
    if data == "menu_stop":
        await safe_edit(q,
            "🛑 *𝐒𝐓𝐎𝐏 𝐓𝐀𝐒𝐊*\n\n"
            "• `.s <command_name>` — stop specific task\n"
            "• `.sall` — stop ALL tasks instantly ⚡",
            reply_markup=back_button(),
            parse_mode=ParseMode.MARKDOWN)
        return

    # ═══════════ SPEED ═══════════
    if data == "menu_speed":
        cid = q.message.chat.id if q.message else q.from_user.id
        cur = CHAT_INTERVALS.get(cid, {})
        lines = ["⚡ *𝐒𝐏𝐄𝐄𝐃 𝐂𝐎𝐍𝐓𝐑𝐎𝐋*", ""]
        for k, v in DEFAULT_INTERVALS.items():
            lines.append(f"• `{k}` = {cur.get(k, v)}s")
        lines.append("\n`.speed <cat> <seconds>` — e.g. `.speed all 0.01`")
        await safe_edit(q, "\n".join(lines),
                        reply_markup=back_button("menu_main"),
                        parse_mode=ParseMode.MARKDOWN)
        return

    # ═══════════ EDITS ═══════════
    if data == "menu_edits":
        kb = [
            [InlineKeyboardButton("🖼️ 𝐄𝐃𝐈𝐓 𝐒𝐓𝐀𝐑𝐓 𝐌𝐄𝐍𝐔 𝐌𝐄𝐃𝐈𝐀", callback_data="ed_startmedia")],
            [InlineKeyboardButton("📝 𝐄𝐃𝐈𝐓 𝐒𝐓𝐀𝐑𝐓 𝐓𝐄𝐗𝐓", callback_data="ed_starttext")],
            [InlineKeyboardButton("🔄 𝐑𝐄𝐒𝐄𝐓 𝐓𝐎 𝐃𝐄𝐅𝐀𝐔𝐋𝐓", callback_data="ed_resetstart")],
            [InlineKeyboardButton("🎬 𝐄𝐃𝐈𝐓 𝐆𝐀𝐌𝐄 𝐎𝐕𝐄𝐑 𝐌𝐄𝐃𝐈𝐀", callback_data="ed_gomedia")],
            [InlineKeyboardButton("➕ 𝐀𝐃𝐃 𝐒𝐔𝐃𝐎", callback_data="ed_addsudo")],
            [InlineKeyboardButton("⬅️ 𝗕𝗔𝗖𝗞", callback_data="menu_main")],
        ]
        await safe_edit(q,
            "✏️ *𝐄𝐃𝐈𝐓𝐒*\n\n"
            "Configure start text, media, sudo.",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN)
        return

    if data == "ed_startmedia":
        await safe_edit(q, "🖼️ Send a photo/video with caption `.setstartmedia`.",
                        reply_markup=back_button("menu_edits"))
        return

    if data == "ed_starttext":
        cur = CFG["start_text"][:200] + ("..." if len(CFG["start_text"]) > 200 else "")
        await safe_edit(q,
            f"📝 *CURRENT START TEXT:*\n\n{cur}\n\n"
            f"Use `.setstarttext <new text>` to update.",
            reply_markup=back_button("menu_edits"),
            parse_mode=ParseMode.MARKDOWN)
        return

    if data == "ed_resetstart":
        CFG["start_text"] = DEFAULT_MENU_HEADER
        CFG["start_media_type"] = None
        CFG["start_media_file_id"] = None
        save_config()
        await ans("✅ Reset to default branding.", alert=True)
        return

    if data == "ed_gomedia":
        await safe_edit(q, "🎬 Send a photo/video with caption `.setgomedia`.",
                        reply_markup=back_button("menu_edits"))
        return

    if data == "ed_addsudo":
        await safe_edit(q, "➕ Reply to a user with `.ok`.",
                        reply_markup=back_button("menu_edits"))
        return

    # ═══════════ NC/SPAM BUTTONS ═══════════
    if data.startswith("cmd_luffync_"):
        n = data.rsplit("_", 1)[-1]
        await safe_edit(q, f"🇱 🇺 🇫 🇫 🇾  ɴᴄ {n}\n\nUsage: `.luffync{n} <text>`",
                        reply_markup=back_button("menu_luffy"))
        return

    if data.startswith("cmd_vegetanc_"):
        n = data.rsplit("_", 1)[-1]
        await safe_edit(q, f"🇻 🇪 🇬 🇪 🇹 🇦  ɴᴄ {n}\n\nUsage: `.vegetanc{n} <text>`",
                        reply_markup=back_button("menu_vegeta"))
        return

    if data.startswith("cmd_spam_"):
        n = data.rsplit("_", 1)[-1]
        await safe_edit(q, f"💥 𝐒𝐏𝐀𝐌 {n}\n\nUsage: `.spam{n} <text>`",
                        reply_markup=back_button("menu_spam"))
        return

    # ═══════════ UNKNOWN ═══════════
    await ans("⚠️ Unknown action", alert=True)

# ═══════════════════════════════════════════════════════════════════════
#   HANDLER REGISTRATION
# ═══════════════════════════════════════════════════════════════════════

def register_master_handlers(app: Application):
    try:
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, dot_dispatcher)
        )
        log.info("  ✅ Registered dot_dispatcher (master)")
    except Exception as e:
        log.exception(f"  ❌ master dispatcher failed: {e}")
    try:
        app.add_handler(CallbackQueryHandler(callback_router))
        log.info("  ✅ Registered callback_router")
    except Exception as e:
        log.exception(f"  ❌ master callback failed: {e}")

def register_child_handlers(app: Application):
    try:
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, dot_dispatcher)
        )
    except Exception as e:
        log.exception(f"  ❌ child dispatcher failed: {e}")
    try:
        app.add_handler(CallbackQueryHandler(callback_router))
    except Exception as e:
        log.exception(f"  ❌ child callback failed: {e}")
    try:
        app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & GROUP_FILTER,
                slide_message_handler
            ),
            group=99
        )
    except Exception as e:
        log.exception(f"  ❌ child slide handler failed: {e}")

# ═══════════════════════════════════════════════════════════════════════
#   MAIN
# ═══════════════════════════════════════════════════════════════════════

async def _post_init_master(app: Application):
    try:
        me = await app.bot.get_me()
        log.info(f"✅ Master @{me.username} online")
    except Exception as e:
        log.error(f"Master post_init error: {e}")

async def main_async():
    log.info("═" * 60)
    log.info(">>> Step 1/6: Building master application...")
    master = ApplicationBuilder().token(BOT_TOKEN).post_init(_post_init_master).build()
    log.info("    ✅ Built")

    log.info(">>> Step 2/6: Registering handlers...")
    register_master_handlers(master)
    log.info(f"    ✅ {len(DOT_COMMANDS)} dot commands registered")

    log.info(">>> Step 3/6: Initializing (Telegram getMe)...")
    await master.initialize()
    log.info("    ✅ Initialized")

    if master.post_init:
        try:
            await master.post_init(master)
        except Exception as e:
            log.warning(f"⚠️  post_init: {e}")

    log.info(">>> Step 4/6: Starting application...")
    await master.start()
    log.info("    ✅ Started")

    log.info(">>> Step 5/6: Starting polling...")
    await master.updater.start_polling(
        allowed_updates=Update.ALL_TYPES, drop_pending_updates=True
    )
    log.info("    ✅ Polling started")

    log.info(">>> Step 6/6: Loading child bots from disk...")
    await CHILD_MGR.start_all_from_disk()
    log.info(f"    ✅ {len(all_bots())} child bots loaded")

    log.info("═" * 60)
    try:
        me = await master.bot.get_me()
        log.info(f"🏴‍☠️  BOT ONLINE: @{me.username}")
    except Exception:
        pass
    log.info(f"📊 Child bots: {len(all_bots())} | Sudo: {len(SUDO_USERS)} | Owner: {OWNER_ID}")
    log.info(f"🎯 Dot commands: {len(DOT_COMMANDS)}")
    log.info("═" * 60)
    log.info("🚀 Listening for updates... (Ctrl+C to stop)")

    stop_event = asyncio.Event()

    def _sig_handler(signum, frame):
        log.info(f"📴 Signal {signum} received")
        stop_event.set()

    try:
        signal.signal(signal.SIGTERM, _sig_handler)
        signal.signal(signal.SIGINT, _sig_handler)
    except (ValueError, AttributeError):
        pass

    try:
        await stop_event.wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        log.info("🛑 Shutting down...")
        try:
            await CHILD_MGR.stop_all()
        except Exception as e:
            log.error(f"  stop_all: {e}")
        try:
            await master.updater.stop()
        except Exception as e:
            log.error(f"  updater.stop: {e}")
        try:
            await master.stop()
        except Exception as e:
            log.error(f"  app.stop: {e}")
        try:
            await master.shutdown()
        except Exception as e:
            log.error(f"  app.shutdown: {e}")
        log.info("✅ Shutdown complete")

def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN is empty. Set: export BOT_TOKEN='123:ABC...'")
        sys.exit(1)
    if BOT_TOKEN == "YOUR_MAIN_BOT_TOKEN_HERE":
        print("❌ BOT_TOKEN is placeholder.")
        sys.exit(1)
    if ":" not in BOT_TOKEN:
        print(f"❌ BOT_TOKEN format invalid (missing ':'): {BOT_TOKEN[:30]}...")
        sys.exit(1)
    if len(BOT_TOKEN) < 40:
        print(f"❌ BOT_TOKEN too short ({len(BOT_TOKEN)} chars)")
        sys.exit(1)
    if not OWNER_ID or OWNER_ID == 0:
        print(f"❌ OWNER_ID not set or is 0. Current: '{OWNER_ID_RAW}'")
        sys.exit(1)

    import telegram
    print("═" * 60)
    print(f"  🏴‍☠️  LUFFY CREW v6.0")
    print(f"  Python:   {sys.version.split()[0]}")
    print(f"  PTB:      {telegram.__version__}")
    print(f"  Owner ID: {OWNER_ID}")
    print(f"  Bot ID:   {BOT_TOKEN.split(':')[0]}")
    print("═" * 60)

    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted.")
    except SystemExit:
        raise
    except Exception as e:
        print()
        print("=" * 60)
        print(f"💥 FATAL ERROR: {type(e).__name__}")
        print("=" * 60)
        print(f"{e}")
        print()
        print("Full traceback:")
        print("-" * 60)
        traceback.print_exc()
        print("-" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
