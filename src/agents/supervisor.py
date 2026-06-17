from src.schema.schema import AgentState

class SupervisorAgent:
    def __init__(self):
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
        intent = state.get("current_intent")
        next_agent = self.route_map.get(intent, "general_chat_agent")
        
        return {
            "next_agent": next_agent
        }