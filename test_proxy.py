import os
import requests
from dotenv import load_dotenv

load_dotenv()

WB_PROXY_URL = os.getenv("WB_PROXY_URL", "").strip()
proxies = None
if WB_PROXY_URL:
    proxies = {
        "http": WB_PROXY_URL,
        "https": WB_PROXY_URL,
    }

print("WB_PROXY_URL:", WB_PROXY_URL)
print("proxies:", proxies)

ip_direct = requests.get("https://api.ipify.org?format=json", timeout=10).json()
print("DIRECT IP:", ip_direct)

if proxies:
    try:
        ip_proxy = requests.get(
            "https://api.ipify.org?format=json",
            timeout=10,
            proxies=proxies,
        ).json()
        print("PROXY IP:", ip_proxy)
    except Exception as e:
        print("Proxy request failed:", e)