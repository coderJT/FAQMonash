import streamlit as st
import asyncio
import playwright_setup

from source_urls_scraper import scrape_url
from url_details_scraper import scrape_pages
from clean_scraped_result import process_data
from build_index import indexing
from query_rag import evaluate  # This function should take user query as input

# UI
st.set_page_config(page_title="Monash Student Chatbot", layout="wide", page_icon="🎓")

with st.sidebar:
    st.header("💡 Suggested Questions")
    if st.button("What is the GPA formula?"):
        st.session_state.suggested_q = "What is the GPA formula?"
    if st.button("How to get a physical certificate?"):
        st.session_state.suggested_q = "How do I receive a physical degree certificate after graduating?"
    if st.button("How do I select class slots?"):
        st.session_state.suggested_q = "How do I select my class timetable for the upcoming semester?"

st.title("🎓 Monash Student Chatbot")
st.markdown("""
Ask me anything about Monash University policies!  
""")

# Session state to track conversation history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Load previous chat conversations
for message in st.session_state.chat_history:
    with st.chat_message("user" if message["role"] == "user" else "assistant"):
        st.markdown(message["text"])

# Handle input
user_input = st.chat_input("Type your question here...")

if "suggested_q" in st.session_state and st.session_state.suggested_q:
    user_input = st.session_state.suggested_q
    st.session_state.suggested_q = None

if user_input:
    with st.spinner("Thinking..."):
        st.session_state.chat_history.append({"role": "user", "text": user_input})
        
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            response = st.write_stream(evaluate(user_input, st.session_state.chat_history[:-1])) 

        st.session_state.chat_history.append({"role": "bot", "text": response})
