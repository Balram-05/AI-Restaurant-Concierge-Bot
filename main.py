import os
import re
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from src.components.database import DatabaseManager
from src.components.graph_bot import RestaurantMultiAgentSystem
from src.utils.telegram_api import TelegramAPIWrapper

load_dotenv(override=False)

app = FastAPI(
    title="Multi-Agent AI Restaurant Concierge API",
    version="1.0.0"
)

db_manager = DatabaseManager()
agent_system = RestaurantMultiAgentSystem()
telegram_client = TelegramAPIWrapper()

class WebChatPayload(BaseModel):
    telegram_id: str
    message_text: str
    phone_number: Optional[str] = None

def execute_agent_pipeline(telegram_id: str, text: str, phone_number: str = None) -> str:
    # Safe validation check to ensure telegram_id never passes blank down to MySQL
    t_id = str(telegram_id).strip()
    if not t_id or t_id == "None":
        t_id = "web_portal_fallback"

    conn = db_manager._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id, phone_number FROM customers WHERE telegram_id = %s", (t_id,))
    row = cursor.fetchone()
    
    customer_id = row[0] if row else None
    existing_phone = row[1] if row else None
    
    if not customer_id:
        customer_id = db_manager.get_or_create_customer(telegram_id=t_id, phone_number=phone_number)
    
    cursor.close()
    conn.close()

    initial_state = {
        "messages": [("user", text)],
        "telegram_id": t_id,
        "phone_number": existing_phone if existing_phone else phone_number,
        "customer_id": customer_id,
        "current_intent": None,
        "next_agent": None,
        "current_order_id": None,
        "current_reservation_id": None,
        "metadata": {}
    }
    
    final_state = agent_system.run_interaction(initial_state)
    return final_state["messages"][-1].content

def process_telegram_background(chat_id: str, text: str, phone_number: str = None):
    try:
        reply_msg = execute_agent_pipeline(telegram_id=chat_id, text=text, phone_number=phone_number)
        telegram_client.send_message(chat_id=chat_id, text=reply_msg)
    except Exception:
        error_fallback = "I am experiencing temporary connection problems. Please try again shortly."
        telegram_client.send_message(chat_id=chat_id, text=error_fallback)

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "Restaurant Concierge Engine"}

@app.post("/webhook/chat_portal")
def web_chat_portal_endpoint(payload: WebChatPayload):
    try:
        # Fallback parameter guards against empty Pydantic data layers
        t_id = str(payload.telegram_id).strip() if payload.telegram_id else "web_portal_fallback"
        if not t_id or t_id == "None":
            t_id = "web_portal_fallback"

        bot_reply = execute_agent_pipeline(
            telegram_id=t_id,
            text=payload.message_text,
            phone_number=payload.phone_number
        )
        return {"status": "success", "response": bot_reply}
    except Exception as e:
        return {"status": "error", "response": f"Server encountered a pipeline error processing your cart. Details: {str(e)}"}

@app.post("/webhook/telegram")
async def telegram_webhook_endpoint(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        if "message" not in payload or "text" not in payload["message"]:
            return {"status": "ignored"}
            
        message_data = payload["message"]
        chat_id = str(message_data["chat"]["id"])
        user_text = message_data["text"]
        
        contact_phone = None
        if "contact" in message_data and "phone_number" in message_data["contact"]:
            contact_phone = str(message_data["contact"]["phone_number"])

        background_tasks.add_task(
            process_telegram_background,
            chat_id=chat_id,
            text=user_text,
            phone_number=contact_phone
        )
        return {"status": "enqueued"}
    except Exception:
        return {"status": "error"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)