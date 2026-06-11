import os
from langchain_groq import ChatGroq
from src.schema.schema import AgentState
from src.components.database import DatabaseManager

class AnalyticsAgent:
    """Provides internal business performance metrics and query analysis for the owner."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name=os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile"),
            temperature=0.0
        )

    def execute(self, state: AgentState) -> dict:
        """Translates owner queries into explicit database insights using aggregation."""
        user_msg = state["messages"][-1].content
        
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # Fetch summary stat parameters across operational tables
            cursor.execute("SELECT COUNT(*) FROM orders")
            total_orders = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM reservations")
            total_reservations = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(rating) FROM feedback")
            avg_rating_raw = cursor.fetchone()[0]
            avg_rating = round(float(avg_rating_raw), 1) if avg_rating_raw else 0.0
            
            cursor.close()
            conn.close()
            
            # Build an structural context text block tracking live performance data
            stats_context = (
                f"Current Live Restaurant Stats:\n"
                f"- Total Orders Processed: {total_orders}\n"
                f"- Total Table Reservations: {total_reservations}\n"
                f"- Average Customer Rating: {avg_rating}/5 stars"
            )
            
            system_prompt = (
                "You are the Analytics Dashboard Agent for the restaurant owner layer.\n"
                "Answer the owner's operational question accurately using the data statistics provided below.\n"
                "Keep your response concise, clear, and business-focused.\n\n"
                f"Database Summary Stats:\n{stats_context}"
            )
            
            response = self.llm.invoke([
                ("system", system_prompt),
                ("user", user_msg)
            ])
            
            return {
                "messages": [response]
            }
            
        except Exception as e:
            print(f"❌ Analytics processing error: {e}")
            return {"messages": [("assistant", "Could not fetch system analytics records at this time.")]}