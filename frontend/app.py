import os
import sys
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=False)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.auth_pipeline import AuthPipeline
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

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Exact Menu Price Tracking Sheets
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

# --- SIDEBAR DATABASE CART SYNC (BULLETPROOF PARSING) ---
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
            
            # Read every open cart entry from database records
            for row in rows:
                items_str = row[0]
                # Split entries if multiple items are stored in one row (e.g. "2x Veg Burger, 1x Coke")
                parts = [p.strip() for p in items_str.split(",")]
                
                for part in parts:
                    if not part:
                        continue
                        
                    qty = 1
                    item_name_extracted = part
                    
                    # Safely handle '2x Item' or '2 x Item' prefixes
                    if "x" in part.lower():
                        qty_part, name_part = part.lower().split("x", 1)
                        try:
                            qty = int(qty_part.strip())
                            item_name_extracted = name_part.strip()
                        except ValueError:
                            qty = 1

                    # Bulletproof Search: Fuzzy find the closest match inside our actual pricing menu dictionary keys
                    matched_key = None
                    for actual_menu_item in MENU_PRICES.keys():
                        if actual_menu_item.lower() in item_name_extracted or item_name_extracted in actual_menu_item.lower():
                            matched_key = actual_menu_item
                            break
                    
                    # If matched successfully, compute pricing metrics
                    if matched_key:
                        price = MENU_PRICES[matched_key]
                        item_total = price * qty
                        grand_total += item_total
                        st.sidebar.write(f"🍽️ **{matched_key}** (x{qty}) — ₹{item_total}")
                    else:
                        # Fallback for unrecognized text additions
                        st.sidebar.write(f"❓ *{part}* (Quantity Untracked)")
            
            st.sidebar.markdown("---")
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
        for role, text in st.session_state.chat_history:
            if role == "user":
                st.markdown(f"**🧑 You:** {text}")
            else:
                st.markdown(f"{text}")
        
        user_input = st.text_input("Ask about menus, reserve tables, or place orders:", placeholder="Type a message...", key="user_msg_input")
        
        if st.button("Send to Agent System"):
            if user_input:
                st.session_state.chat_history.append(("user", user_input))
                
                with st.spinner("Communicating with Multi-Agent Cluster..."):
                    t_id_raw = st.session_state.get("user_telegram_id", "web_portal_fallback")
                    if t_id_raw is None:
                        t_id_raw = "web_portal_fallback"

                    payload = {
                        "telegram_id": str(t_id_raw).strip(),
                        "message_text": str(user_input),
                        "phone_number": st.session_state.get("phone_number", None)
                    }
                    
                    try:
                        response = requests.post(f"{BACKEND_URL}/webhook/chat_portal", json=payload, timeout=15)
                        if response.status_code == 200:
                            reply_data = response.json()
                            assistant_response = reply_data.get("response", "Message logged successfully.")
                            st.session_state.chat_history.append(("assistant", f"**🤖 Bot:** {assistant_response}"))
                        else:
                            st.session_state.chat_history.append(("assistant", "⚠️ Error communicating with backend API node."))
                    except Exception as e:
                        st.session_state.chat_history.append(("assistant", f"⚠️ Network timeout connecting to backend logic: {e}"))
                
                st.rerun()

with col_info:
    st.subheader("📊 Active Live Menu Quick-View")
    try:
        rag = RestaurantMenuRAGEngine()
        records = rag.query_menu_records(user_query="All dishes", max_results=6)
        st.markdown(records)
    except Exception:
        st.write("Menu catalog currently syncing offline.")