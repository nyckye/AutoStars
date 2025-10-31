import os
import json

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

config = load_config()

BOT_TOKEN = config.get("BOT_TOKEN", os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN"))
API_TON = config.get("API_TON", os.getenv("API_TON", "YOUR_API_TON"))
GROQ_API_KEY = config.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", "YOUR_GROQ_KEY"))

MNEMONIC_STR = config.get("MNEMONIC", os.getenv("MNEMONIC", ""))
MNEMONIC = MNEMONIC_STR.split(",") if MNEMONIC_STR else []

DATA = {
    "stel_ssid": config.get("STEL_SSID", os.getenv("STEL_SSID", "")),
    "stel_dt": config.get("STEL_DT", os.getenv("STEL_DT", "-240")),
    "stel_ton_token": config.get("STEL_TON_TOKEN", os.getenv("STEL_TON_TOKEN", "")),
    "stel_token": config.get("STEL_TOKEN", os.getenv("STEL_TOKEN", "")),
}

FRAGMENT_HASH = config.get("FRAGMENT_HASH", os.getenv("FRAGMENT_HASH", ""))
FRAGMENT_PUBLICKEY = config.get("FRAGMENT_PUBLICKEY", os.getenv("FRAGMENT_PUBLICKEY", ""))
FRAGMENT_WALLETS = config.get("FRAGMENT_WALLETS", os.getenv("FRAGMENT_WALLETS", ""))
FRAGMENT_ADDRES = config.get("FRAGMENT_ADDRES", os.getenv("FRAGMENT_ADDRES", ""))

ADMIN_IDS_STR = config.get("ADMIN_IDS", os.getenv("ADMIN_IDS", ""))
ADMIN_IDS = [int(x) for x in ADMIN_IDS_STR.split(",") if x]

SHOP_NAME = "AU Stars"
DAILY_BONUS_AMOUNT = 10
STAR_PRICE_RUB = 2.5

def update_config(key, value):
    config[key] = value
    save_config(config)
    
def get_config(key, default=""):
    return config.get(key, default)

def reload_config():
    global BOT_TOKEN, API_TON, GROQ_API_KEY, MNEMONIC, DATA, FRAGMENT_HASH
    global FRAGMENT_PUBLICKEY, FRAGMENT_WALLETS, FRAGMENT_ADDRES, ADMIN_IDS
    
    config_new = load_config()
    
    BOT_TOKEN = config_new.get("BOT_TOKEN", BOT_TOKEN)
    API_TON = config_new.get("API_TON", API_TON)
    GROQ_API_KEY = config_new.get("GROQ_API_KEY", GROQ_API_KEY)
    
    MNEMONIC_STR = config_new.get("MNEMONIC", "")
    MNEMONIC = MNEMONIC_STR.split(",") if MNEMONIC_STR else MNEMONIC
    
    DATA["stel_ssid"] = config_new.get("STEL_SSID", DATA["stel_ssid"])
    DATA["stel_dt"] = config_new.get("STEL_DT", DATA["stel_dt"])
    DATA["stel_ton_token"] = config_new.get("STEL_TON_TOKEN", DATA["stel_ton_token"])
    DATA["stel_token"] = config_new.get("STEL_TOKEN", DATA["stel_token"])
    
    FRAGMENT_HASH = config_new.get("FRAGMENT_HASH", FRAGMENT_HASH)
    FRAGMENT_PUBLICKEY = config_new.get("FRAGMENT_PUBLICKEY", FRAGMENT_PUBLICKEY)
    FRAGMENT_WALLETS = config_new.get("FRAGMENT_WALLETS", FRAGMENT_WALLETS)
    FRAGMENT_ADDRES = config_new.get("FRAGMENT_ADDRES", FRAGMENT_ADDRES)
    
    ADMIN_IDS_STR = config_new.get("ADMIN_IDS", "")
    ADMIN_IDS = [int(x) for x in ADMIN_IDS_STR.split(",") if x] if ADMIN_IDS_STR else ADMIN_IDS
