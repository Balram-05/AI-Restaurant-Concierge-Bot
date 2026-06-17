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

        # 1. Billing flow: User explicitly asks for bill/checkout
        if any(keyword in user_msg.lower() for keyword in ["bill", "total", "checkout", "amount"]):
            try:
                conn = self.db._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT items FROM orders WHERE customer_id = %s AND status = 'Cart' ORDER BY created_at ASC",
                    (customer_id,)
                )
                rows = cursor.fetchall()
                
                if not rows:
                    cursor.close()
                    conn.close()
                    return {"messages": [("assistant", "🛒 Your shopping cart is currently empty! Add items by asking me, like: 'Add 2 Veg Burgers to my cart'.")]}
                
                all_items = ", ".join([row[0] for row in rows])
                order_id = f"INV{uuid.uuid4().hex[:4].upper()}"
                
                # Mark as Completed so they are checked out
                cursor.execute(
                    "UPDATE orders SET status = 'Completed' WHERE customer_id = %s AND status = 'Cart'",
                    (customer_id,)
                )
                conn.commit()
                cursor.close()
                conn.close()
                
                calc_prompt = (
                    f"You are the dynamic billing system calculator. Consolidate this aggregated list of items: '{all_items}'.\n"
                    f"Using this explicit price dictionary matrix: {self.prices}, create a clean, elegant itemized receipt.\n"
                    "List each item, its quantity, matched individual cost, subtotal, and summarize the Final Grand Total at the bottom clearly."
                )
                bill_invoice = self.llm.invoke([("system", calc_prompt)]).content
                return {"messages": [("assistant", f"📄 **Gourmet Invoice Summary - {order_id}**\n\n{bill_invoice}")]}
            except Exception:
                return {"messages": [("assistant", "Could not calculate your cart bill metrics at this moment.")]}

        # 2. Add to Cart flow
        system_prompt = (
            "You are a food order item extractor for a restaurant cart interface.\n"
            "Extract the list of food items and their respective quantities mentioned in the user message.\n"
            "Respond ONLY with a clean summarized string of the items found exactly matching the items in the menu (e.g., '2x Veg Burger, 1x Coke / Coca Cola').\n"
            "If no clear menu items are being added to the cart, respond with 'EMPTY'."
        )

        extracted_items = self.llm.invoke([("system", system_prompt), ("user", user_msg)]).content.strip()

        if "EMPTY" in extracted_items or not extracted_items:
            return {"messages": [("assistant", "Which dishes would you like to add to your cart? Please specify quantities and items from our active menu.")]}

        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO orders (order_id, customer_id, items, status) VALUES (%s, %s, %s, 'Cart')",
                (f"CRT{uuid.uuid4().hex[:4].upper()}", customer_id, extracted_items)
            )
            conn.commit()
            cursor.close()
            conn.close()

            confirmation = (
                f"🛒 **Added to Cart successfully!**\n"
                f"Items: `{extracted_items}`\n\n"
                "You can continue adding more dishes, or simply type *'bill'* whenever you are ready to check out!"
            )
            return {"messages": [("assistant", confirmation)]}
        except Exception:
            return {"messages": [("assistant", "An error occurred while attempting to update your shopping cart entries.")]}