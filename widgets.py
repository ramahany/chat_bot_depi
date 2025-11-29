
import streamlit as st
from functions import DataBase

def login():
    st.session_state.db_app = DataBase()

    if st.session_state.state == "logging in":

        st.title("Welcome to our English Learning Chatbot")
        st.header("Login:")
        username = st.text_input(label="User or Email:", value="")
        password = st.text_input(label="password:", value="", type="password")

        if st.button(label="login", type="primary"):
            if st.session_state.db_app.check_valid_user(username, password):
                st.rerun()
        if st.button(label="Create account", type="tertiary"):
            st.session_state.state = "signing up"
            st.rerun()

    if st.session_state.state == "signing up":
        st.title("Welcome to our English Learning Chatbot")
        st.header("Signup:")
        username = st.text_input(label="User_name or Email:", value="")
        name = st.text_input(label="name", value="")
        password = st.text_input(label="password:", value="", type="password")

        if st.button(label="signup", type="primary") and username != '' and password != '' and name != '':
            if st.session_state.db_app.sign_up(username, name, password):
                st.rerun()

        if st.button(label="already have an account?", type="tertiary"):
            st.session_state.state = "logging in"
            st.rerun()

def logout(): 
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()   

def add_chat(title:str):

    st.session_state.db_app.add_chat(title = title)
