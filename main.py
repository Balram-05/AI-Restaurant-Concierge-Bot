import os
from dotenv import load_dotenv
load_dotenv(override=False)

import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from src.components.database import DatabaseManager
from src.components.graph_bot import RestaurantMultiAgentSystem
from src.utils.telegram_api import TelegramAPIWrapper

# TEMPORARY DEBUG PRINT
print(f"DEBUG: GROQ_API_KEY is set: {os.getenv('GROQ_API_KEY') is not None}")
if os.getenv('GROQ_API_KEY'):
    print(f"DEBUG: Key starts with: {os.getenv('GROQ_API_KEY')[:7]}")

# Initialize FastAPI application container instance
app = FastAPI(
    title="Multi-Agent AI Restaurant Concierge API",
    description="Production backend managing high-speed message loops via LangGraph.",
    version="1.0.0"
)

# Core singletons initialization
db_manager = DatabaseManager()
agent_system = RestaurantMultiAgentSystem()
telegram_client = TelegramAPIWrapper()

def process_bot_interaction(telegram_id: str, text: str, phone_number: str = None):
    """Background task to run message payload loops through LangGraph and reply via Telegram."""
    # Lookup or register the customer ID in the database before processing
    customer_id = db_manager.get_or_create_customer(telegram_id=telegram_id, phone_number=phone_number)
    
    # Structure the base state initialization dictionary matching AgentState channels
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
        # Run the complete compiled multi-agent execution pipeline graph
        final_state = agent_system.run_interaction(initial_state)
        
        # Pull the very last assistant response from the processed state history
        assistant_reply = final_state["messages"][-1].content
        
        # Fire the textual message payload directly back to the user chat screen on Telegram
        telegram_client.send_message(chat_id=telegram_id, text=assistant_reply)
    except Exception as e:
        print(f"❌ Error during multi-agent graph execution loop: {e}")
        error_fallback = "I am experiencing temporary connection problems. Please try again shortly."
        telegram_client.send_message(chat_id=telegram_id, text=error_fallback)

@app.get("/")
def health_check():
    """Simple root endpoint to quickly verify service up-time status."""
    return {"status": "healthy", "service": "Restaurant Concierge Engine"}

@app.post("/webhook/telegram")
async def telegram_webhook_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    Receives incoming JSON updates from Telegram Bot API servers.
    Offloads execution to background worker threads to ensure sub-second response times.
    """
    try:
        payload = await request.json()
        
        # Guardrail check to verify message object structure
        if "message" not in payload or "text" not in payload["message"]:
            return {"status": "ignored", "reason": "No readable text content found"}
            
        message_data = payload["message"]
        chat_id = str(message_data["chat"]["id"])
        user_text = message_data["text"]
        
        # Extract optional phone number from contact metadata fields if shared
        contact_phone = None
        if "contact" in message_data and "phone_number" in message_data["contact"]:
            contact_phone = str(message_data["contact"]["phone_number"])

        # Enqueue the business logic loop task into non-blocking async background threads
        background_tasks.add_task(
            process_bot_interaction,
            telegram_id=chat_id,
            text=user_text,
            phone_number=contact_phone
        )
        
        return {"status": "enqueued"}
    except Exception as e:
        print(f"❌ Webhook parsing failure: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)