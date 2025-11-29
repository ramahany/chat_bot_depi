
import streamlit as st
from widgets import  login, logout, add_chat
from pages.mainpage import chat_page

# initial state
if "state" not in st.session_state:
    st.session_state.state = "logging in"


# for now only the log in and signup page: 
if st.session_state.state == "logging in" or st.session_state.state == "signing up": 
    pg = st.navigation([st.Page(login)])
else : 
    pages = []
    for doc in st.session_state.user_chats: 
        pages.append(
            st.Page(lambda doc_id=doc.id: chat_page(doc_id)
            , title=str(doc.to_dict()["title"]),  url_path=f"chat_{doc.id}" ))



    pages.append(st.Page(logout,  title="Logout", icon=":material/logout:"))
    pg = st.navigation(pages)
    
    # Adding new chat
    new_chat_title = st.sidebar.text_input(label="New Chat title", max_chars = 15)
    if new_chat_title: 
        btn_state = False
    else :
        btn_state = True
    
    st.sidebar.button("Add New Chat!", on_click=lambda title=new_chat_title: add_chat(title=title), type = 'secondary', disabled=btn_state)


pg.run()