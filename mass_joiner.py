#!/usr/bin/env python3
"""
Mass Discord Server Joiner - All tokens join one server
- Reads tokens and captcha config from .env
"""

import os
import sys
import time
import random
import json
import threading
import requests
from pathlib import Path
import hashlib
from datetime import datetime

# Load .env
try:
    from dotenv import load_dotenv
    if not os.environ.get('RAILWAY_PROJECT_ID'):
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
except ImportError:
    pass

from captcha_solver import CaptchaSolver

TOKENS = [t.strip() for t in os.environ.get('DISCORD_TOKENS', '').split(',') if t.strip()]
DEBUG = os.environ.get('MASS_JOIN_DEBUG', '').lower() in ('1','true','yes')

HEADERS_TEMPLATE = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://discord.com",
    "Referer": "https://discord.com/channels/@me"
}

def get_username(token):
    headers = {**HEADERS_TEMPLATE, "Authorization": token}
    try:
        r = requests.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=10)
        if r.status_code == 200:
            d = r.json()
            return f"{d.get('username','?')}#{d.get('discriminator','0000')}"
    except:
        pass
    return "Unknown"

def resolve_invite(invite):
    invite = invite.strip()
    for p in ["https://discord.gg/", "https://discord.com/invite/", "discord.gg/", "discord.com/invite/"]:
        if p in invite:
            invite = invite.split(p)[1].split()[0].split("/")[0]
            break
    return invite.split("/")[-1].split("?")[0]


def fetch_invite_info(invite_code):
    try:
        r = requests.get(f"https://discord.com/api/v9/invites/{invite_code}?with_counts=true", timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def join_server(token, invite_code, solver):
    username = get_username(token)
    headers = {**HEADERS_TEMPLATE, "Authorization": token}
    
    print(f"[{username}] Joining {invite_code}...")
    r = requests.post(f"https://discord.com/api/v9/invites/{invite_code}", headers=headers, timeout=15)
    
    if r.status_code == 200:
        print(f"[{username}] ✅ Joined!")
        return True
    
    if r.status_code == 400:
        try:
            data = r.json()
            err = data.get("captcha_key", [""])[0]
            if "captcha" in err.lower() or "verify" in err.lower():
                print(f"[{username}] Captcha required!")
                sitekey = data.get("captcha_sitekey", "4c672d35-0701-42b2-88c3-78380b0db560")
                rqdata = data.get("captcha_rqdata", "")
                rqtoken = data.get("captcha_rqtoken", "")
                
                solution = solver.solve(sitekey=sitekey, rqdata=rqdata)
                if not solution:
                    print(f"[{username}] ❌ No captcha solution")
                    return False
                
                join_headers = {
                    **headers,
                    "X-Captcha-Key": solution,
                    "X-Captcha-Rqtoken": rqtoken
                }
                sid = data.get("captcha_session_id")
                if sid:
                    join_headers["X-Captcha-Session-Id"] = sid
                
                r2 = requests.post(
                    f"https://discord.com/api/v9/invites/{invite_code}",
                    headers=join_headers, timeout=15
                )
                if r2.status_code == 200:
                    print(f"[{username}] ✅ Joined after captcha!")
                    return True
                else:
                    print(f"[{username}] ❌ Captcha failed: {r2.status_code}")
                    return False
        except:
            pass
    
    elif r.status_code == 429:
        retry = r.json().get("retry_after", 5)
        print(f"[{username}] Rate limited, waiting {retry}s...")
        time.sleep(retry + 1)
        return join_server(token, invite_code, solver)
    
    # Debug output
    if DEBUG:
        try:
            print(f"[{username}] Response body: {r.text}")
        except Exception:
            pass
    print(f"[{username}] ❌ HTTP {r.status_code}")
    return False

def main():
    if not TOKENS:
        print("[!] No DISCORD_TOKENS in environment")
        sys.exit(1)

    print("  ╔══════════════════════════════════════╗")
    print("  ║       MASS DISCORD JOINER           ║")
    print("  ╚══════════════════════════════════════╝")

    invite = input("Invite code/URL: ").strip() or sys.exit()
    code = resolve_invite(invite)
    info = fetch_invite_info(code)
    guild_id = None
    if info:
        guild = info.get('guild') or {}
        guild_id = guild.get('id')
        print(f"  Code: {code} | Guild: {guild.get('name','unknown')} | Tokens: {len(TOKENS)}")
    else:
        print(f"  Code: {code} | Tokens: {len(TOKENS)}")

    confirm = input(f"Prepare to process {len(TOKENS)} token(s)? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Aborted.")
        return

    # Load or create log
    log_path = Path(__file__).parent / 'mass_join_log.json'
    try:
        if log_path.exists():
            log = json.loads(log_path.read_text())
        else:
            log = {}
    except Exception:
        log = {}

    invite_log = log.get(code, {})

    solver = CaptchaSolver()

    success = 0
    failed = 0

    for token in TOKENS:
        # compute token hash to avoid storing raw token
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        username = get_username(token)

        # Check log: if this token hash already recorded as joined for this invite
        if token_hash in invite_log:
            entry = invite_log[token_hash]
            print(f"[{username}] ▶ Already recorded as joined at {entry.get('joined_at')}")
            success += 1
            # wait 10s before next token
            time.sleep(10)
            continue

        # If possible, check membership via /users/@me/guilds
        already_member = False
        if guild_id:
            try:
                headers = {**HEADERS_TEMPLATE, 'Authorization': token}
                r = requests.get('https://discord.com/api/v9/users/@me/guilds', headers=headers, timeout=10)
                if r.status_code == 200:
                    guilds = r.json()
                    if any(g.get('id') == guild_id for g in guilds):
                        already_member = True
            except Exception:
                pass

        if already_member:
            print(f"[{username}] ✅ Already a member of the guild")
            invite_log[token_hash] = {'username': username, 'joined_at': datetime.utcnow().isoformat()}
            success += 1
            # write log incrementally
            log[code] = invite_log
            try:
                log_path.write_text(json.dumps(log, indent=2))
            except Exception:
                pass
            time.sleep(10)
            continue

        # Do not massjoin immediately: perform join with 10s delay between tokens
        print(f"[{username}] Waiting 10s before attempting join...")
        time.sleep(10)
        joined = join_server(token, code, solver)
        if joined:
            invite_log[token_hash] = {'username': username, 'joined_at': datetime.utcnow().isoformat()}
            success += 1
        else:
            failed += 1

        # persist log after each token
        log[code] = invite_log
        try:
            log_path.write_text(json.dumps(log, indent=2))
        except Exception:
            pass

    print(f"\n  ✅ {success}/{len(TOKENS)} joined (recorded)")
    print(f"  ❌ {failed}/{len(TOKENS)} failed")


if __name__ == "__main__":
    main()