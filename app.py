from dotenv import load_dotenv
import os
import uuid
import streamlit as st
from langchain_core.messages import HumanMessage,AIMessage
from ddgs import DDGS
load_dotenv()
from src.memory.profile_store import load_profile

from src.agent.graph import graph



st.set_page_config(page_title="Financial Advisor", page_icon=":money_with_wings:", layout="wide")
st.title("Financial Advisor :money_with_wings:")

if not os.getenv("OPENAI_API_KEY"):
    st.error("Please set the OPENAI_API_KEY environment variable.")
    st.stop()

# thread id - which conversation we are in - can be used for session management, or to link to a specific graph session
query_params = st.query_params

if "thread_id" in query_params:
    st.session_state.thread_id = query_params["thread_id"][0]
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    st.query_params["thread_id"] = st.session_state.thread_id

if "user_id" not in st.session_state:
    st.session_state.user_id = "default"

config={"configurable":{"thread_id": st.session_state.thread_id, "user_id": st.session_state.user_id}}

st.sidebar.caption(f"Chat: {st.session_state.thread_id[:8]}...")
st.sidebar.caption(f"User: {st.session_state.user_id}")
profile = load_profile(st.session_state.user_id)
if profile:
    st.sidebar.subheader("Your profile")
    st.sidebar.json(profile.model_dump(exclude_none=True))
else:
    st.sidebar.caption("No profile saved yet.")
if st.sidebar.button("New Conversation"):
    st.session_state.thread_id = str(uuid.uuid4())
    st.query_params["thread_id"] = st.session_state.thread_id
    # do NOT change user_id — long-term memory persists
    st.rerun()

#show history from checkpointer
snapshot = graph.get_state(config)
history = snapshot.values.get("messages", []) if snapshot else []

for msg in history:
    if isinstance(msg, HumanMessage):
        st.chat_message("user").write(msg.content)
    elif isinstance(msg, AIMessage):
        st.chat_message("assistant").write(msg.content) 

if prompt:=st.chat_input("Ask me anything about personal finance!"):
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        thinking = st.empty()
        thinking.write("Thinking...")
        def token_streamer():
            first_chunk = True
            for chunk, metadata in graph.stream({"messages": [HumanMessage(content=prompt)]}, config=config, stream_mode="messages"):
                if metadata.get("langgraph_node")=="chatbot" and chunk.content:
                    if first_chunk:
                        thinking.empty()
                        first_chunk = False
                    yield chunk.content
        st.write_stream(token_streamer)
    #st.rerun()