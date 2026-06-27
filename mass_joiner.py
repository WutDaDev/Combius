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
    print(f"  Code: {code} | Tokens: {len(TOKENS)}")
    
    confirm = input(f"Join {len(TOKENS)} token(s)? (y/N): ").strip().lower()
    if confirm != 'y':
        return
    
    solver = CaptchaSolver()
    results = [False] * len(TOKENS)
    
    def _join(i, t):
        results[i] = join_server(t, code, solver)
    
    threads = []
    for i, token in enumerate(TOKENS):
        t = threading.Thread(target=_join, args=(i, token))
        threads.append(t)
        t.start()
        time.sleep(random.uniform(1.5, 3.5))
    
    for t in threads:
        t.join(timeout=180)
    
    success = sum(1 for r in results if r)
    print(f"\n  ✅ {success}/{len(TOKENS)} joined")
    print(f"  ❌ {len(TOKENS)-success}/{len(TOKENS)} failed")


if __name__ == "__main__":
    main()