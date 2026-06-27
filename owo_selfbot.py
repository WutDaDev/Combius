#!/usr/bin/env python3
"""
OWO MULTI-TOKEN SELFBOT v3.0
- All config from .env
- Railway/GitHub safe
- Multi-token, multi-channel, gems, inventory, sellall, captcha
"""

import os
import sys
import json
import random
import time
import threading
import requests
from datetime import datetime
from pathlib import Path

# ====== LOAD .ENV ======
try:
    from dotenv import load_dotenv
    # Check if running on Railway (they inject env vars natively)
    if not os.environ.get('RAILWAY_PROJECT_ID'):
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print("[+] Loaded .env file")
        else:
            print("[!] No .env file found. Using system environment variables.")
except ImportError:
    print("[!] python-dotenv not installed. Install with: pip install python-dotenv")
    print("[!] Make sure env vars are set in your environment.")

# ====== CONFIG FROM ENV ======
def env_bool(key, default=False):
    val = os.environ.get(key, str(default)).strip().lower()
    return val in ('true', '1', 'yes', 'on')

def env_int(key, default=0):
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default

def env_float(key, default=0.0):
    try:
        return float(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default

def env_list(key, default=""):
    val = os.environ.get(key, default)
    if not val:
        return []
    return [x.strip() for x in val.split(',') if x.strip()]

# Read all config from environment
DISCORD_TOKENS = env_list('DISCORD_TOKENS')
CHANNEL_IDS = env_list('CHANNEL_IDS')

MIN_DELAY = env_int('MIN_DELAY', 20)
MAX_DELAY = env_int('MAX_DELAY', 40)
SELLALL_INTERVAL = env_int('SELLALL_INTERVAL', 100)
SELLALL_COOLDOWN = env_int('SELLALL_COOLDOWN', 600)

GEM_ENABLED = env_bool('GEM_ENABLED', True)
GEM_IDS = [int(x) for x in env_list('GEM_IDS', '51,52,53,56') if x.isdigit()]

INVENTORY_CHECK_INTERVAL = env_int('INVENTORY_CHECK_INTERVAL', 25)
USE_LOOTBOXES = env_bool('USE_LOOTBOXES', True)
USE_WEAPON_CRATES = env_bool('USE_WEAPON_CRATES', True)
AUTO_CLAIM = env_bool('AUTO_CLAIM', True)
VERIFY_SOUND = env_bool('VERIFY_SOUND', True)

CAPTCHA_SERVICE = os.environ.get('CAPTCHA_SERVICE', 'manual')
CAPMONSTER_API_KEY = os.environ.get('CAPMONSTER_API_KEY', '')
TWOCAPTCHA_API_KEY = os.environ.get('TWOCAPTCHA_API_KEY', '')

# Per-token gem overrides (format: TOKEN_GEMS_<token_prefix>=id1,id2,id3)
TOKEN_GEMS_OVERRIDES_RAW = os.environ.get('TOKEN_GEMS_OVERRIDES', '')

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ====== PARSE PER-TOKEN GEM OVERRIDES ======
TOKEN_GEMS_OVERRIDES = {}
if TOKEN_GEMS_OVERRIDES_RAW:
    try:
        TOKEN_GEMS_OVERRIDES = json.loads(TOKEN_GEMS_OVERRIDES_RAW)
    except json.JSONDecodeError:
        print("[!] Invalid TOKEN_GEMS_OVERRIDES format. Use JSON: {\"token_prefix\": [51,65,72]}")

# Also scan for TOKEN_GEMS_<prefix> style env vars
for key, val in os.environ.items():
    if key.startswith('TOKEN_GEMS_') and key != 'TOKEN_GEMS_OVERRIDES':
        prefix = key[11:]  # Remove 'TOKEN_GEMS_' prefix
        try:
            ids = [int(x.strip()) for x in val.split(',') if x.strip().isdigit()]
            if ids:
                TOKEN_GEMS_OVERRIDES[prefix] = ids
        except:
            pass

# ====== VALIDATION ======
if not DISCORD_TOKENS:
    print("[!] No DISCORD_TOKENS found in environment!")
    print("[!] Set DISCORD_TOKENS in .env or Railway variables")
    sys.exit(1)

valid_channels = [c for c in CHANNEL_IDS if c.isdigit()]
if not valid_channels:
    print("[!] No valid CHANNEL_IDS found in environment!")
    print("[!] Set CHANNEL_IDS in .env or Railway variables")
    sys.exit(1)

print(f"[+] Loaded {len(DISCORD_TOKENS)} token(s)")
print(f"[+] Loaded {len(valid_channels)} channel(s)")
print(f"[+] Timing: {MIN_DELAY}s - {MAX_DELAY}s")
print(f"[+] Gems: {GEM_IDS if GEM_ENABLED else 'DISABLED'}")
print(f"[+] Sellall: every {SELLALL_INTERVAL} / {SELLALL_COOLDOWN}s cooldown")


# ====== API HELPERS ======
HEADERS_TEMPLATE = {
    "Content-Type": "application/json",
    "User-Agent": USER_AGENT,
    "Origin": "https://discord.com",
    "Referer": "https://discord.com/channels/@me"
}

def send_message(token, channel_id, content):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {**HEADERS_TEMPLATE, "Authorization": token}
    payload = {"content": content}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 429:
            retry = r.json().get('retry_after', 5)
            print(f"  [!] Rate limited, waiting {retry}s...")
            time.sleep(retry + 1)
            return None
        return None
    except Exception as e:
        return None

def get_recent_messages(token, channel_id, limit=5):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit={limit}"
    headers = {**HEADERS_TEMPLATE, "Authorization": token}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
        return []
    except:
        return []

def check_verification(token, channel_id):
    messages = get_recent_messages(token, channel_id, limit=3)
    for msg in messages:
        content = msg.get("content", "").lower()
        author = msg.get("author", {}).get("username", "").lower()
        if "owo" in author or "owo" in content:
            if any(w in content for w in ["human", "verify", "captcha", "verification", "are you human"]):
                return True
    return False

def play_alert():
    try:
        import winsound
        for _ in range(5):
            winsound.Beep(1000, 300)
            time.sleep(0.2)
        print("\n[!!!] 🔔 HUMAN VERIFICATION DETECTED!")
    except ImportError:
        print("\a" * 5)
        print("\n[!!!] 🔔 HUMAN VERIFICATION DETECTED!")

def get_username(token):
    headers = {**HEADERS_TEMPLATE, "Authorization": token}
    try:
        r = requests.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=10)
        if r.status_code == 200:
            d = r.json()
            return f"{d.get('username', '?')}#{d.get('discriminator', '0000')}"
    except:
        pass
    return "Unknown"


