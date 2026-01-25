from retrieval.vector_retrieval import update_summary,add_to_vectordb
from agent.graph import app
from langchain_core.messages import HumanMessage,AIMessage


session=[]
memory_summary="Conversation just started!"
def run_agent(user_input:str):
        global memory_summary, session
        session_id = "default_session"


        # We only pass the CURRENT message. The graph pulls the rest from 'summary'
        active_history = session[-4:]
        input_state = {
            "messages": active_history+[HumanMessage(content=user_input)],
            "chat_memory": memory_summary ,
            "question":  user_input,  
            "rewrite_count": 0,        
            "structured_context": ""
        }
        
        # Invoke the graph with a recursion limit to prevent runaway loops
        res = app.invoke(input_state, config={"recursion_limit": 10})
        
        answer = res['messages'][-1].content

        # Phase 2: Update the session history
        session.append(HumanMessage(content=user_input))
        session.append(AIMessage(content=answer))

        # Phase 3: Archive logic
        if len(session) > 10:
            # 1. Archive the oldest 6 messages to VectorDB
            add_to_vectordb(session_id, session[:-4]) 
            
            # 2. Generate a new summary to replace the archived messages
            memory_summary = update_summary(memory_summary, session) 
            
            # 3. Truncate the session to keep tokens low for the next turn
            session = session[-4:]
        return {
            "answer":answer
        }
