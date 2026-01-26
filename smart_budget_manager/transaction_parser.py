from pydantic import BaseModel, Field
from typing import Optional, Literal
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from datetime import datetime

# Extract transaction details
class TransactionExtract(BaseModel):
    """Schema for extracting transaction details from chat"""
    amount: float = Field(..., description="Transaction amount in INR")
    category: Optional[str] = Field(None, description="Expense category: food, transport, entertainment, shopping, bills, health, education, other")
    description: str = Field(..., description="Brief description of transaction")
    type: Literal["expense", "income"] = Field("expense", description="Transaction type")
    payment_mode: Optional[str] = Field(None, description="Payment method: cash, upi, card, netbanking")
    date: Optional[str] = Field(None, description="Transaction date if mentioned, format: YYYY-MM-DD")


llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)


transaction_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are a financial transaction parser. Extract transaction details from user messages.

RULES:
- Amount is MANDATORY
- Infer category from context using these mappings:
  * FOOD: tea, coffee, chai, lunch, dinner, breakfast, snacks, restaurant, food, meal, pizza, burger
  * TRANSPORT: auto, taxi, uber, ola, bus, train, metro, petrol, diesel, fuel, cab
  * SHOPPING: clothes, shirt, shoes, dress, shopping, mall, online shopping, amazon, flipkart
  * ENTERTAINMENT: movie, cinema, netflix, game, gaming, concert, party
  * BILLS: electricity, water, rent, internet, wifi, phone bill, recharge
  * HEALTH: doctor, medicine, hospital, clinic, pharmacy, medical
  * EDUCATION: book, course, tuition, fees, school, college
  * OTHER: anything else

- Default type is "expense" unless income keywords like "salary", "received", "credited"
- **IMPORTANT**: For date field:
  * If user mentions specific date (e.g., "yesterday", "on 15th", "last Monday") → extract it
  * If NO date mentioned → return null (NOT today's date)
  * Let the backend handle default date assignment
- Be smart with natural language

Examples:
"Spent 50 rupees on tea" → amount: 50, category: food, description: tea, date: null
"Auto fare 30" → amount: 30, category: transport, description: auto fare, date: null
"Bought shirt for 800 yesterday" → amount: 800, category: shopping, description: shirt, date: <yesterday's date>
"Got salary 25000" → amount: 25000, type: income, description: salary, date: null
"Paid 200 for lunch on 20th" → amount: 200, category: food, description: lunch, date: "2025-01-20"
"""),
    ("human", "{user_message}")
])

def parse_transaction(user_message: str) -> Optional[TransactionExtract]:
    """
    Parse transaction from natural language.
    
    Args:
        user_message: User's natural language transaction description
        
    Returns:
        TransactionExtract object or None if parsing fails
    """
    chain = transaction_prompt | llm.with_structured_output(TransactionExtract)
    
    try:
        transaction = chain.invoke({"user_message": user_message})
        
        # ✅ CRITICAL FIX: Set current date if LLM didn't provide one
        if not transaction.date:
            transaction.date = datetime.now().strftime("%Y-%m-%d")
            print(f"[TransactionParser] ⚠️ No date in query, using today: {transaction.date}")
        
        # Log parsed details
        print(f"[TransactionParser] ✅ Parsed transaction:")
        print(f"  Amount: ₹{transaction.amount}")
        print(f"  Category: {transaction.category}")
        print(f"  Description: {transaction.description}")
        print(f"  Date: {transaction.date}")
        
        return transaction
        
    except Exception as e:
        print(f"[TransactionParser] ❌ Error: {e}")
        return None