# ====== OWO SELFBOT CLASS ======
class OWOSelfbot:
    def __init__(self, token, channels):
        self.token = token
        self.channels = channels
        self.username = get_username(token)
        self.command_count = 0
        self.cycle_count = 0
        self.running = True
        self.last_gem_check = 0
        self.last_inv_check = 0
        self.last_claim = 0
        self.gems_active = False
        
        # Per-token gem overrides
        self.gem_ids = self._resolve_gem_ids()
        
    def _resolve_gem_ids(self):
        """Check if this token has custom gem IDs via override."""
        # Check by full token prefix (first 10 chars)
        for prefix, ids in TOKEN_GEMS_OVERRIDES.items():
            if self.token.startswith(prefix):
                print(f"  [{self.username}] Using custom gems: {ids}")
                return ids
        return GEM_IDS
    
    def _tag(self):
        return f"[{self.username}]"
    
    def _pick_channel(self):
        return random.choice(self.channels)
    
    def _get_delay(self):
        return random.uniform(MIN_DELAY, MAX_DELAY)
    
    def _get_owo_cmd(self):
        commands = [
            "owo", "owo", "owo", "owo",
            "owo hunt", "owo hunt", "owo hunt",
            "owo battle", "owo battle",
            "owo dig", "owo fish",
            "owo pray",
        ]
        return random.choice(commands)
    
    def _get_gem_use_cmd(self):
        selected = random.sample(self.gem_ids, min(len(self.gem_ids), random.randint(1, 4)))
        return f"owo use {' '.join(str(g) for g in selected)}"
    
    def _check_and_handle_verification(self, channel_id):
        if check_verification(self.token, channel_id):
            if VERIFY_SOUND:
                play_alert()
            print(f"{self._tag()} [!!!] HUMAN VERIFICATION DETECTED in channel!")
            print(f"{self._tag()} Paused. Solve the captcha manually, then press Enter.")
            input(f"{self._tag()} Press Enter after verifying...")
            print(f"{self._tag()} Resuming...")
            return True
        return False
    
    def _do_sellall(self):
        self.command_count = 0
        channel = self._pick_channel()
        
        print(f"{self._tag()} ⚡ SELLALL triggered!")
        send_message(self.token, channel, "owo sellall")
        print(f"{self._tag()} 💰 Sent 'owo sellall'")
        
        print(f"{self._tag()} 😴 Cooldown: {SELLALL_COOLDOWN//60} min")
        end = time.time() + SELLALL_COOLDOWN
        while time.time() < end and self.running:
            for ch in random.sample(self.channels, min(2, len(self.channels))):
                self._check_and_handle_verification(ch)
            time.sleep(10)
        
        print(f"{self._tag()} ✅ Cooldown done, resuming")
    
    def _do_gem_equip(self):
        channel = self._pick_channel()
        cmd = self._get_gem_use_cmd()
        send_message(self.token, channel, cmd)
        print(f"{self._tag()} 💎 Gems equipped: {cmd}")
        self.gems_active = True
        self.last_gem_check = self.cycle_count
    
    def _do_inventory_use(self):
        channel = self._pick_channel()
        send_message(self.token, channel, "owo inv")
        time.sleep(random.uniform(2, 4))
        
        if USE_LOOTBOXES:
            send_message(self.token, channel, "owo use 50")
            print(f"{self._tag()} 📦 Used lootbox")
            time.sleep(random.uniform(1, 2))
        
        if USE_WEAPON_CRATES:
            send_message(self.token, channel, "owo use 100")
            print(f"{self._tag()} 📦 Used weapon crate")
            time.sleep(random.uniform(1, 2))
        
        self.last_inv_check = self.cycle_count
    
    def _do_claim(self):
        channel = self._pick_channel()
        send_message(self.token, channel, "owo claim")
        print(f"{self._tag()} 🎁 Claimed daily")
        time.sleep(random.uniform(1, 2))
        send_message(self.token, channel, "owo daily")
        print(f"{self._tag()} 📅 Daily command sent")
        self.last_claim = time.time()
    
    def run(self):
        print(f"{self._tag()} Started | Gems: {self.gem_ids}")
        
        while self.running:
            try:
                # Auto-claim every ~8 hours
                if AUTO_CLAIM and self.last_claim > 0 and (time.time() - self.last_claim > 28800):
                    self._do_claim()
                # First claim
                if AUTO_CLAIM and self.last_claim == 0 and self.cycle_count > 3:
                    self._do_claim()
                
                # Equip gems
                if GEM_ENABLED and not self.gems_active:
                    self._do_gem_equip()
                elif GEM_ENABLED and (self.cycle_count - self.last_gem_check > 20):
                    self.gems_active = False
                
                # Inventory management
                if INVENTORY_CHECK_INTERVAL > 0 and self.cycle_count > 0 \
                   and self.cycle_count % INVENTORY_CHECK_INTERVAL == 0:
                    self._do_inventory_use()
                
                # Main command
                channel = self._pick_channel()
                cmd = self._get_owo_cmd()
                
                self.command_count += 1
                self.cycle_count += 1
                
                print(f"{self._tag()} [{datetime.now().strftime('%H:%M:%S')}] #{self.command_count} '{cmd}'")
                send_message(self.token, channel, cmd)
                
                # Check verification
                self._check_and_handle_verification(channel)
                
                # Sellall check
                if self.command_count >= SELLALL_INTERVAL:
                    self._do_sellall()
                    continue
                
                # Delay with verification checks
                delay = self._get_delay()
                elapsed = 0
                while elapsed < delay and self.running:
                    time.sleep(1)
                    elapsed += 1
                    if int(elapsed) % 5 == 0 and elapsed > 0:
                        for ch in random.sample(self.channels, min(1, len(self.channels))):
                            self._check_and_handle_verification(ch)
                
            except KeyboardInterrupt:
                print(f"\n{self._tag()} Stopped.")
                self.running = False
                break
            except Exception as e:
                print(f"{self._tag()} Error: {e}")
                time.sleep(15)
    
    def stop(self):
        self.running = False


