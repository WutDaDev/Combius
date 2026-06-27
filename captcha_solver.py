#!/usr/bin/env python3
"""
Captcha Solver - reads config from environment
"""

import os
import time
import json
import requests

DISCORD_HCAPTCHA_SITEKEY = "4c672d35-0701-42b2-88c3-78380b0db560"

CAPTCHA_SERVICE = os.environ.get('CAPTCHA_SERVICE', 'manual')
CAPMONSTER_KEY = os.environ.get('CAPMONSTER_API_KEY', '')
TWOCAPTCHA_KEY = os.environ.get('TWOCAPTCHA_API_KEY', '')

class CaptchaSolver:
    def __init__(self):
        self.service = CAPTCHA_SERVICE
        self.capmonster_key = CAPMONSTER_KEY
        self.two_captcha_key = TWOCAPTCHA_KEY
        
    def solve(self, sitekey=DISCORD_HCAPTCHA_SITEKEY, rqdata="", url="https://discord.com/channels/@me"):
        if self.service == "capmonster" and self.capmonster_key:
            return self._capmonster(sitekey, rqdata, url)
        elif self.service == "2captcha" and self.two_captcha_key:
            return self._twocaptcha(sitekey, rqdata, url)
        else:
            return self._manual()
    
    def _capmonster(self, sitekey, rqdata, url):
        print("[Captcha] CapMonster solving...")
        task = {
            "clientKey": self.capmonster_key,
            "task": {
                "type": "HCaptchaTaskProxyless",
                "websiteURL": url,
                "websiteKey": sitekey
            }
        }
        if rqdata:
            task["task"]["data"] = rqdata
        
        try:
            r = requests.post("https://api.capmonster.cloud/createTask", json=task, timeout=30)
            res = r.json()
            if res.get("errorId") != 0:
                print(f"[Captcha] Error: {res.get('errorDescription')}")
                return None
            
            tid = res.get("taskId")
            for _ in range(60):
                time.sleep(3)
                r = requests.post("https://api.capmonster.cloud/getTaskResult", json={
                    "clientKey": self.capmonster_key, "taskId": tid
                }, timeout=10)
                res = r.json()
                if res.get("status") == "ready":
                    token = res.get("solution", {}).get("gRecaptchaResponse")
                    print("[Captcha] ✅ Solved via CapMonster")
                    return token
            print("[Captcha] Timeout")
            return None
        except Exception as e:
            print(f"[Captcha] Error: {e}")
            return None
    
    def _twocaptcha(self, sitekey, rqdata, url):
        print("[Captcha] 2Captcha solving...")
        try:
            payload = {
                "key": self.two_captcha_key, "method": "hcaptcha",
                "sitekey": sitekey, "pageurl": url, "json": 1
            }
            if rqdata:
                payload["data"] = rqdata
            
            r = requests.post("https://2captcha.com/in.php", data=payload, timeout=30)
            res = r.json()
            if res.get("status") != 1:
                print(f"[Captcha] Error: {res}")
                return None
            
            cid = res.get("request")
            for _ in range(60):
                time.sleep(5)
                r = requests.get(
                    f"https://2captcha.com/res.php?key={self.two_captcha_key}&action=get&id={cid}&json=1",
                    timeout=10
                )
                res = r.json()
                if res.get("status") == 1:
                    print("[Captcha] ✅ Solved via 2Captcha")
                    return res.get("request")
            print("[Captcha] Timeout")
            return None
        except Exception as e:
            print(f"[Captcha] Error: {e}")
            return None
    
    def _manual(self):
        print("\n[!!!] CAPTCHA REQUIRED - Manual solve needed")
        print("Open: https://discord.com/channels/@me")
        token = input("Paste captcha token (Enter to skip): ").strip()
        return token if token else None