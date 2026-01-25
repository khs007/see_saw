from retrieval.vector_retrieval import update_summary, add_to_vectordb
from agent.graph import app
from langchain_core.messages import HumanMessage, AIMessage
from typing import Dict, Any

# Session management (in production, use Redis/database)
sessions = {}  # {user_id: {"session": [], "memory": ""}}


def get_session(user_id: str):
    """Get or create session for user"""
    if user_id not in sessions:
        sessions[user_id] = {
            "session": [],
            "memory": "Conversation just started!"
        }
    return sessions[user_id]


def run_agent(user_input: str, user_id: str = "default_user") -> Dict[str, Any]:
    """
    Run the RAG agent for government schemes queries.
    
    Args:
        user_input: User's query
        user_id: User identifier for session management
        
    Returns:
        Dictionary with answer and metadata
    """
    session_data = get_session(user_id)
    session = session_data["session"]
    memory_summary = session_data["memory"]
    
    # Prepare input state with recent context
    active_history = session[-4:]
    input_state = {
        "messages": active_history + [HumanMessage(content=user_input)],
        "chat_memory": memory_summary,
        "question": user_input,
        "rewrite_count": 0,
        "structured_context": "",
        "unstructured_context": "",
        "user_profile": {},
        "target_profile": {},
        "target_scope": "generic"
    }
    
    # Invoke the graph
    try:
        res = app.invoke(input_state, config={"recursion_limit": 10})
        answer = res['messages'][-1].content
    except Exception as e:
        print(f"[RunAgent] Error: {e}")
        answer = "I apologize, I encountered an error processing your request. Please try again."
    
    # Update session history
    session.append(HumanMessage(content=user_input))
    session.append(AIMessage(content=answer))
    
    # Archive logic
    if len(session) > 10:
        # Archive oldest messages to VectorDB
        add_to_vectordb(user_id, session[:-4])
        
        # Generate new summary
        memory_summary = update_summary(memory_summary, session)
        session_data["memory"] = memory_summary
        
        # Keep only recent messages
        session_data["session"] = session[-4:]
    else:
        session_data["session"] = session
    
    return {
        "answer": answer,
        "type": "schemes",
        "user_profile": res.get("user_profile", {}),
        "target_scope": res.get("target_scope", "generic")
    }