from Agents.components import classify_input, translator, fact_search, grammar_explanation_Rag, chat, final_composer, tools
from langgraph.graph import StateGraph, START, END
from Agents.state import State
from langgraph.prebuilt import ToolNode, tools_condition

from langgraph.checkpoint.memory import InMemorySaver

memory = InMemorySaver()

# initial node 
def init_node(state):
    # Modify whatever you want
    # Reset fields that should not persist between turns
    state['status_message'] = "🔍 Classifying your input..."
    state['intent'] = None  # Reset intent
    state['language'] = None  # Reset language
    state['translated_input'] = None  # Reset translation if you have it
    # resoponses
    state['grammar_explanation'] = None
    state['fact_answer'] = None
    state['chat_response'] = None

    # final response
    state['final_output'] = None
    # Keep chat_history intact - don't reset it
    return state


# check point 
def check_point(state:State) -> State: 
    if state["intent"] == "chat":
        state['status_message'] = "💬 Chat agent generating natural reply..."

    elif state["intent"] == "grammar_question":
        state['status_message'] = "🧩 Grammar explanation agent preparing answer... \n\n 📚 RAG agent retrieving knowledge..."
        
    elif state["intent"] == "fact_question":
        state['status_message'] = "🔎 Fact agent performing web search..."


    return state

# conditional functions 
def detect_lang(state:State) -> str: 
    
    return state['language']

def detect_intent(state:State) -> str: 
    return state['intent']

# init builder 
builder = StateGraph(State)

# add nodes 
builder.add_node("init_node", init_node)
builder.add_node("classify_input_node", classify_input)
builder.add_node("translator_node", translator)
builder.add_node("intent_classifier_cb_node", check_point)

# nodes for intent
builder.add_node("fact_search_node", fact_search)
builder.add_node("grammar_explanation_Rag_node", grammar_explanation_Rag)
builder.add_node("chat_response_node", chat) # we will have the grammer correction as a tool here
builder.add_node("tools", ToolNode(tools))

# final_composer node
builder.add_node("final_composer_node", final_composer)

# add edges
builder.add_edge(START, "init_node")
builder.add_edge("init_node", "classify_input_node")
builder.add_conditional_edges(
    "classify_input_node", 
    detect_lang , 
    {
        
        'arabic' : 'translator_node',
        'english': "intent_classifier_cb_node",
        
    } )

builder.add_edge("translator_node", "intent_classifier_cb_node")
builder.add_conditional_edges(
    "intent_classifier_cb_node",
    detect_intent,
      {
          "fact_question" : "fact_search_node",
          "grammar_question" : "grammar_explanation_Rag_node",
          "chat" : "chat_response_node" 
      }
    )
builder.add_edge("fact_search_node", "final_composer_node")
builder.add_edge("chat_response_node", "final_composer_node")
builder.add_edge("grammar_explanation_Rag_node", "final_composer_node")

# chat bot tools 
builder.add_conditional_edges("chat_response_node", tools_condition,  {
        "tools": "tools",         # if tool call detected
        "default": "final_composer_node", # if NO tool call
        "__end__": "final_composer_node"
    })
builder.add_edge("tools", "chat_response_node")

builder.add_edge("final_composer_node", END)


graph = builder.compile(checkpointer=memory)

# ## get graph img:
# png_bytes = graph.get_graph().draw_mermaid_png()

# with open("graph.png", "wb") as f:
#     f.write(png_bytes)

# print("Saved as graph.png")
