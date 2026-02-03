from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_chroma import Chroma
from agent.class_agent import AgentState
from langchain_core.messages import HumanMessage,AIMessage
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os

load_dotenv()

def get_llm():
     return ChatGroq(model="llama-3.1-8b-instant",temperature=0)

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    task_type="retrieval_document",
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

try:
    
    scheme_vector_store = Chroma(
    persist_directory="./scheme_vector_db",
    collection_name="schemes",
    embedding_function=embeddings
    )
    
    chat_memory_store = Chroma(
    persist_directory="./chat_memory_db",
    collection_name="chat_memory",
    embedding_function=embeddings
    )
except Exception as e:
        print(f"Error setting up DB: {str(e)}")
        raise


###        VECTOR DATABSE RELATED SEARCH        ###

import uuid
import datetime

### ADD CHAT HISTORY(SESSION) IN DATABSE ###
def add_to_vectordb(session_id,session_list):
    """Takes session list which gets out of sliding window and add to our database."""
    formatted_txt="\n".join( f"{msg.type}:{msg.content}" for msg in session_list )
    mem_id=str(uuid.uuid4())
    chat_memory_store.add_texts(
        texts=[formatted_txt],
        ids=[mem_id],
        metadatas=[{
            "session_id":session_id,
            "timestamp":datetime.datetime.now().isoformat(),
            "type":"chat_chunk"
        }]
    )    


### RETRIEVE FROM DATABASE PAST CONTEXT ###
def retrieve_scheme_context(state: AgentState):
       
        user_input = state["messages"][-1].content

        docs=scheme_vector_store.similarity_search(user_input,k=2)
        unstructured_context="\n---\n".join([doc.page_content for doc in docs])
        
        state["unstructured_context"] = unstructured_context
        return state

## UPDATE SUMMARY TAKES OLD SUMMARY AND NEW CHAT HISTORY AND UPDATE ###
def update_summary(old_memory:str,update_context:list)->str:
    """Updates conversation summary using a LLM.
     Args:
        old_memory: Previous summary of the conversation
        update_context: Recent messages to incorporate into summary
        
    Returns:
        Updated summary string
    """
    summary_llm=ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.3
    )
    
    recent_context = ""
    for msg in update_context:  
        if isinstance(msg, HumanMessage):
            recent_context += f"User: {msg.content}\n"
        elif isinstance(msg, AIMessage):
            recent_context += f"Assistant: {msg.content[:200]}\n"  

    prompt_llm=f"""You are a conversation summarizer. 
    PREVIOUS SUMMARY: {old_memory}
    
    NEW RECENT CHAT:
    {recent_context}

    Create a NEW summary that takes important features from previous summary and add them to new summary:
    1. User preferences,facts about user
    1. Captures the main topic the user is learning
    2. Notes key questions asked and concepts covered
    3. Identifies any struggles or confusion points
    4. Keeps track of what the student has accomplished
    5. Maximum 3-4 sentences
    """
    try:
        new_response=summary_llm.invoke([HumanMessage(content=prompt_llm)])
       
        return new_response.content.strip()
            
    except Exception as e:
            print(f" Summary update failed: {e}")
            return old_memory