from typing import Annotated, Dict, Any, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    telegram_id: str
    phone_number: Optional[str]
    current_intent: Optional[str]
    next_agent: Optional[str]
    customer_id: Optional[int]
    current_order_id: Optional[str]
    current_reservation_id: Optional[str]
    metadata: Dict[str, Any]


class IntentClassification(BaseModel):
    intent: str = Field(
        description="Must be exactly one of: 'menu_query', 'food_recommendation', 'reservation', 'place_order', 'track_order', 'feedback', or 'general_chat'"
    )
    confidence: float


class WebhookPayloadModel(BaseModel):
    telegram_id: str
    message_text: str
    phone_number: Optional[str] = None