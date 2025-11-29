# state.py
from typing import Optional, TypedDict, Annotated
from langgraph.graph.message import add_messages

class State(TypedDict):
    user_input: str
    messages : Annotated[list, add_messages]
    
    language: str = None
    intent: str = None
    status_message : str = None # indcate current state 
    translated_input: Optional[str] = None

    # resoponses
    grammar_explanation: Optional[str] = None
    fact_answer: Optional[str] = None
    chat_response : Optional[str] = None

    # final response
    final_output: str = None
