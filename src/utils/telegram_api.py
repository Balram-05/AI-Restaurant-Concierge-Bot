import os
import requests

class TelegramAPIWrapper:
    """Helper utility to handle outbound text communication to Telegram clients."""
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.base_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send_message(self, chat_id: str, text: str) -> bool:
        """Sends a direct text message to a specific Telegram chat ID."""
        if not self.token:
            print(f"⚠️ Telegram Token missing. Simulation output to {chat_id}: {text}")
            return True

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(self.base_url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")
            return False