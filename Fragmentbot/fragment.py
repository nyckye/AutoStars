import logging
import base64
import re
import httpx
from tonutils.client import TonapiClient
from tonutils.wallet import WalletV5R1
from config import API_TON, MNEMONIC, DATA, FRAGMENT_HASH, FRAGMENT_PUBLICKEY, FRAGMENT_WALLETS, FRAGMENT_ADDRES

def get_cookies(DATA):
    return {
        "stel_ssid": DATA.get("stel_ssid", ""),
        "stel_dt": DATA.get("stel_dt", ""),
        "stel_ton_token": DATA.get("stel_ton_token", ""),
        "stel_token": DATA.get("stel_token", ""),
    }

def fix_base64_padding(b64_string: str) -> str:
    missing_padding = len(b64_string) % 4
    if missing_padding:
        b64_string += "=" * (4 - missing_padding)
    return b64_string

class FragmentClient:
    URL = f"https://fragment.com/api?hash={FRAGMENT_HASH}"

    async def fetch_recipient(self, query):
        data = {"query": query, "method": "searchStarsRecipient"}
        async with httpx.AsyncClient() as client:
            response = await client.post(self.URL, cookies=get_cookies(DATA), data=data)
            return response.json().get("found", {}).get("recipient")

    async def fetch_req_id(self, recipient, quantity):
        data = {"recipient": recipient, "quantity": quantity, "method": "initBuyStarsRequest"}
        async with httpx.AsyncClient() as client:
            response = await client.post(self.URL, cookies=get_cookies(DATA), data=data)
            return response.json().get("req_id")

    async def fetch_buy_link(self, recipient, req_id, quantity):
        data = {
            "address": f"{FRAGMENT_ADDRES}", 
            "chain": "-239",
            "walletStateInit": f"{FRAGMENT_WALLETS}",
            "publicKey": f"{FRAGMENT_PUBLICKEY}",
            "features": ["SendTransaction", {"name": "SendTransaction", "maxMessages": 255}],
            "maxProtocolVersion": 2,
            "platform": "iphone", 
            "appName": "Tonkeeper", 
            "appVersion": "5.0.14",
            "transaction": "1",
            "id": req_id,
            "show_sender": "0",
            "method": "getBuyStarsLink"
        }
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://fragment.com",
            "referer": f"https://fragment.com/stars/buy?recipient={recipient}&quantity={quantity}",
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            "x-requested-with": "XMLHttpRequest"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.URL, headers=headers, cookies=get_cookies(DATA), data=data)
            json_data = response.json()
            if json_data.get("ok") and "transaction" in json_data:
                transaction = json_data["transaction"]
                return transaction["messages"][0]["address"], transaction["messages"][0]["amount"], transaction["messages"][0]["payload"]
        return None, None, None

class TonTransaction:
    async def send_ton_transaction(self, recipient, amount_nano, la, stars):
        client = TonapiClient(api_key=API_TON, is_testnet=False)
        wallet, public_key, private_key, mnemonic = WalletV5R1.from_mnemonic(client, MNEMONIC)

        if not recipient or amount_nano <= 0:
            return None

        encoded_str = la
        decoded_bytes = base64.b64decode(fix_base64_padding(encoded_str))
        decoded_text = "".join(chr(b) if 32 <= b < 127 else " " for b in decoded_bytes)
        clean_text = re.sub(r"\s+", " ", decoded_text).strip()
        match = re.search(rf"{stars} Telegram Stars.*", clean_text)
        final_text = match.group(0) if match else clean_text

        tx_hash = await wallet.transfer(
            destination=recipient,
            amount=amount_nano,
            body=final_text,
        )
        logging.info(f"Транзакция отправлена: {tx_hash}")
        return tx_hash

async def buy_stars_process(QUERY, QUANTITY):
    client = FragmentClient()
    recipient = await client.fetch_recipient(QUERY)
    if recipient:
        req_id = await client.fetch_req_id(recipient, QUANTITY)
        if req_id:
            recipient_addr, amount_nano, la = await client.fetch_buy_link(recipient, req_id, QUANTITY)
            if recipient_addr and amount_nano and la:
                amount_decimal = float(amount_nano) / 1_000_000_000
                logging.info(f"Сумма для отправки: {amount_decimal:.4f} TON")
                transaction = TonTransaction()
                tx_hash = await transaction.send_ton_transaction(recipient_addr, amount_decimal, la, QUANTITY)
                if tx_hash:
                    return True, tx_hash
    return False, None
