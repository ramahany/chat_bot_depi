import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import streamlit as st
from datetime import datetime
import random
import string
from langchain_core.messages import messages_to_dict, messages_from_dict, SystemMessage
from langchain_core.messages import (
    BaseMessage, SystemMessage, AIMessage, HumanMessage
)

class DataBase: 
    chat_bot_sys_prompt = '''
            You are an English conversation partner.
            Your rules:
            1. NEVER correct grammar yourself.
            2. If the user's message contains grammar errors to a level where its is noticable and would cause a missunderstanding:
                → You MUST invoke the tool `get_grammar_correction`.
            3. NEVER generate corrected sentences on your own.
            4. When the tool returns the corrected sentence:
                → Output exactly this format (do NOT modify the corrected sentence just insert it as it is in the place holder):
                It would be better to say: "<Output>"
            5. Then continue the conversation naturally in a new sentence.
            6. If the user message is already correct:
                → DO NOT call the tool.
                → Just respond naturally.
            7. You MUST follow these rules strictly.'''

    def __init__(self):
        cred = credentials.Certificate(dict(st.secrets["FIREBASE_KEY"]))
        try:
            st.session_state.app = firebase_admin.get_app()
        except ValueError as e:
            st.session_state.app = firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        self.current_user = None
        self.chats = None

    def ensure_lc_message(self, m):
        if isinstance(m, BaseMessage):
            return m
        
        # If it's a dict: convert manually
        if isinstance(m, dict) and "role" in m:
            if m["role"] == "system":
                return SystemMessage(content=m["content"])
            if m["role"] == "user":
                return HumanMessage(content=m["content"])
            if m["role"] == "assistant":
                return AIMessage(content=m["content"])
            raise ValueError(f"Unknown role: {m}")

        raise ValueError(f"Invalid message type: {m}")


    def check_valid_user(self, username_, password_):
        doc_ref = self.db.collection("users").document(username_)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict() # only the main data doesn't get the chats collection
            if password_ == data['password']:
                self.current_user = username_
                self.chats = doc_ref.collection("chats")
                st.session_state.user_id = username_
                st.session_state.user_data = data
                st.session_state.user_chats = self.chats.get()
                st.session_state.state = "hello"
                return True
            else:
                st.error("invalid password")
        else:
            st.error("invalid username")
        return False

    def sign_up(self, username, name, password): 
        data = {
            "name": name,
            "password": password,
        }

        if self.db.collection("users").where(filter=FieldFilter("name", "==", username)).get():
            st.error("Invalid username")
            return False
        else:
            try:
                self.db.collection("users").document(username).set(data)
                self.current_user = username
                ref = self.db.collection("users").document(username)
                self.chats  = ref.collection("chats").document(self.generate_unique_id())
                self.chats.set({
                    "title": "first chat",
                    "chat_bot_hist":messages_to_dict([SystemMessage(content=self.chat_bot_sys_prompt)]),
                    "hist": []
                },  merge=True )
                self.chats = ref.collection("chats")
                st.session_state.user_chats = self.chats.get()
                st.session_state.user_id = username
                st.session_state.user_data = data
                st.session_state.state = "hello"
                return True
            except ValueError:
                st.error("An error occurred please try again!")
                return False


    def get_chat(self, id):
        return self.chats.document(id).get().to_dict()["hist"]
    
    def get_chat_bot_msgs(self, id):
        msgs = self.chats.document(id).get().to_dict()["chat_bot_hist"]
        return messages_from_dict(msgs)
    
    
    def add_chat(self, title = "New Chat"):
       
        chats = self.chats.document(self.generate_unique_id())
        chats.set({
            "title": title,
            "chat_bot_hist": messages_to_dict([SystemMessage(content=self.chat_bot_sys_prompt)]),
            "hist": []
        },  merge=True )
        st.session_state.user_chats = self.chats.get()
    
    def update_chat(self, chat_id, chat , chat_bot_hist):
        chats = self.chats.document(chat_id)
        fixed = []
        for m in chat_bot_hist:
            if hasattr(m, "model_dump"):
                fixed.append(m)
            else:
                # Convert dict → LC Message
                fixed.append(self.ensure_lc_message(m))

        safe_messages = messages_to_dict(fixed)
        # print(safe_messages)
        # print("\n\n", chat, "\n\n")

        chats.set({
            "chat_bot_hist":safe_messages,
            "hist": chat
        },  merge=True )
        
    

    # generate new id for each chat
    def generate_unique_id(self,length=11):
        """Generate a unique ID consisting of uppercase, lowercase letters, and digits."""
        characters = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
        unique_id = ''.join(random.choices(characters, k=length))
        return unique_id

        