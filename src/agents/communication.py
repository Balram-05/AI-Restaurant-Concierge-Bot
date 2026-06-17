import os
from dotenv import load_dotenv
from src.schema.schema import AgentState
from src.components.database import DatabaseManager
from src.utils.whatsapp_api import WhatsAppAPIWrapper

load_dotenv(override=False)

class WhatsAppAgent:
    def __init__(self):
        self.whatsapp = WhatsAppAPIWrapper()

    def execute(self, state: AgentState) -> dict:
        phone = state.get("phone_number")
        order_id = state.get("current_order_id")
        reservation_id = state.get("current_reservation_id")
        intent = state.get("current_intent")

        active_id = order_id if intent != "reservation" else reservation_id
        if not active_id:
            return {"messages": []}

        if intent == "reservation":
            msg_text = f"Success! Your table booking has been confirmed. Booking Reference ID: {active_id}."
        else:
            msg_text = f"Success! Your delicious food order has been placed. Order Tracking ID: {active_id}."

        clean_phone = str(phone).strip().replace(" ", "").lstrip("+")
        whatsapp_text = f"📢 Confirmation: {msg_text}\nReference ID: {active_id}"
        sent = self.whatsapp.send_free_text(clean_phone, whatsapp_text)

        if sent:
            return {"messages": [("assistant", msg_text + "\n\n📱 A confirmation alert has been sent to your WhatsApp number!")]}
        else:
            return {"messages": [("assistant", msg_text + "\n\n⚠️ Could not send WhatsApp confirmation due to a delivery issue. Please check your order/booking status in-app.")]}


class FeedbackAgent:
    def __init__(self):
        self.db = DatabaseManager()

    def execute(self, state: AgentState) -> dict:
        messages = state.get("messages", [])
        customer_id = state.get("customer_id", 0)
        telegram_id = state.get("telegram_id", "")

        if not messages:
            return {"messages": [("assistant", "No interaction content found to process feedback.")]}

        user_msg = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])

        if not customer_id and telegram_id:
            customer_id = self.db.get_or_create_customer(telegram_id)

        rating = None
        words = user_msg.replace(",", " ").replace(".", " ").split()
        for word in words:
            if word.isdigit():
                val = int(word)
                if 1 <= val <= 5:
                    rating = val
                    break

        if rating is None:
            return {"messages": [("assistant", "Thank you for sharing your thoughts! Could you please explicitly rate us on a scale from 1 to 5 stars so we can record your review properly?")]}

        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            query = "INSERT INTO feedback (customer_id, rating, review) VALUES (%s, %s, %s)"
            cursor.execute(query, (customer_id, rating, user_msg))
            conn.commit()
            cursor.close()
            conn.close()

            return {"messages": [("assistant", f"⭐⭐⭐⭐⭐\nThank you so much! We have recorded your {rating}-star rating and feedback in our system. Your insights help our kitchen improve continuously!")]}
        except Exception:
            return {"messages": [("assistant", "Thank you for your feedback! We appreciated your message, though we encountered a temporary hiccup logging it into our database system.")]}