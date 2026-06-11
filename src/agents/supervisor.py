from src.schema.schema import AgentState

class SupervisorAgent:
    """Orchestrates workflow routing by mapping detected intents to destination agents."""
    
    def __init__(self):
        # Map intents directly to the LangGraph node names handling them
        self.route_map = {
            "menu_query": "menu_agent",
            "food_recommendation": "recommendation_agent",
            "reservation": "reservation_agent",
            "place_order": "order_agent",
            "track_order": "tracking_agent",
            "feedback": "feedback_agent",
            "general_chat": "general_chat_agent"
        }

    def route(self, state: AgentState) -> dict:
        """Reads current intent and assigns the next agent node to execute."""
        intent = state.get("current_intent")
        
        # Fallback to general chat if intent is unknown or missing
        next_agent = self.route_map.get(intent, "general_chat_agent")
        
        return {
            "next_agent": next_agent
        }