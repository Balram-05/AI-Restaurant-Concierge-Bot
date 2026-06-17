import os
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from dotenv import load_dotenv
from src.components.database import DatabaseManager
from src.components.graph_bot import RestaurantMultiAgentSystem
from src.utils.telegram_api import TelegramAPIWrapper

load_dotenv(override=False)

app = FastAPI(
    title="Multi-Agent AI Restaurant Concierge API",
    description="Production backend managing high-speed message loops via LangGraph.",
    version="1.0.0"
)

db_manager = DatabaseManager()
agent_system = RestaurantMultiAgentSystem()
telegram_client = TelegramAPIWrapper()

def process_bot_interaction(telegram_id: str, text: str, phone_number: str = None):
    customer_id = db_manager.get_or_create_customer(telegram_id=telegram_id, phone_number=phone_number)
    
    initial_state = {
        "messages": [("user", text)],
        "telegram_id": telegram_id,
        "phone_number": phone_number,
        "customer_id": customer_id,
        "current_intent": None,
        "next_agent": None,
        "current_order_id": None,
        "current_reservation_id": None,
        "metadata": {}
    }
    
    try:
        final_state = agent_system.run_interaction(initial_state)
        assistant_reply = final_state["messages"][-1].content
        telegram_client.send_message(chat_id=telegram_id, text=assistant_reply)
    except Exception:
        error_fallback = "I am experiencing temporary connection problems. Please try again shortly."
        telegram_client.send_message(chat_id=telegram_id, text=error_fallback)

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "Restaurant Concierge Engine"}

@app.post("/webhook/telegram")
async def telegram_webhook_endpoint(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        
        if "message" not in payload or "text" not in payload["message"]:
            return {"status": "ignored", "reason": "No readable text content found"}
            
        message_data = payload["message"]
        chat_id = str(message_data["chat"]["id"])
        user_text = message_data["text"]
        
        contact_phone = None
        if "contact" in message_data and "phone_number" in message_data["contact"]:
            contact_phone = str(message_data["contact"]["phone_number"])

        background_tasks.add_task(
            process_bot_interaction,
            telegram_id=chat_id,
            text=user_text,
            phone_number=contact_phone
        )
        
        return {"status": "enqueued"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)