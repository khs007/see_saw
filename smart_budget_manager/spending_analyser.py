# smart_budget_manager/spending_analyser.py

from datetime import datetime, timedelta
from langchain_neo4j import Neo4jGraph

class SpendingAnalyzer:
    def __init__(self, kg_conn: Neo4jGraph):
        """
        Initialize SpendingAnalyzer with Neo4j connection.
        
        Args:
            kg_conn: Neo4jGraph connection to FINANCE database
                     (NOT the schemes database!)
        """
        self.kg = kg_conn
        print(f"[SpendingAnalyzer] ✅ Initialized with connection: {type(kg_conn)}")
    
    def get_monthly_spending(self, user_id: str, category: str = None) -> list:
        """
        Get current month spending
        
        Returns:
            List of dicts with spending by category
        """
        # ✅ FIXED: Proper date filtering with NULL handling
        query = """
        MATCH (u:User {id: $user_id})-[:MADE_TRANSACTION]->(t:Transaction)
        WHERE t.type = 'expense'
          AND t.date IS NOT NULL
          AND t.date >= datetime($start_date)
          AND t.date <= datetime($end_date)
          AND ($category IS NULL OR t.category = $category)
        WITH COALESCE(t.category, 'other') as category, t.amount as amount
        RETURN 
            category,
            sum(amount) as total_spent,
            count(amount) as transaction_count
        ORDER BY total_spent DESC
        """
        
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        
        try:
            # Debug: Check total transactions first
            debug_query = """
            MATCH (u:User {id: $user_id})-[:MADE_TRANSACTION]->(t:Transaction)
            RETURN count(t) as total_count, 
                   count(CASE WHEN t.date IS NULL THEN 1 END) as null_dates,
                   min(t.date) as earliest,
                   max(t.date) as latest
            """
            debug_result = self.kg.query(debug_query, {"user_id": user_id})
            if debug_result and debug_result[0]:
                dr = debug_result[0]
                print(f"[SpendingAnalyzer] 🔍 Total: {dr.get('total_count', 0)} | Null dates: {dr.get('null_dates', 0)}")
                print(f"[SpendingAnalyzer] 🔍 Date range: {dr.get('earliest')} to {dr.get('latest')}")
                print(f"[SpendingAnalyzer] 🔍 Filtering: {start_of_month.isoformat()} to {now.isoformat()}")
            
            # Run actual query
            result = self.kg.query(query, {
                "user_id": user_id,
                "category": category,
                "start_date": start_of_month.isoformat(),
                "end_date": now.isoformat()
            })
            
            print(f"[SpendingAnalyzer] ✅ Found {len(result)} spending categories for user {user_id}")
            if result:
                for item in result:
                    print(f"[SpendingAnalyzer]    {item['category']}: ₹{item['total_spent']:.2f}")
            return result
            
        except Exception as e:
            print(f"[SpendingAnalyzer] ❌ Query failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def check_budget_status(self, user_id: str) -> list:
        """
        Check budget usage across all categories
        
        Returns:
            List of dicts with budget status by category
        """
        # ✅ SIMPLIFIED: Remove complex date filtering for now
        query = """
        MATCH (u:User {id: $user_id})-[:HAS_BUDGET]->(b:Budget)
        OPTIONAL MATCH (u)-[:MADE_TRANSACTION]->(t:Transaction)
        WHERE t.category = b.category 
          AND t.type = 'expense'
        WITH b, sum(COALESCE(t.amount, 0)) as spent
        RETURN 
            b.category as category,
            b.monthly_limit as budget,
            spent as spent,
            (spent / b.monthly_limit * 100) as usage_percent
        ORDER BY usage_percent DESC
        """
        
        try:
            result = self.kg.query(query, {"user_id": user_id})
            
            print(f"[SpendingAnalyzer] ✅ Budget status check complete for user {user_id}")
            if result:
                for item in result:
                    print(f"[SpendingAnalyzer]    {item['category']}: ₹{item['spent']:.2f} / ₹{item['budget']:.2f} ({item['usage_percent']:.1f}%)")
            return result
            
        except Exception as e:
            print(f"[SpendingAnalyzer] ❌ Budget check failed: {e}")
            import traceback
            traceback.print_exc()
            return []