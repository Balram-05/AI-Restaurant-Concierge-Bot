import os
import sys
import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=False)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.auth_pipeline import AuthPipeline
from src.components.graph_bot import RestaurantMultiAgentSystem
from src.components.rag_engine import RestaurantMenuRAGEngine
from src.components.database import DatabaseManager

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Gourmet Concierge Dashboard", page_icon="🍽️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #1A1A1A; color: #E0E0E0; }
    h1, h2, h3 { color: #D4AF37 !important; font-family: 'Playfair Display', serif; }
    div.stButton > button:first-child {
        background-color: #D4AF37 !important; color: #1A1A1A !important;
        border-radius: 8px !important; border: 1px solid #D4AF37 !important; font-weight: bold !important;
    }
    div.stButton > button:first-child:hover { background-color: #E6C655 !important; }
    section[data-testid="stSidebar"] { background-color: #111111 !important; border-right: 1px solid #2D2D2D; }
    </style>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

MENU_PRICES = {
    "Paneer Pizza": 299,
    "Veg Burger": 120,
    "Cheese French Fries": 150,
    "Margherita Pizza": 249,
    "Coke / Coca Cola": 40,
    "Paneer Burger": 160
}

db = DatabaseManager()
auth_manager = AuthPipeline()
auth_manager.render_sidebar_auth()

if st.session_state.logged_in:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🛒 Your Active Dining Cart")
    
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT items FROM orders WHERE customer_id = %s AND status = 'Cart'",
            (st.session_state.customer_id,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not rows:
            st.sidebar.info("Your cart is empty. Order via chatbot to populate items!")
        else:
            grand_total = 0
            for row in rows:
                items_str = row[0]
                parts = [p.strip() for p in items_str.split(",")]
                for part in parts:
                    if "x" in part:
                        qty_part, name_part = part.split("x", 1)
                        try:
                            qty = int(qty_part.strip())
                        except ValueError:
                            qty = 1
                        item_name = name_part.strip()
                    else:
                        qty = 1
                        item_name = part.strip()
                        
                    price = MENU_PRICES.get(item_name, 120)
                    item_total = price * qty
                    grand_total += item_total
                    
                    st.sidebar.write(f"🍽️ {item_name} (x{qty}) — ₹{item_total}")
            
            st.sidebar.markdown(f"### **Total Bill: ₹{grand_total}**")
            
            if st.sidebar.button("Clear Shopping Cart"):
                conn = db._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM orders WHERE customer_id = %s AND status = 'Cart'",
                    (st.session_state.customer_id,)
                )
                conn.commit()
                cursor.close()
                conn.close()
                st.rerun()
    except Exception:
        st.sidebar.error("Error linking with database cart.")

st.title("🍽️ Gourmet Concierge AI Hub")
st.write("Interact with our multi-agent culinary platform seamlessly from the web or your chat app.")

col_chat, col_info = st.columns([2, 1])

with col_chat:
    st.subheader("💬 Chat with Concierge Core")
    
    if not st.session_state.logged_in:
        st.info("💡 Please complete registration or sign in on the left Guest Portal sidebar to begin.")
    else:
        user_input = st.text_input("Ask about menus, reserve tables, or place orders:", placeholder="Type a message...")
        
        if st.button("Send to Agent System"):
            if user_input:
                with st.spinner("Orchestrating agents..."):
                    initial_state = {
                        "messages": [("user", user_input)],
                        "telegram_id": st.session_state.user_telegram_id,
                        "customer_id": st.session_state.customer_id,
                        "phone_number": st.session_state.get("phone_number", ""),
                        "current_intent": None,
                        "next_agent": None,
                        "current_order_id": None,
                        "current_reservation_id": None,
                        "metadata": {}
                    }
                    
                    try:
                        system = RestaurantMultiAgentSystem()
                        final_output = system.run_interaction(initial_state)
                        response_text = final_output["messages"][-1].content
                        st.markdown(f"**🤖 Assistant Response:**\n\n{response_text}")
                        st.rerun()
                            
                    except Exception as e:
                        st.error(f"Workflow execution failure: {e}")

with col_info:
    st.subheader("📊 Active Live Menu Quick-View")
    try:
        rag = RestaurantMenuRAGEngine()
        records = rag.query_menu_records(user_query="All dishes", max_results=6)
        st.markdown(records)
    except Exception:
        st.write("Menu catalog currently syncing offline.")