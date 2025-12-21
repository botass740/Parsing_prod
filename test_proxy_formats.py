"""
test_proxy_formats.py — проверка разных форматов прокси
"""

import requests

# Твои данные (замени на свои)
LOGIN = "23fmwsTtvu"
PASSWORD = "Wx8hCmKzI5"  # ← впиши сюда
IP = "45.132.252.132"
HTTP_PORT = "38267"
SOCKS_PORT = "25591"

print("=" * 60)
print("ПРОВЕРКА РАЗНЫХ ФОРМАТОВ ПРОКСИ")
print("=" * 60)

# Разные форматы подключения
formats = [
    # HTTP с авторизацией
    ("HTTP (login:pass@ip:port)", f"http://{LOGIN}:{PASSWORD}@{IP}:{HTTP_PORT}"),
    
    # HTTPS 
    ("HTTPS", f"https://{LOGIN}:{PASSWORD}@{IP}:{HTTP_PORT}"),
    
    # Без указания протокола в начале
    ("HTTP simple", f"{LOGIN}:{PASSWORD}@{IP}:{HTTP_PORT}"),
    
    # SOCKS5
    ("SOCKS5", f"socks5://{LOGIN}:{PASSWORD}@{IP}:{SOCKS_PORT}"),
    
    # SOCKS5h (с DNS через прокси)
    ("SOCKS5h", f"socks5h://{LOGIN}:{PASSWORD}@{IP}:{SOCKS_PORT}"),
]

for name, proxy_url in formats:
    print(f"\n--- {name} ---")
    print(f"URL: {proxy_url.replace(PASSWORD, '****')}")
    
    proxies = {"http": proxy_url, "https": proxy_url}
    
    try:
        resp = requests.get(
            "https://api.ipify.org?format=json",
            proxies=proxies,
            timeout=10
        )
        if resp.status_code == 200:
            ip = resp.json().get("ip")
            print(f"✅ РАБОТАЕТ! IP: {ip}")
        else:
            print(f"❌ Status: {resp.status_code}")
    except Exception as e:
        error_msg = str(e)
        if "10061" in error_msg:
            print("❌ Соединение отклонено (порт закрыт или неверный)")
        elif "timed out" in error_msg.lower():
            print("❌ Таймаут (прокси не отвечает)")
        elif "407" in error_msg:
            print("❌ Неверный логин/пароль")
        elif "ProxyError" in error_msg:
            print(f"❌ Ошибка прокси: {error_msg[:100]}")
        else:
            print(f"❌ Ошибка: {error_msg[:100]}")

print("\n" + "=" * 60)