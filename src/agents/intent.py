import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from src.schema.schema import AgentState, IntentClassification

# Force-load environment variables right at the module import step
load_dotenv()

class IntentAgent:
    """Classifies user input into predefined restaurant system intents."""
    
    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name=os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile"),
            temperature=0.0
        )
        # Force structured output using the Pydantic schema
        self.structured_llm = self.llm.with_structured_output(IntentClassification)

    def classify(self, state: AgentState) -> dict:
        """Extracts intent from the last user message and updates state."""
        user_msg = state["messages"][-1].content

        system_prompt = (
            "You are an AI intent classifier for a restaurant concierge bot.\n"
            "Analyze the user message and select the most appropriate intent category.\n"
            "Do not guess or create new categories outside the provided schema choices."
        )

        result = self.structured_llm.invoke([
            ("system", system_prompt),
            ("user", user_msg)
        ])

        return {
            "current_intent": result.intent,
            "metadata": {"intent_confidence": result.confidence}
        }