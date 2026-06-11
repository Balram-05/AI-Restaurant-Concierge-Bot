import os
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"
import sys
import streamlit as st
from dotenv import load_dotenv

# Path alignment to access source modules cleanly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from frontend.auth_pipeline import AuthPipeline
from src.components.graph_bot import RestaurantMultiAgentSystem
from src.components.rag_engine import RestaurantMenuRAGEngine

load_dotenv()

# App Configuration & Custom Luxury Theme
st.set_page_config(page_title="Gourmet Concierge Dashboard", page_icon="🍽️", layout="wide")

st.markdown("""
    <style>
    /* Premium Charcoal and Gold Aesthetic Design Layout Overrides */
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

# Initialize Session Memory Slots
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# --- DYNAMIC INJECTION OF THE AUTHENTICATION SIDEPANEL ---
auth_manager = AuthPipeline()
auth_manager.render_sidebar_auth()

# --- MAIN DISPLAY VIEWPORTS ---
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
            st.write("DEBUG session_state:", dict(st.session_state))
            if user_input:
                with st.spinner("Orchestrating agents..."):
                    # Populate our standard LangGraph runtime dictionary matching AgentState
                    
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