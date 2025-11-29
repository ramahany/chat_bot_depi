import streamlit as st
from Agents.graph import graph
import time
from Agents.state import State


sys_prompt = '''
            You are an English conversation partner.
            Your rules:
            1. NEVER correct grammar yourself.
            2. If the user's message contains grammar errors to a level where its is noticable and would cause a missunderstanding:
                → You MUST invoke the tool `get_grammar_correction`.
            3. NEVER generate corrected sentences on your own.
            4. When the tool returns the corrected sentence (don't check it wither its valid or not jsut use the output as it is):
                → Output exactly this format (do NOT modify the corrected sentence just insert it as it is in the place holder):
                It would be better to say: "<Output>"
            5. Then continue the conversation naturally in a new sentence.
            6. If the user message is already correct:
                → DO NOT call the tool.
                → Just respond naturally.
            7. You MUST follow these rules strictly.'''

state: State = { 'messages' : 
                    [{"role": "system", "content": sys_prompt}]}

def chat_page(chat_id):

    st.session_state.messages = st.session_state.db_app.get_chat(chat_id)
    st.session_state.chat_bot_msgs = st.session_state.db_app.get_chat_bot_msgs(chat_id)
    
    st.session_state.curr_chat_id = chat_id
    config ={ 'configurable': {'thread_id' : f'{st.session_state.curr_chat_id}'}}


    avatars = {
        "user" : "./icons/user.png",
        "assistant" : "./icons/assistant1.png",
        "assistant2": "./icons/assistant2.png"

    }



    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar= avatars[message["role"]]):
            st.markdown(message["content"])



    # Get user input
    if prompt := st.chat_input("Say something"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar= avatars["user"]):
            st.markdown(prompt)

        status_box = st.empty()
        final_ans = ''
        state['user_input'] =  prompt
        # Stream node-by-node updates
        for event in graph.stream(state, stream_mode="values", config=config):

            # If node updates its status, show it live
            if "status_message" in event and event["status_message"]:
                status_box.info(event["status_message"])

            # If node updates the final output field, capture it
            if "final_output" in event and event["final_output"]:
                time.sleep(1)
                final_ans = event["final_output"]
                state['status_message'] = None
        
                

        # Clear the status text once workflow completes
        status_box.empty()

        with st.chat_message("assistant", avatar=avatars["assistant"]):
            st.markdown(final_ans)
        st.session_state.chat_bot_msgs = event["messages"]

        st.session_state.messages.append({"role": "assistant", "content": final_ans})
        st.session_state.db_app.update_chat(st.session_state.curr_chat_id, st.session_state.messages, st.session_state.chat_bot_msgs)
