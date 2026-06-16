import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import uuid
from datetime import datetime
from src.schema.schema import AgentState
from src.components.database import DatabaseManager

# Force-load environment variables right at the module import step
load_dotenv()

class ReservationAgent:
    """Handles table reservation queries including availability checks and booking creations."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name=os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile"),
            temperature=0.0
        )

    def execute(self, state: AgentState) -> dict:
        """Parses booking info from the message and logs the reservation into MySQL."""
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
        except Exception as e:
            print(f"❌ Reservation processing error: {e}")
            return {"messages": [("assistant", "Sorry, I could not complete your booking request at the moment.")]}


class OrderAgent:
    """Manages customer checkout cycles by adding or clearing selected food items."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name=os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile"),
            temperature=0.0
        )

    def execute(self, state: AgentState) -> dict:
        """Processes ordering requests and initializes order records within the database."""
        user_msg = state["messages"][-1].content
        customer_id = state.get("customer_id")

        if not customer_id:
            customer_id = self.db.get_or_create_customer(telegram_id=state["telegram_id"], phone_number=state.get("phone_number"))

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

            confirmation = f"Order created successfully! Order ID: {order_id}. Items: {extracted_items}. Status: Received."
            return {
                "current_order_id": order_id,
                "messages": [("assistant", confirmation)]
            }
        except Exception as e:
            print(f"❌ Order creation failure: {e}")
            return {"messages": [("assistant", "An error occurred while building your order cart.")]}