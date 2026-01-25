from langchain_neo4j import Neo4jGraph
from datetime import datetime
import uuid
import os

class FinanceDB:
    def __init__(self, kg_conn: Neo4jGraph = None):
        """
        Initialize FinanceDB with Neo4j connection.
        
        Args:
            kg_conn: Existing Neo4jGraph connection instance.
                    If None, creates new connection from env vars.
        """
        if kg_conn is None:
            # Create new connection
            self.kg = Neo4jGraph(
                url=os.getenv("NEO4J_URI"),
                username=os.getenv("NEO4J_USERNAME"),
                password=os.getenv("NEO4J_PASSWORD")
            )
        else:
            self.kg = kg_conn
        
        # Only create indexes once at startup, not on every request
        if not hasattr(FinanceDB, '_indexes_created'):
            self._create_indexes()
            FinanceDB._indexes_created = True
            
    def _create_indexes(self):
        """Create necessary indexes for performance"""
        indexes = [
            "CREATE INDEX user_id_idx IF NOT EXISTS FOR (u:User) ON (u.id)",
            "CREATE INDEX transaction_user_date_idx IF NOT EXISTS FOR (t:Transaction) ON (t.user_id, t.date)",
            "CREATE INDEX budget_user_category_idx IF NOT EXISTS FOR (b:Budget) ON (b.user_id, b.category)",
        ]
        
        for index_query in indexes:
            try:
                self.kg.query(index_query)
                print(f"[FinanceDB] Index created/verified: {index_query[:70]}...")
            except Exception as e:
                print(f"[FinanceDB] Index creation warning: {e}")
    
    
    def add_transaction(self, user_id: str, transaction: dict) -> bool:
        """Store transaction in Neo4j"""
        query = """
        MERGE (u:User {id: $user_id})
        CREATE (t:Transaction {
            id: $tx_id,
            user_id: $user_id,
            amount: $amount,
            category: $category,
            description: $description,
            type: $type,
            payment_mode: $payment_mode,
            date: datetime($date),
            created_at: datetime()
        })
        CREATE (u)-[:MADE_TRANSACTION]->(t)
        WITH t
        OPTIONAL MATCH (b:Budget {user_id: $user_id, category: $category})
        FOREACH (_ IN CASE WHEN b IS NOT NULL THEN [1] ELSE [] END |
            CREATE (t)-[:BELONGS_TO]->(b)
        )
        RETURN t.id as transaction_id
        """
        
        try:
            result = self.kg.query(query, {
                "tx_id": str(uuid.uuid4()),
                "user_id": user_id,
                "amount": transaction["amount"],
                "category": transaction.get("category", "other"),
                "description": transaction["description"],
                "type": transaction.get("type", "expense"),
                "payment_mode": transaction.get("payment_mode", "unknown"),
                "date": transaction.get("date", datetime.now().isoformat())
            })
            return True
        except Exception as e:
            print(f"[FinanceDB] Error adding transaction: {e}")
            return False
    
    def set_budget(self, user_id: str, category: str, monthly_limit: float) -> bool:
        """Set or update budget for a category"""
        query = """
        MERGE (u:User {id: $user_id})
        MERGE (b:Budget {user_id: $user_id, category: $category})
        ON CREATE SET b.created_at = datetime()
        SET b.monthly_limit = $monthly_limit,
            b.currency = 'INR',
            b.updated_at = datetime()
        MERGE (u)-[:HAS_BUDGET]->(b)
        RETURN b
        """
        
        try:
            self.kg.query(query, {
                "user_id": user_id,
                "category": category.lower(),
                "monthly_limit": monthly_limit
            })
            return True
        except Exception as e:
            print(f"[FinanceDB] Error setting budget: {e}")
            return False


# Singleton pattern for connection reuse
_finance_db_instance = None

def get_finance_db(kg_conn=None):
    """Get or create FinanceDB singleton instance"""
    global _finance_db_instance
    if _finance_db_instance is None:
        _finance_db_instance = FinanceDB(kg_conn)
    return _finance_db_instance