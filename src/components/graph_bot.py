from langgraph.graph import StateGraph, END
from src.schema.schema import AgentState
from src.agents.intent import IntentAgent
from src.agents.supervisor import SupervisorAgent
from src.agents.core_agents import MenuAgent, RecommendationAgent
from src.agents.operational import ReservationAgent, OrderAgent
from src.agents.communication import WhatsAppAgent, FeedbackAgent
from src.agents.analytics import AnalyticsAgent

class RestaurantMultiAgentSystem:
    def __init__(self):
        self.intent_agent = IntentAgent()
        self.supervisor_agent = SupervisorAgent()
        self.menu_agent = MenuAgent()
        self.recommendation_agent = RecommendationAgent()
        self.reservation_agent = ReservationAgent()
        self.order_agent = OrderAgent()
        self.whatsapp_agent = WhatsAppAgent()
        self.feedback_agent = FeedbackAgent()
        self.analytics_agent = AnalyticsAgent()
        self.workflow = self._build_graph()

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(AgentState)

        builder.add_node("intent_router", self.intent_agent.classify)
        builder.add_node("supervisor", self.supervisor_agent.route)
        builder.add_node("menu_agent", self.menu_agent.execute)
        builder.add_node("recommendation_agent", self.recommendation_agent.execute)
        builder.add_node("reservation_agent", self.reservation_agent.execute)
        builder.add_node("order_agent", self.order_agent.execute)
        builder.add_node("whatsapp_agent", self.whatsapp_agent.execute)
        builder.add_node("feedback_agent", self.feedback_agent.execute)
        builder.add_node("analytics_agent", self.analytics_agent.execute)

        builder.set_entry_point("intent_router")
        builder.add_edge("intent_router", "supervisor")

        builder.add_conditional_edges(
            "supervisor",
            lambda state: state.get("next_agent", "menu_agent"),
            {
                "menu_agent": "menu_agent",
                "recommendation_agent": "recommendation_agent",
                "reservation_agent": "reservation_agent",
                "order_agent": "order_agent",
                "tracking_agent": "menu_agent",
                "feedback_agent": "feedback_agent",
                "general_chat_agent": "menu_agent",
                "analytics_agent": "analytics_agent"
            }
        )

        builder.add_edge("reservation_agent", "whatsapp_agent")
        builder.add_edge("order_agent", "whatsapp_agent")
        
        builder.add_edge("menu_agent", END)
        builder.add_edge("recommendation_agent", END)
        builder.add_edge("whatsapp_agent", END)
        builder.add_edge("feedback_agent", END)
        builder.add_edge("analytics_agent", END)

        return builder.compile()

    def run_interaction(self, input_state: dict) -> dict:
        return self.workflow.invoke(input_state)