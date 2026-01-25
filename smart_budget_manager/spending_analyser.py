# finance/spending_analyzer.py

from datetime import datetime, timedelta
from langchain_neo4j import Neo4jGraph

class SpendingAnalyzer:
    def __init__(self, kg_conn: Neo4jGraph):
        self.kg = kg_conn
    
    def get_monthly_spending(self, user_id: str, category: str = None) -> dict:
        """Get current month spending"""
        query = """
        MATCH (u:User {id: $user_id})-[:MADE_TRANSACTION]->(t:Transaction)
        WHERE t.type = 'expense'
          AND datetime(t.date) >= datetime($start_date)
          AND datetime(t.date) <= datetime($end_date)
          AND ($category IS NULL OR t.category = $category)
        RETURN 
            COALESCE(t.category, 'other') as category,
            sum(t.amount) as total_spent,
            count(t) as transaction_count
        """
        
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        
        result = self.kg.query(query, {
            "user_id": user_id,
            "category": category,
            "start_date": start_of_month.isoformat(),
            "end_date": now.isoformat()
        })
        
        return result
    
    def check_budget_status(self, user_id: str) -> dict:
        """Check budget usage across all categories"""
        query = """
        MATCH (u:User {id: $user_id})-[:HAS_BUDGET]->(b:Budget)
        OPTIONAL MATCH (t:Transaction)-[:BELONGS_TO]->(b)
        WHERE t.type = 'expense'
          AND datetime(t.date) >= datetime($start_date)
        WITH b, sum(COALESCE(t.amount, 0)) as spent
        RETURN 
            b.category as category,
            b.monthly_limit as budget,
            spent as spent,
            (spent / b.monthly_limit * 100) as usage_percent
        ORDER BY usage_percent DESC
        """
        
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        
        result = self.kg.query(query, {
            "user_id": user_id,
            "start_date": start_of_month.isoformat()
        })
        
        return result