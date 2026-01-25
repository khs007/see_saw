from typing  import TypedDict,Annotated,Sequence,Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages:Annotated[Sequence[BaseMessage],add_messages]
    chat_memory: str
    unstructured_context:str
    structured_context:str
    question: str
    rewrite_count: int
    user_profile: dict 
    target_profile: dict    
    target_scope: str

    #smart_budget_manager
    transaction_data: Optional[dict]  # Parsed transaction
    budget_status: Optional[dict]     # Current budget usage
    alert_message: Optional[str]      # Warning/alert if any
    finance_mode: bool     