# ====== MAIN ======
def main():
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║     OWO MULTI-TOKEN SELFBOT v3.0        ║")
    print("  ║     .env Config | Railway Ready          ║")
    print("  ╚══════════════════════════════════════════╝")
    print()
    
    # Detect Railway
    if os.environ.get('RAILWAY_PROJECT_ID'):
        print("[+] Running on Railway")
    
    print(f"  Tokens:  {len(DISCORD_TOKENS)}")
    print(f"  Channels: {len(valid_channels)}")
    print(f"  Delay:   {MIN_DELAY}s - {MAX_DELAY}s")
    print(f"  Sellall: every {SELLALL_INTERVAL} / {SELLALL_COOLDOWN}s")
    print(f"  Gems:    {GEM_IDS if GEM_ENABLED else 'OFF'}")
    print(f"  Captcha: {CAPTCHA_SERVICE}")
    print()
    
    # Start all bots
    bots = []
    threads = []
    
    for token in DISCORD_TOKENS:
        bot = OWOSelfbot(token, valid_channels)
        bots.append(bot)
        t = threading.Thread(target=bot.run, daemon=True)
        threads.append(t)
        t.start()
        time.sleep(random.uniform(2, 5))
    
    print(f"\n  ✅ {len(bots)} bot(s) running. Ctrl+C to stop.\n")
    
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  ⛔ Shutting down...")
        for bot in bots:
            bot.stop()
        print("  ✅ Done.\n")


if __name__ == "__main__":
    main()