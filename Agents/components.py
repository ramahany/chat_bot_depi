from Agents.state import State
from huggingface_hub import InferenceClient
import re, json
from tavily import TavilyClient
from Agents.Rag import Rag
import streamlit as st
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from groq import Groq
from gradio_client import Client

Hf_token = st.secrets["HF_token"]
travily_token = st.secrets["Travily_token"]
gemini_key = st.secrets["Gemini_key"]
groq_api_key = st.secrets["Groq_api_key"]
GC_mdl = Client("Hager-Mohamed/Gemma_Grammar_Correction")

@tool
def get_grammar_correction(statment: str) -> str:
    # TODO add the FT model later 
    """
    Corrects the grammar of the user's sentence.

    Input:
        statement (str): A raw user sentence that may contain grammatical errors.

    Output:
        str: The corrected version of the sentence with proper grammar.
        
    Usage:
        The LLM should call this tool when it detects the user’s input
        contains grammar mistakes or could be phrased more naturally.
        The tool returns ONLY the corrected sentence with no extra text.
    """
    raw_output = GC_mdl.predict(statment, api_name="/correct")
    res = re.sub(r"Corrected:", "", raw_output, flags=re.DOTALL).strip()
    return res

tools = [get_grammar_correction]
llm = init_chat_model("google_genai:gemini-2.0-flash", api_key = gemini_key)
llm_with_tools = llm.bind_tools(tools, enforce_tool_use=False)
groq_client = Groq(api_key=groq_api_key)

grammer_explain = Rag()
client = InferenceClient(
    api_key=Hf_token,
)

# call the model
def call_model(prompt, model_name = "HuggingFaceTB/SmolLM3-3B",  temperature=0.5, top_p = 0.5, stream = False): 
    completion = client.chat.completions.create(
    model=model_name,
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ],
    temperature= temperature,
    top_p= top_p,
    stream=stream, # send wonce finished
    )
    raw_output = completion.choices[0].message.content
    if "<think>" in raw_output:
        return re.sub(r"<think>.*?</think>", "", raw_output, flags=re.DOTALL).strip()
    return raw_output



# language classifier and intent: 
def classify_input(state:State) -> State:

    prompt = f"""
        You are a text classifier for an English practice chatbot.

        Classify the user's input based on:

        1. LANGUAGE:
        - "english": If the input is primarily in English (ignore minor grammar mistakes)
        - "arabic": If the input is primarily in Arabic

        2. INTENT:
        - "grammar_question": User is ASKING for explanation of a grammar rule, concept, or asking why something is correct/incorrect
            Examples: "Why do we use 'have been'?", "What's the difference between past simple and present perfect?", "Can you explain when to use 'a' vs 'an'?"
        
        - "fact_question": User is asking for factual information about the world, definitions, or knowledge
            Examples: "What is the capital of France?", "Who invented the telephone?", "What does 'serendipity' mean?"
        
        - "chat": User is having a conversation, sharing experiences, or making statements (even with grammar mistakes)
            Examples: "Yesterday I goes to the market", "I like pizza", "How are you?", "Tell me about your day"

        IMPORTANT:
        - Ignore grammar mistakes - they don't indicate a grammar question
        - A grammar question is ONLY when the user explicitly asks about a grammar rule or concept
        - If the user is simply speaking/writing (even incorrectly), classify as "chat"
        - If unsure between fact_question and chat, default to "chat"

        Respond in JSON ONLY (no markdown, no extra text):
        {{"language": "...", "intent": "..."}}

        User input: "{state['user_input']}"
        """

    chat_completion = groq_client.chat.completions.create(
        messages=[

            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature= 0.3,
        top_p= 0.7,
        stream= False,
        model="qwen/qwen3-32b")
    content = chat_completion.choices[0].message.content    
    if "<think>" in content:
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    try:
        res = json.loads(content)
        state["intent"], state["language"] = res["intent"], res["language"]
        if state["language"] == "arabic" : state['status_message'] = "🌐 Translator agent working..."
        
    except : 
        print("error ecured")
    
    return state


# translator agent :
def translator(state : State) -> State: 
    client = InferenceClient(
        provider="hf-inference",
        api_key=Hf_token,
    )

    result = client.translation(
    state['user_input'],
    model="Helsinki-NLP/opus-mt-ar-en",
    )
    state['translated_input'] = result.translation_text
    state["status_message"] = "🔍 Classifying your input..."

    return state


# fact search
def fact_search(state: State) -> State: 
    tavily_client = TavilyClient(api_key=travily_token)
    query = state['user_input'] if state['language'] == 'english' else state['translated_input']
    response = tavily_client.search(query=query,
                                    max_results = 1)["results"][0]
    content, url  = response["content"], response["url"] 
    state['fact_answer'] = f"""
        \n{content}\nFor more info visit {url}
    """
    
    return state

# grammar_explanation
def grammar_explanation_Rag(state: State) -> State: 
    query = state['user_input'] if state['language'] == 'english' else state['translated_input']
    state['grammar_explanation'] = grammer_explain.explain(query)
    return state
 



def chat(state: State)-> State:
    
    query = state['user_input'] if state['language'] == 'english' else state['translated_input']
    state['messages'].append({"role": "user","content": query})
    state['messages'] = [llm_with_tools.invoke(state["messages"])]
    state['chat_response'] = state["messages"][-1].content
    return state
    
# final composer # TODO lem l denya b2a w mmken guardrail 
def final_composer(state: State) -> State: 
    state['final_output'] = (
    state.get("grammar_explanation")
    or state.get("fact_answer")
    or state.get("chat_response")
    )
    state['status_message'] = "✨ Final response ready."
    return state
