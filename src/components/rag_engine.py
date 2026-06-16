import os
from dotenv import load_dotenv
load_dotenv(override=False)

import chromadb
from chromadb.utils import embedding_functions

class RestaurantMenuRAGEngine:
    """Handles vector index caching and semantic search queries for the menu."""
    
    def __init__(self):
        self.db_path = os.getenv("CHROMA_DB_PATH", os.path.join(os.getcwd(), "restaurant_db"))
        self.collection_name = "restaurant_menu_faq"
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function
        )
        self._seed_initial_menu_data()

    def _seed_initial_menu_data(self) -> None:
        """Seeds default menu choices into storage if it is empty."""
        if self.collection.count() > 0:
            return

        print("ℹ️ Seeding initial restaurant menu records...")
        sample_dishes = [
            "Paneer Pizza - Premium cottage cheese with capsicum, onions, and extra mozzarella. Price: ₹299. Category: Vegetarian.",
            "Veg Burger - Crispy mixed vegetable patty with lettuce, tomatoes, and creamy mayo cheese sauce. Price: ₹120. Category: Vegetarian.",
            "Cheese French Fries - Loaded with liquid cheddar cheese. Price: ₹150. Category: Vegetarian.",
            "Margherita Pizza - Classic tomato base with fresh basil leaves and double mozzarella. Price: ₹249. Category: Vegetarian.",
            "Coke / Coca Cola - Refreshing chilled carbonated soft drink. Price: ₹40. Category: Beverage.",
            "Paneer Burger - Spicy tandoori dressing and fresh onions. Price: ₹160. Category: Vegetarian."
        ]
        sample_ids = [f"dish_{i}" for i in range(len(sample_dishes))]
        sample_metadata = [{"source": "seeded_menu"} for _ in sample_dishes]
        
        self.collection.add(
            documents=sample_dishes,
            ids=sample_ids,
            metadatas=sample_metadata
        )
        print(f"✅ Loaded {self.collection.count()} items into the vector store.")

    def query_menu_records(self, user_query: str, max_results: int = 3) -> str:
        """Finds closest matching food items using vector similarity search."""
        try:
            results = self.collection.query(
                query_texts=[user_query],
                n_results=max_results
            )
            
            if not results or 'documents' not in results or not results['documents'][0]:
                return "No matching records found on our active menu catalog right now."
            
            return "\n".join([f"- {doc}" for doc in results['documents'][0]])
            
        except Exception as e:
            print(f"❌ Error inside RAG querying pipeline: {e}")
            return "An error occurred while searching through our active menu archives."