from dotenv import load_dotenv
import os
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage,ToolMessage
from ddgs import DDGS

load_dotenv()

@tool
def web_search(query: str) -> str:
    """ Search the web for current Indian mutual fund info, debt funds, RBI rates, and market news. Use this when the user asks about funds, investments, or current financial data. """
    results = []
    for r in DDGS().text(query, region="in-en", max_results=5):
        results.append(f"{r['title']}: {r['href']}")
    return "\n".join(results)

# map tools to their implementations
tools_by_name = {
    "web_search": web_search
}





st.set_page_config(page_title="Financial Advisor", page_icon=":money_with_wings:", layout="wide")
st.title("Financial Advisor :money_with_wings:")

if not os.getenv("OPENAI_API_KEY"):
    st.error("Please set the OPENAI_API_KEY environment variable.")
    st.stop()


llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.2)
llm_with_tools = llm.bind_tools(list(tools_by_name.values()))
prompt = st.text_input("Enter your financial question or request:")


if prompt: 
    messages = [
    SystemMessage(content="You are a wealth advisor for Indian investors. "
    "When users ask about funds, markets, or current rates, use the web_search tool. "
    "Base your answer on tool results. "
    "Suggest specific fund names or categories when the search results support it. "
    "Always end with: this is educational, not SEBI-registered advice." \
    " If the user asks for general financial advice, provide it based on your training data, but also suggest they ask about specific funds or market conditions for more tailored info."),
    HumanMessage(content=prompt)
]
    
    response = llm_with_tools.invoke(messages)
    messages.append(response)

    if response.tool_calls:
        for call in response.tool_calls:
            tool_fn = tools_by_name[call["name"]]
            tool_response = tool_fn.invoke(call["args"])
            tool_response = tool_fn.invoke(call["args"])
            print("QUERY:", call["args"])
            print("TOOL RESULT:", repr(tool_response))
            st.sidebar.write("Search query:", call["args"])
            st.sidebar.write("Results:", tool_response)
            messages.append(ToolMessage(content=tool_response, tool_name=call["name"], tool_call_id=call["id"]))
            final_response = llm.invoke(messages)
            st.write(final_response.content)
           
    else:
        st.write(response.content)
        




