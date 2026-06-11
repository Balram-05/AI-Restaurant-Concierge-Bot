import os
import requests
from dotenv import load_dotenv

load_dotenv()

class WhatsAppAPIWrapper:
    def __init__(self):
        self.token = os.getenv("WHATSAPP_API_TOKEN")
        self.phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

        print("TOKEN EXISTS:", bool(self.token))
        print("TOKEN LENGTH:", len(self.token) if self.token else 0)
        print("PHONE ID:", self.phone_id)

        self.base_url = f"https://graph.facebook.com/v18.0/{self.phone_id}/messages"

    def send_free_text(self, to_phone: str, text_body: str) -> bool:
        print("=" * 50)
        print("WhatsApp send initiated")
        print("Recipient:", to_phone)

        if not self.token:
            print("TOKEN MISSING")
            return False

        if not self.phone_id:
            print("PHONE ID MISSING")
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
            print("Calling Meta API...")

            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=10
            )

            print("Status:", response.status_code)
            print("Body:", response.text)

            return response.status_code == 200

        except Exception as e:
            print("Exception:", repr(e))
            return False


        
        