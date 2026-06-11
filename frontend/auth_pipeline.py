import streamlit as st
from src.components.database import DatabaseManager
from dotenv import load_dotenv

load_dotenv()
class AuthPipeline:
    """Manages the isolated login, registration, and session states for restaurant guests."""
    
    def __init__(self):
        self.db = DatabaseManager()

    def render_sidebar_auth(self):
        """Renders the secure luxury login/register wizard in the Streamlit sidebar."""
        st.sidebar.title("🔐 Guest Portal")
        auth_mode = st.sidebar.radio("Choose Action", ["Login", "Register New Account"])

        if auth_mode == "Register New Account":
            st.sidebar.subheader("Create Profile")
            reg_name = st.sidebar.text_input("Full Name")
            reg_telegram_id = st.sidebar.text_input("Telegram ID (Without @)")
            reg_phone = st.sidebar.text_input("WhatsApp Phone (With Country Code)")
            
            if st.sidebar.button("Register Account"):
                if not reg_telegram_id or not reg_phone:
                    st.sidebar.error("Telegram ID and Phone Number are required.")
                else:
                    self._register_user(reg_name, reg_telegram_id, reg_phone)
        else:
            st.sidebar.subheader("Sign In")
            login_id = st.sidebar.text_input("Enter Registered Telegram ID")
            
            if st.sidebar.button("Log In"):
                if not login_id:
                    st.sidebar.error("Please enter your Telegram ID to login.")
                else:
                    self._login_user(login_id)

        # Render logout button if the user session is active
        if st.session_state.get("logged_in", False):
            if st.sidebar.button("Log Out"):
                st.session_state.logged_in = False
                st.session_state.user_telegram_id = None
                st.session_state.customer_id = None
                st.rerun()

    def _register_user(self, name: str, telegram_id: str, phone: str):
        """Handles internal database execution to save user profiles securely."""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT customer_id FROM customers WHERE telegram_id = %s", (telegram_id,))
            if cursor.fetchone():
                st.sidebar.warning("Telegram ID already registered. Please Login.")
            else:
                cursor.execute(
                    "INSERT INTO customers (name, telegram_id, phone_number) VALUES (%s, %s, %s)",
                    (name if name else None, telegram_id, phone)
                )
                conn.commit()
                st.sidebar.success("Account created! Switch to Login to sign in.")
            
            cursor.close()
            conn.close()
        except Exception as e:
            st.sidebar.error(f"Registration dropped: {e}")

    def _login_user(self, telegram_id: str):
        """Validates credentials and maps persistent database primary keys to the active session."""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT customer_id, name, phone_number FROM customers WHERE telegram_id = %s", (telegram_id,))
            row = cursor.fetchone()
            
            if row:
                st.session_state.logged_in = True
                st.session_state.customer_id = row[0]
                st.session_state.user_telegram_id = telegram_id
                st.session_state.phone_number = row[2]
                st.sidebar.success(f"Welcome back, {row[1] if row[1] else telegram_id}!")
                st.rerun()
            else:
                st.sidebar.error("Account not found. Please register first.")
                
            cursor.close()
            conn.close()
        except Exception as e:
            st.sidebar.error(f"Login failed: {e}")