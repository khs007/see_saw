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


# Fixed: Removed curly braces from examples that were being interpreted as template variables
transaction_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are a financial transaction parser. Extract transaction details from user messages.

RULES:
- Amount is MANDATORY
- Infer category from context (e.g., "chai" → food, "auto" → transport)
- Default type is "expense" unless income keywords like "salary", "received", "credited"
- If date not mentioned, assume today
- Be smart with natural language

Examples:
"Spent 50 rupees on tea" → amount: 50, category: food, description: tea
"Auto fare 30" → amount: 30, category: transport, description: auto fare
"Bought shirt for 800" → amount: 800, category: shopping, description: shirt
"Got salary 25000" → amount: 25000, type: income, description: salary
"Paid 200 for lunch" → amount: 200, category: food, description: lunch
"""),
    ("human", "{user_message}")
])

def parse_transaction(user_message: str) -> Optional[TransactionExtract]:
    """Parse transaction from natural language"""
    chain = transaction_prompt | llm.with_structured_output(TransactionExtract)
    
    try:
        transaction = chain.invoke({"user_message": user_message})
        return transaction
    except Exception as e:
        print(f"[TransactionParser] Error: {e}")
        return None