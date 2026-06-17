import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from src.schema.schema import AgentState
from src.components.database import DatabaseManager

load_dotenv(override=False)

class ReservationAgent:
    def __init__(self):
        self.db = DatabaseManager()
        self.llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name=os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile"),
            temperature=0.0
        )

    def execute(self, state: AgentState) -> dict:
        user_msg = state["messages"][-1].content
        customer_id = state.get("customer_id")

        if not customer_id:
            customer_id = self.db.get_or_create_customer(telegram_id=state["telegram_id"], phone_number=state.get("phone_number"))

        system_prompt = (
            "You are a structured data extractor for a restaurant booking system.\n"
            "Extract the reservation details from the user's message.\n"
            "Respond ONLY with a valid comma-separated string in this exact format: YYYY-MM-DD,HH:MM:SS,guest_count\n"
            f"If today's date context is needed, note that today is: {datetime.now().strftime('%Y-%m-%d')}.\n"
            "If any detail is missing, respond with 'MISSING'."
        )

        llm_out = self.llm.invoke([("system", system_prompt), ("user", user_msg)]).content.strip()

        if "MISSING" in llm_out or "," not in llm_out:
            return {"messages": [self.llm.invoke([
                ("system", "Ask the user politely to provide the missing reservation details (date, time, or number of guests)."),
                ("user", user_msg)
            ])]}

        try:
            date_str, time_str, count_str = llm_out.split(",")
            reservation_id = f"RES{uuid.uuid4().hex[:4].upper()}"

            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO reservations (reservation_id, customer_id, date, time, guest_count) VALUES (%s, %s, %s, %s, %s)",
                (reservation_id, customer_id, date_str.strip(), time_str.strip(), int(count_str.strip()))
            )
            conn.commit()
            cursor.close()
            conn.close()

            return {
                "messages": [("assistant", f"I have successfully booked your table! Your reservation reference is {reservation_id}.")],
                "current_reservation_id": reservation_id,  
                "current_intent": "reservation"
            }
        except Exception:
            return {"messages": [("assistant", "Sorry, I could not complete your booking request at the moment.")]}


class OrderAgent:
    def __init__(self):
        self.db = DatabaseManager()
        self.llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name=os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile"),
            temperature=0.0
        )
        self.prices = {
            "Paneer Pizza": 299,
            "Veg Burger": 120,
            "Cheese French Fries": 150,
            "Margherita Pizza": 249,
            "Coke / Coca Cola": 40,
            "Paneer Burger": 160
        }

    def execute(self, state: AgentState) -> dict:
        user_msg = state["messages"][-1].content
        customer_id = state.get("customer_id")

        if not customer_id:
            customer_id = self.db.get_or_create_customer(telegram_id=state["telegram_id"], phone_number=state.get("phone_number"))

        if any(keyword in user_msg.lower() for keyword in ["bill", "total", "checkout", "amount"]):
            try:
                conn = self.db._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT items, order_id FROM orders WHERE customer_id = %s ORDER BY created_at DESC LIMIT 1",
                    (customer_id,)
                )
                row = cursor.fetchone()
                cursor.close()
                conn.close()

                if not row:
                    return {"messages": [("assistant", "Your active cart is currently empty! Order some dishes first.")]}
                
                items_summary = row[0]
                order_id = row[1]
                
                calc_prompt = (
                    f"You are the billing system calculator. Based on the items string: '{items_summary}' "
                    f"and this absolute pricing sheet: {self.prices}, compile a beautiful itemized text bill response.\n"
                    "Show items, quantities, matching individual costs, and sum up the exact Final Grand Total clearly."
                )
                bill_invoice = self.llm.invoke([("system", calc_prompt)]).content
                return {"messages": [("assistant", f"📄 **Order Invoice - ID: {order_id}**\n\n{bill_invoice}")]}
            except Exception:
                return {"messages": [("assistant", "Could not calculate your bill details at this moment.")]}

        system_prompt = (
            "You are a food order processing assistant.\n"
            "Extract the list of items and quantities from the user message.\n"
            "Respond ONLY with a clean summarized string of the items found (e.g., '2x Veg Burger, 1x Coke').\n"
            "If no clear items are being added, respond with 'EMPTY'."
        )

        extracted_items = self.llm.invoke([("system", system_prompt), ("user", user_msg)]).content.strip()

        if "EMPTY" in extracted_items:
            return {"messages": [("assistant", "What items would you like to add to your cart? Please specify quantities.")]}

        try:
            order_id = f"ORD{uuid.uuid4().hex[:4].upper()}"

            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO orders (order_id, customer_id, items, status) VALUES (%s, %s, %s, 'Received')",
                (order_id, customer_id, extracted_items)
            )
            conn.commit()
            cursor.close()
            conn.close()

            confirmation = f"🛒 Added to Cart! Order ID: {order_id}.\nItems: {extracted_items}.\n\nType *'bill'* whenever you are ready to check out the complete total amount!"
            return {
                "current_order_id": order_id,
                "messages": [("assistant", confirmation)]
            }
        except Exception:
            return {"messages": [("assistant", "An error occurred while building your order cart.")]}