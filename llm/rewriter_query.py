from agent.class_agent import AgentState
from langchain_groq import ChatGroq


# Rewriter function

rewriter_llm=ChatGroq(model="llama-3.1-8b-instant", temperature=0)
def rewrite_query(state: AgentState):
    print("---REWRITING QUERY---")
    history = state["messages"]
    # We use the 'question' from state which failed the previous grade
    current_query = state["question"]
    system_prompt = """You are a prompt expert for query writting. Rewrite the user's question to be 
    more effective for a Knowledge Graph and Vector search.
    - Resolve pronouns using the chat history.
    - Keep technical terms intact.
    - Output ONLY the improved search string."""

    response = rewriter_llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"History: {history}\n\nQuestion to rewrite: {current_query}"}
    ])

    state["question"] = response.content.strip()
    return state