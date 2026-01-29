from langchain_neo4j import Neo4jGraph
from typing import List, Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_neo4j.vectorstores.neo4j_vector import remove_lucene_chars
from agent.class_agent import AgentState
from langchain_core.messages import HumanMessage, AIMessage
import os
load_dotenv()

_kg_conn = None
_kg_initialized = False

def get_kg_conn() -> Neo4jGraph:
    """Get or create Knowledge Graph connection (lazy)"""
    global _kg_conn
    
    if _kg_conn is None:
        _kg_conn = Neo4jGraph(
            url=os.getenv("NEO4J_URI"),
            username=os.getenv("NEO4J_USERNAME"),
            password=os.getenv("NEO4J_PASSWORD"),
        )
        print("[KG] ✅ Connection established")
    
    return _kg_conn

def initialize_kg_if_needed():
    """
    Initialize KG ONLY on first use (not at import time)
    
    This is called by structured_retriever() when needed
    """
    global _kg_initialized
    
    if _kg_initialized:
        return  
    
    try:
        kg = get_kg_conn()
        
        kg.query("""
        CREATE FULLTEXT INDEX entity_name_index IF NOT EXISTS 
        FOR (n:Entity) ON EACH [n.name]
        """)
        
        print("[KG] ✅ Indexes created/verified")
        _kg_initialized = True
        
    except Exception as e:
        print(f"[KG] ⚠️ Initialization failed: {e}")


class KnowledgeConcept(BaseModel):
    """Schema for extracting entities"""
    names: List[str] = Field(
        ...,
        min_items=1,
        max_items=5,
        description="Extract at most 5 core concepts"
    )

class UserProfile(BaseModel):
    age: Optional[int] = None
    income: Optional[int] = None
    state: Optional[str] = None
    category: Optional[str] = None
    occupation: Optional[str] = None

llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)

profile_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You extract user profile information for government scheme eligibility.

STRICT RULES:
- Extract ONLY information explicitly stated by the user.
- DO NOT guess, infer, or assume values.
- If a value is unclear or approximate, return null.
- Use numeric values where applicable (e.g., income in INR).
- State names should be full (e.g., Uttar Pradesh, not UP).

Return ONLY structured data in the specified format.
"""),
    ("human", "Recent Messages:\n{recent_messages}")
])

entity_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are extracting objects and entities from the text."),
    ("human", "Use the given format to extract information from the following input:{question}"),
])

def detect_target_scope(text: str) -> str:
    """Detect if query is about self, other, or generic"""
    t = text.lower()
    
    if any(x in t for x in ["for me", "i am", "my eligibility", "am i eligible"]):
        return "self"
    
    if any(x in t for x in ["my father", "my mother", "my friend", "someone else", "for a "]):
        return "other"
    
    if any(x in t for x in ["eligible", "subsidy", "which scheme", "loan", "benefit"]):
        return "unclear"
    
    return "generic"


def extract_user_profile(state: AgentState) -> AgentState:
    """Extract user profile from conversation"""
    messages = state.get("messages", [])
    recent_msgs = []
    
    for m in messages[-4:]:
        if isinstance(m, HumanMessage):
            recent_msgs.append(m.content)
    
    recent_messages_text = "\n".join(recent_msgs)
    target_scope = detect_target_scope(recent_messages_text)
    
    chain = profile_prompt | llm.with_structured_output(UserProfile)
    
    try:
        extracted: UserProfile = chain.invoke({
            "recent_messages": recent_messages_text
        })
        extracted_profile = extracted.model_dump(exclude_none=True)
    except Exception as e:
        print(f"[ProfileExtractor] Failed: {e}")
        extracted_profile = {}
    
    if target_scope == "self":
        state["user_profile"] = extracted_profile
        state["target_profile"] = extracted_profile
        state["target_scope"] = "self"
    elif target_scope == "other":
        state["target_profile"] = extracted_profile
        state["target_scope"] = "other"
    else:
        state["target_profile"] = {}
        state["target_scope"] = "generic"
    
    return state

def generate_full_query(input: str) -> str:
    """Generate Lucene query from input"""
    full_query = ""
    words = [el for el in remove_lucene_chars(input).split() if el]
    
    for word in words[:-1]:
        full_query += f"{word}~2 AND "
    full_query += f"{words[-1]}~2"
    
    return full_query.strip()

def structured_retriever(state: AgentState) -> AgentState:
    """
    Retrieve from Knowledge Graph
    
    FIXED: Now initializes KG lazily on first use
    """
    # Check if unclear scope
    if state.get("target_scope") == "unclear":
        state["structured_context"] = ""
        state["messages"].append(
            AIMessage(content=(
                "Scheme eligibility depends on who the beneficiary is. "
                "Should I check this for you, or for someone else?"
            ))
        )
        return state
    
    question = state.get("question", "")
    if not question.strip():
        state["structured_context"] = ""
        return state
    
    initialize_kg_if_needed()
    
    kg = get_kg_conn()
    kg_query = generate_full_query(question)
    result = ""
    
    try:
        response = kg.query(
            """
            CALL db.index.fulltext.queryNodes('entity_name_index', $query, {limit: 3})
            YIELD node, score
            OPTIONAL MATCH (node)-[r]->(neighbor)
            WHERE neighbor IS NOT NULL AND type(r) <> 'MENTIONS'
            RETURN
                coalesce(node.name, node.id, 'UNKNOWN') AS entity,
                collect(DISTINCT type(r)) AS relations
            LIMIT 10
            """,
            {"query": kg_query}
        )
        
        for row in response:
            result += f"- Entity: {row['entity']}\n"
            if row["relations"]:
                result += f"  Related via: {', '.join(row['relations'])}\n"
    
    except Exception as e:
        print(f"[KG Error]: {e}")
        result = ""

    state["structured_context"] = result.strip()
    return state