import os
import sys
import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=False)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.auth_pipeline import AuthPipeline
from src.components.graph_bot import RestaurantMultiAgentSystem
from src.components.rag_engine import RestaurantMenuRAGEngine

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
    .cart-box { background-color: #222222; padding: 15px; border-radius: 8px; border: 1px solid #333333; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "cart" not in st.session_state:
    st.session_state.cart = {}

# Menu Price Matrix matching RAG Engine Seeding exactly
MENU_PRICES = {
    "Paneer Pizza": 299,
    "Veg Burger": 120,
    "Cheese French Fries": 150,
    "Margherita Pizza": 249,
    "Coke / Coca Cola": 40,
    "Paneer Burger": 160
}

auth_manager = AuthPipeline()
auth_manager.render_sidebar_auth()

# --- SIDEBAR LIVE PERSISTENT SHOPPING CART ENGINE ---
if st.session_state.logged_in:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🛒 Your Active Dining Cart")
    
    if not st.session_state.cart:
        st.sidebar.info("Your cart is empty. Order via chatbot to populate items!")
    else:
        grand_total = 0
        for item, qty in list(st.session_state.cart.items()):
            price = MENU_PRICES.get(item, 100) # Fallback baseline default price
            item_total = price * qty
            grand_total += item_total
            
            col_item, col_qty = st.sidebar.columns([3, 1])
            col_item.write(f"🍽️ {item} (x{qty})")
            col_qty.write(f"₹{item_total}")
            
        st.sidebar.markdown(f"### **Total Bill: ₹{grand_total}**")
        
        if st.sidebar.button("Clear Shopping Cart"):
            st.session_state.cart = {}
            st.rerun()

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
                        
                        # Dynamic Cart Sync intercept wrapper logic
                        # Intercept structural extraction keywords inside final output state history
                        lower_text = user_input.lower()
                        for dish in MENU_PRICES.keys():
                            if dish.lower() in lower_text:
                                # Determine quantity implicitly or default safely to 1
                                qty = 1
                                words = lower_text.split()
                                for idx, word in enumerate(words):
                                    if word.isdigit() and idx < len(words) - 1 and words[idx+1] in dish.lower():
                                        qty = int(word)
                                        break
                                st.session_state.cart[dish] = st.session_state.cart.get(dish, 0) + qty
                        
                        # Force real-time view updates if bill context is requested conversational loop
                        if "bill" in lower_text or "total" in lower_text or "checkout" in lower_text:
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