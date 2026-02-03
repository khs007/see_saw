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
                    ⚠️ Should ALWAYS be None to use finance credentials!
        """
        if kg_conn is None:
          
            self.kg = Neo4jGraph(
                url=os.getenv("NEO4J_URI2"),
                username=os.getenv("NEO4J_USERNAME2"),
                password=os.getenv("NEO4J_PASSWORD2")
            )
            print("[FinanceDB] ✅ Created NEW connection to finance database")
            print(f"[FinanceDB]    Connected to: {os.getenv('NEO4J_URI2')}")
        else:
          
            self.kg = kg_conn
            print("[FinanceDB] 🚨 WARNING: Using provided connection - may be wrong database!")
        
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
                print(f"[FinanceDB] ✅ Index: {index_query[:50]}...")
            except Exception as e:
                if "already exists" not in str(e).lower() and "equivalent" not in str(e).lower():
                    print(f"[FinanceDB] ⚠️ Index warning: {e}")
    
    
    def add_transaction(self, user_id: str, transaction: dict) -> bool:
        """
        Store transaction in Neo4j FINANCE database
        
        Args:
            user_id: User identifier
            transaction: Transaction dictionary with amount, category, description, etc.
            
        Returns:
            True if successful, False otherwise
        """
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
      
        transaction_date = transaction.get("date")
        
        if not transaction_date or transaction_date == "":
            transaction_date = datetime.now().isoformat()
            print(f"[FinanceDB] ⚠️ No date in transaction, using now: {transaction_date}")
        elif isinstance(transaction_date, str):
            try:
                # Parse the date string and convert to datetime
                if "T" not in transaction_date: 
                    dt = datetime.strptime(transaction_date, "%Y-%m-%d")
                    transaction_date = dt.isoformat()
                    print(f"[FinanceDB] ✅ Converted date to ISO: {transaction_date}")
            except ValueError as e:
                print(f"[FinanceDB] ⚠️ Invalid date format '{transaction_date}', using now")
                transaction_date = datetime.now().isoformat()
        
        try:
            result = self.kg.query(query, {
                "tx_id": str(uuid.uuid4()),
                "user_id": user_id,
                "amount": transaction["amount"],
                "category": transaction.get("category", "other"),
                "description": transaction["description"],
                "type": transaction.get("type", "expense"),
                "payment_mode": transaction.get("payment_mode", "unknown"),
                "date": transaction_date
            })
            
            print(f"[FinanceDB] ✅ Transaction saved:")
            print(f"  Amount: ₹{transaction['amount']}")
            print(f"  Description: {transaction['description']}")
            print(f"  Date: {transaction_date}")
            
            return True
            
        except Exception as e:
            print(f"[FinanceDB] ❌ Transaction failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def set_budget(self, user_id: str, category: str, monthly_limit: float) -> bool:
        """Set or update budget for a category in FINANCE database"""
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
            print(f"[FinanceDB] ✅ Budget: {category} = ₹{monthly_limit:,.2f}")
            return True
        except Exception as e:
            print(f"[FinanceDB] ❌ Budget failed: {e}")
            return False
    
    def verify_connection(self) -> bool:
        """Verify connection to finance database"""
        try:
            result = self.kg.query("RETURN 1 as test")
            print("[FinanceDB] ✅ Connection verified")
            return True
        except Exception as e:
            print(f"[FinanceDB] ❌ Connection failed: {e}")
            return False

_finance_db_instance = None

def get_finance_db(kg_conn=None):
    """
    Get or create FinanceDB singleton instance.
    
    ⚠️ CRITICAL: ALWAYS call without parameters!
    
    Usage:
        ✅ CORRECT: finance_db = get_finance_db()
        ❌ WRONG:   finance_db = get_finance_db(some_connection)
    
    Returns:
        FinanceDB: Singleton instance connected to NEO4J_URI2 (finance database)
    """
    global _finance_db_instance
    
    if kg_conn is not None:
        print("[get_finance_db] 🚨 WARNING: kg_conn parameter ignored!")
        print("[get_finance_db]    This may indicate a bug. Check your code.")
        print("[get_finance_db]    Finance DB should ALWAYS use its own connection.")

    if _finance_db_instance is None:
        _finance_db_instance = FinanceDB(None)
        print("[get_finance_db] ✅ Singleton created")
    
    return _finance_db_instance


def reset_finance_db():
    """
    Reset singleton instance (for testing or reconnecting).
    
    ⚠️ WARNING: This closes the current connection!
    Use only for testing or if you need to reconnect.
    """
    global _finance_db_instance
    _finance_db_instance = None
    FinanceDB._indexes_created = False  
    print("[reset_finance_db] 🔄 Singleton reset")