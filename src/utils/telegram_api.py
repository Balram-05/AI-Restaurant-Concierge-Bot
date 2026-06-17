import os
import requests

class TelegramAPIWrapper:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.base_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send_message(self, chat_id: str, text: str) -> bool:
        if not self.token:
            return False

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(self.base_url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception:
            return False