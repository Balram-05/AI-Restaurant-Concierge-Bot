import os
import requests
from dotenv import load_dotenv

load_dotenv()

class WhatsAppAPIWrapper:
    def __init__(self):
        self.token = os.getenv("WHATSAPP_API_TOKEN")
        self.phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.base_url = f"https://graph.facebook.com/v18.0/{self.phone_id}/messages"

    def send_free_text(self, to_phone: str, text_body: str) -> bool:
        if not self.token or not self.phone_id:
            return False

        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"body": text_body}
        }

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False