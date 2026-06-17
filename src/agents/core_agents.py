import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from src.schema.schema import AgentState
from src.components.rag_engine import RestaurantMenuRAGEngine

load_dotenv(override=False)

class MenuAgent:
    def __init__(self):
        self.rag_engine = RestaurantMenuRAGEngine()
        self.llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name=os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile"),
            temperature=0.2
        )

    def execute(self, state: AgentState) -> dict:
        user_msg = state["messages"][-1].content
        menu_context = self.rag_engine.query_menu_records(user_query=user_msg, max_results=3)
        
        system_prompt = (
            "You are the Menu Agent for a restaurant concierge system.\n"
            "Answer the customer's query using only the provided menu context below.\n"
            "If an item is not found in the context, politely state that it is unavailable.\n\n"
            f"Active Menu Context:\n{menu_context}"
        )
        
        response = self.llm.invoke([
            ("system", system_prompt),
            ("user", user_msg)
        ])
        
        return {
            "messages": [response]
        }


class RecommendationAgent:
    def __init__(self):
        self.rag_engine = RestaurantMenuRAGEngine()
        self.llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name=os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile"),
            temperature=0.5
        )

    def execute(self, state: AgentState) -> dict:
        user_msg = state["messages"][-1].content
        menu_context = self.rag_engine.query_menu_records(user_query=user_msg, max_results=4)
        
        system_prompt = (
            "You are the Recommendation Agent for a restaurant concierge system.\n"
            "Suggest individual items or meal combinations based on user requirements (budget, group count, etc.).\n"
            "Calculate total prices accurately and ensure suggested items exist in the active menu context.\n\n"
            f"Active Menu Context:\n{menu_context}"
        )
        
        response = self.llm.invoke([
            ("system", system_prompt),
            ("user", user_msg)
        ])
        
        return {
            "messages": [response]
        }