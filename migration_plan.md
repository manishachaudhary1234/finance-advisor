# Plan: Migrate Finance Advisor to Google Agent Development Kit

**Date:** June 30, 2026  
**Project:** Finance Advisor Python Project Migration  
**Target:** Google Agent Development Kit with Gemini API  

---

## Executive Summary

This document provides a **step-by-step roadmap** to migrate your finance advisor from OpenAI+LangGraph to **Google Agent Development Kit** using Google's Gemini API.

**Key Points:**
- ✅ Preserve all existing functionality (memory, profiles, sessions)
- ✅ Swap OpenAI → Google Gemini incrementally
- ✅ Learn Google ADK patterns through hands-on migration
- ✅ Estimated effort: 4-6 hours for basic migration, 8-12 hours with optimization

---

## Current Project Architecture Summary

**Tech Stack (Current):**
- Web UI: Streamlit
- AI Model: OpenAI GPT-4o-mini
- Agent Framework: LangGraph
- Memory: SQLite (dual-layer: profiles + events)
- Language: Python 3.x

**Key Components:**
1. **Chatbot Node** - Responds to financial queries with user profile context
2. **Extract Node** - Auto-extracts profile updates from conversation
3. **Profile Store** - Persists user financial data (SQLite)
4. **Events Store** - Logs significant conversation events (SQLite)
5. **Streamlit UI** - Real-time streaming chat interface

**Data Structures:**
- `FinancialProfile` - User data (income, expenses, age, risk tolerance, goals)
- `ProfileUpdate` - Partial updates from LLM extraction
- `MemoryEvent` - Conversation events for audit trail

---

## Migration Strategy Overview

```
Phase 1: Foundation (1-2 hours)
├─ Install Google AI SDK
├─ Set up Gemini API key
└─ Test connectivity

Phase 2: Agent Logic Rewrite (3-4 hours)
├─ Replace chatbot node (OpenAI → Gemini)
├─ Replace extract node (structured output)
├─ Test both nodes independently
└─ Optional: Evaluate Google Agent Framework

Phase 3: Preserve Memory (1 hour)
├─ Keep SQLite layers unchanged
├─ Verify message format compatibility
└─ Test persistence

Phase 4: Update Frontend (1 hour)
├─ Update app.py model references
├─ Test Streamlit streaming
└─ Verify session management

Phase 5: Testing & Learning (1-2 hours)
├─ Unit tests (nodes, extraction, streaming)
├─ Integration tests (end-to-end flow)
└─ Performance comparison
```

---

## Detailed Implementation Steps

### ✅ Phase 1: Foundation & Setup (1-2 hours)

#### Step 1.1: Set Up Google Cloud Project & Gemini API Key

**Objective:** Get authenticated and ready to use Gemini API

**Actions:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Google Generative AI API**
4. Create API key:
   - Navigation → "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "API Key"
   - Copy the key
5. Store API key in `.env` file:
   ```
   GOOGLE_API_KEY=your_api_key_here
   OPENAI_API_KEY=your_existing_key_here  # Keep for reference
   ```
6. Load in Python via `python-dotenv`:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   google_api_key = os.getenv("GOOGLE_API_KEY")
   ```

**Verification:**
- ✓ `.env` file contains `GOOGLE_API_KEY`
- ✓ Can load the key without errors

---

#### Step 1.2: Install Google AI SDK & Dependencies

**Objective:** Add Google AI libraries to project

**Actions:**
1. Open `requirements.txt`
2. Add these dependencies:
   ```
   google-generativeai>=0.4.0
   google-cloud-aiplatform>=1.40.0  # Optional: for Vertex AI features later
   ```
3. Keep existing dependencies (remove only if explicitly duplicated):
   - Keep: `langchain-core`, `langgraph`, `pydantic`, `streamlit`, `langgraph-checkpoint-sqlite`
   - Remove/Replace: `langchain-openai` (replaced by `google-generativeai`)
4. Run: `pip install -r requirements.txt`

**Verification:**
- ✓ No import errors when running: `python -c "import google.generativeai; print(google.generativeai.__version__)"`
- ✓ All existing dependencies still install

---

#### Step 1.3: Create Test Script & Verify Gemini Connectivity

**Objective:** Test basic Gemini functionality before migrating core logic

**Actions:**
1. Create file: `test_gemini.py` in project root
2. Write test script:
   ```python
   import os
   import google.generativeai as genai
   from dotenv import load_dotenv
   
   load_dotenv()
   genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
   
   model = genai.GenerativeModel("gemini-2.0-flash")
   
   # Test 1: Simple chat
   response = model.generate_content("What are the best investment strategies for beginners?")
   print("Test 1 - Simple chat:")
   print(response.text)
   print()
   
   # Test 2: Streaming
   print("Test 2 - Streaming response:")
   for chunk in model.generate_content(
       "Explain compound interest in 3 sentences",
       stream=True
   ):
       print(chunk.text, end="", flush=True)
   print("\n")
   
   # Test 3: System prompt + context
   system_prompt = """You are an expert financial advisor. 
   Answer questions based on user's financial profile:
   Income: 50000 INR/month
   Age: 30
   Risk Tolerance: Medium"""
   
   response = model.generate_content(system_prompt + "\n\nWhat should I invest in?")
   print("Test 3 - With context:")
   print(response.text)
   ```
3. Run: `python test_gemini.py`
4. Document observations:
   - Response quality vs OpenAI
   - Streaming latency
   - Token counts / pricing estimate

**Verification:**
- ✓ All 3 tests run without errors
- ✓ Streaming works (Test 2 output appears incrementally)
- ✓ Context-aware response (Test 3 references profile)

---

### ✅ Phase 2: Rewrite Core Agent Logic (3-4 hours)

#### Step 2.1: Replace Chatbot Node (OpenAI → Gemini)

**Objective:** Migrate the main LLM conversation layer

**File:** `src/agent/graph.py`

**Current Code Pattern (OpenAI):**
```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
response = model.invoke(messages)
```

**New Code Pattern (Gemini):**
```python
import google.generativeai as genai
from langchain_core.messages import HumanMessage, AIMessage

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=genai.types.GenerationConfig(temperature=0.2),
    system_instruction="Your system prompt here"
)

# Convert LangChain messages to Gemini format
content = convert_messages_to_gemini_format(messages)
response = model.generate_content(content)
```

**Actions:**
1. Open `src/agent/graph.py`
2. Replace imports:
   ```python
   # Remove:
   # from langchain_openai import ChatOpenAI
   
   # Add:
   import google.generativeai as genai
   from langchain_core.messages import HumanMessage, AIMessage
   import os
   ```
3. Create conversion helper function:
   ```python
   def convert_messages_to_gemini_format(messages: list) -> list:
       """Convert LangChain messages to Gemini format"""
       gemini_messages = []
       for msg in messages:
           if isinstance(msg, HumanMessage):
               gemini_messages.append({
                   "role": "user",
                   "parts": [msg.content]
               })
           elif isinstance(msg, AIMessage):
               gemini_messages.append({
                   "role": "model",
                   "parts": [msg.content]
               })
       return gemini_messages
   ```
4. Replace model initialization in chatbot node:
   ```python
   async def chatbot(state: AgentState):
       user_id = state.get("user_id")
       
       # Load user profile
       profile = get_user_profile(user_id)
       
       # Build system prompt with profile context
       system_prompt = f"""You are an expert financial advisor for Indian investors.
       
       User Profile:
       Name: {profile.name}
       Age: {profile.age}
       Monthly Income: ₹{profile.income}
       Monthly Expenses: ₹{profile.expenses}
       Monthly Savings: ₹{profile.savings}
       Risk Tolerance: {profile.risk_tolerance}
       Investment Goals: {profile.goals}
       
       Provide personalized, actionable financial advice based on their profile."""
       
       # Initialize Gemini model
       model = genai.GenerativeModel(
           model_name="gemini-2.0-flash",
           generation_config=genai.types.GenerationConfig(temperature=0.2),
           system_instruction=system_prompt
       )
       
       # Convert messages and generate response
       gemini_messages = convert_messages_to_gemini_format(state["messages"][:-1])
       last_user_msg = state["messages"][-1].content
       
       response = model.generate_content(last_user_msg)
       
       return {"messages": [AIMessage(content=response.text)]}
   ```
5. Test the chatbot node independently (Step 2.4)

**Key Differences to Note:**
- Gemini doesn't use LangChain's message abstraction—need conversion
- System prompt must be set at model initialization
- Streaming works differently (covered in Step 4)
- No chat history passed as message list (you build it manually)

---

#### Step 2.2: Replace Extract Node (Structured Output)

**Objective:** Migrate profile extraction with structured output

**File:** `src/agent/graph.py` (extract node function)

**Current Code Pattern (OpenAI):**
```python
from langchain_openai import ChatOpenAI
from src.schemas.updates import ProfileUpdate

extractor = ChatOpenAI(model="gpt-4o-mini").with_structured_output(ProfileUpdate)
update = extractor.invoke(conversation_summary)
```

**New Code Pattern (Gemini):**
```python
import google.generativeai as genai
from pydantic import BaseModel
from src.schemas.updates import ProfileUpdate

# Gemini uses Pydantic schema directly
model = genai.GenerativeModel(
    "gemini-2.0-flash",
    generation_config=genai.types.GenerationConfig(
        response_mime_type="application/json",
        response_schema=ProfileUpdate
    )
)
response = model.generate_content(prompt)
update = ProfileUpdate.model_validate_json(response.text)
```

**Actions:**
1. Open `src/agent/graph.py` - find the `extract` node function
2. Replace the extractor initialization:
   ```python
   async def extract(state: AgentState):
       """Extract profile updates from conversation"""
       
       extraction_prompt = """Based on the conversation history, extract any new financial information 
       about the user that should update their profile.
       
       Return ONLY valid JSON matching the ProfileUpdate schema.
       If no updates, return empty object: {}
       
       Conversation:
       {conversation_summary}
       """.format(conversation_summary=format_messages_for_extraction(state["messages"]))
       
       model = genai.GenerativeModel(
           "gemini-2.0-flash",
           generation_config=genai.types.GenerationConfig(
               response_mime_type="application/json",
               response_schema=ProfileUpdate
           )
       )
       
       response = model.generate_content(extraction_prompt)
       
       try:
           update = ProfileUpdate.model_validate_json(response.text)
           
           # Merge update into profile if not empty
           if any(getattr(update, field) is not None for field in update.__fields__):
               user_id = state.get("user_id")
               merge_profile_update(user_id, update)
               log_event(user_id, "profile_updated", f"Extracted: {update}")
       
       except Exception as e:
           print(f"Extraction failed: {e}")
       
       return state
   ```
3. Create helper function to format messages:
   ```python
   def format_messages_for_extraction(messages: list) -> str:
       """Format message history into readable text for extraction"""
       formatted = []
       for msg in messages:
           role = "User" if isinstance(msg, HumanMessage) else "Advisor"
           formatted.append(f"{role}: {msg.content}")
       return "\n".join(formatted)
   ```
4. Test extraction independently (Step 2.4)

**Key Differences:**
- Gemini's structured output uses `response_schema` + `response_mime_type`
- Response comes as JSON string, must parse with Pydantic
- More explicit error handling needed
- Performance may differ—test extraction accuracy

---

#### Step 2.3: Evaluate Agent Framework Options (Optional Learning)

**Objective:** Understand if you need Google's agentic framework or can keep LangGraph

**Decision Point:** Do you want to use:

**Option A: Keep LangGraph (Minimal Changes)**
- ✅ Quick migration (1-2 days)
- ✅ Familiar framework (already using)
- ✅ Good for learning Gemini API
- ❌ Not using Google's native agent patterns

**Option B: Migrate to Google Agent Framework**
- ✅ Learn Google ADK patterns deeply
- ✅ Better integration with Google Cloud services
- ✅ Access to tool-use, grounding, planning
- ❌ Larger rewrite (3-5 days)
- ❌ More complex learning curve

**Recommendation:** 
- **Start with Option A** (keep LangGraph, swap Gemini)
- Complete Phase 2 first
- **Then (optional):** In Phase 2.3 Bonus, refactor to Google Agent Framework for deeper learning

**Action (if choosing Option B):**
- Research [Google Cloud Agents](https://cloud.google.com/agents)
- Or [Vertex AI Agent Builder](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-builder/overview)
- Consider if you want to move to hosted solution vs keeping local Python

**For now:** Proceed with Option A. You'll have a working migration, and can explore Google's frameworks later.

---

#### Step 2.4: Test Nodes Independently

**Objective:** Verify chatbot and extract nodes work before integration

**Actions:**

1. **Test Chatbot Node:**
   - Create `test_chatbot_node.py`:
   ```python
   import asyncio
   from src.agent.graph import chatbot
   from src.schemas.profile import FinancialProfile
   from langchain_core.messages import HumanMessage
   
   async def test():
       # Mock profile
       profile = FinancialProfile(
           name="Test User",
           age=30,
           income=50000,
           expenses=20000,
           savings=10000,
           risk_tolerance="medium",
           goals=["retirement", "home"],
           exclusions=[]
       )
       
       # Mock state
       state = {
           "messages": [HumanMessage(content="What should I invest in?")],
           "user_id": "test_user_123"
       }
       
       # Run chatbot
       result = await chatbot(state)
       print("Chatbot Response:")
       print(result["messages"][-1].content)
   
   asyncio.run(test())
   ```
   - Run: `python test_chatbot_node.py`
   - Verify: Response is coherent and references profile

2. **Test Extract Node:**
   - Create `test_extract_node.py`:
   ```python
   import asyncio
   from src.agent.graph import extract
   from langchain_core.messages import HumanMessage, AIMessage
   
   async def test():
       state = {
           "messages": [
               HumanMessage(content="My income just increased to 75000 INR per month"),
               AIMessage(content="Great! That's wonderful news. Higher income opens up new investment opportunities...")
           ],
           "user_id": "test_user_123"
       }
       
       result = await extract(state)
       print("Extraction Result:")
       print(result)
   
   asyncio.run(test())
   ```
   - Run: `python test_extract_node.py`
   - Verify: Profile updated correctly (check `data/profiles.db` or logs)

**Verification Checklist:**
- ✓ Both nodes run without errors
- ✓ Chatbot produces relevant financial advice
- ✓ Extract correctly identifies profile updates
- ✓ No hallucinated data in ProfileUpdate

---

### ✅ Phase 3: Preserve Memory & Persistence (1 hour)

#### Step 3.1: Verify Memory Layers Work with Gemini

**Objective:** Ensure SQLite storage remains compatible

**Actions:**
1. No code changes needed—memory layers are framework-agnostic
2. Verify compatibility:
   - `src/memory/profile_store.py` - stores/loads `FinancialProfile` (Python objects)
   - `src/memory/events_store.py` - logs events with timestamps
   - Both use SQLite directly, no dependency on OpenAI/LangGraph
3. Run existing memory tests:
   ```python
   from src.memory.profile_store import get_profile, save_profile
   from src.schemas.profile import FinancialProfile
   
   # Test load
   profile = get_profile("test_user_123")
   print(f"Loaded: {profile}")
   
   # Test save
   profile.income = 75000
   save_profile("test_user_123", profile)
   
   # Verify persistence
   reloaded = get_profile("test_user_123")
   assert reloaded.income == 75000
   print("✓ Memory layer working")
   ```

**Verification:**
- ✓ Profile loads/saves without errors
- ✓ Events log correctly
- ✓ No data loss between sessions

---

#### Step 3.2: Verify Message Format Compatibility

**Objective:** Ensure message history works with both LangGraph + Gemini

**Actions:**
1. Check if messages stored in SQLite use LangChain format:
   - Look at `langgraph-checkpoint-sqlite` format
   - Verify messages can be converted to Gemini format (Step 2.1 conversion function)
2. If checkpointing is used, test:
   ```python
   # Load conversation from checkpoint
   messages = load_conversation_checkpoint(thread_id)
   
   # Verify conversion works
   gemini_format = convert_messages_to_gemini_format(messages)
   
   # Feed to Gemini
   model = genai.GenerativeModel("gemini-2.0-flash")
   response = model.generate_content(gemini_format)
   ```

**Verification:**
- ✓ Messages load from checkpoint
- ✓ Conversion to Gemini format succeeds
- ✓ Model generates response using history

---

### ✅ Phase 4: Update Frontend (1 hour)

#### Step 4.1: Update Streamlit App (`app.py`)

**Objective:** Swap model references and add Gemini streaming support

**File:** `app.py`

**Current Code Pattern (OpenAI):**
```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4o-mini")
response = model.invoke(messages)
```

**Changes Needed:**
1. **Import changes:**
   ```python
   # Remove:
   # from langchain_openai import ChatOpenAI
   
   # Add:
   import google.generativeai as genai
   import os
   from dotenv import load_dotenv
   
   load_dotenv()
   ```

2. **Initialize Gemini in app:**
   ```python
   # Configure Gemini API
   genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
   
   @st.cache_resource
   def get_model():
       return genai.GenerativeModel(
           "gemini-2.0-flash",
           generation_config=genai.types.GenerationConfig(temperature=0.2)
       )
   
   model = get_model()
   ```

3. **Update message streaming:**
   ```python
   # In the chat loop where you stream responses:
   
   # OLD (OpenAI):
   # for chunk in model.stream(messages):
   #     st.write(chunk.content, end="")
   
   # NEW (Gemini):
   with st.chat_message("assistant"):
       response_text = ""
       placeholder = st.empty()
       
       for chunk in model.generate_content(user_input, stream=True):
           if chunk.text:
               response_text += chunk.text
               placeholder.markdown(response_text)
   ```

4. **Update conversation flow:**
   - Ensure messages are converted to Gemini format before sending
   - Update any display logic that references model names

**Testing Steps:**
- Run `streamlit run app.py`
- Test: Send a financial query
- Verify: Response streams in real-time
- Verify: Profile updates are extracted and saved

---

### ✅ Phase 5: Testing & Optimization (1-2 hours)

#### Step 5.1: Unit Tests

**Objective:** Validate individual components

**Create test files:**

1. **`tests/test_chatbot_gemini.py`:**
   ```python
   import pytest
   from src.agent.graph import chatbot
   
   @pytest.mark.asyncio
   async def test_chatbot_with_profile():
       # Test chatbot responds with profile context
       state = {"messages": [...], "user_id": "..."}
       result = await chatbot(state)
       assert len(result["messages"]) > 0
       assert "income" in result["messages"][-1].content.lower() \
              or "savings" in result["messages"][-1].content.lower()
   
   @pytest.mark.asyncio
   async def test_chatbot_streaming():
       # Test that streaming returns content progressively
       state = {"messages": [...], "user_id": "..."}
       result = await chatbot(state)
       assert result["messages"][-1].content  # Non-empty response
   ```

2. **`tests/test_extraction.py`:**
   ```python
   import pytest
   from src.agent.graph import extract
   
   @pytest.mark.asyncio
   async def test_extract_income_update():
       state = {
           "messages": [
               HumanMessage("My salary increased to 100000 INR"),
               AIMessage("Congratulations...")
           ],
           "user_id": "test_123"
       }
       await extract(state)
       # Verify profile was updated
       profile = get_profile("test_123")
       assert profile.income == 100000
   ```

3. **`tests/test_memory.py`:**
   ```python
   import pytest
   from src.memory.profile_store import save_profile, get_profile
   
   def test_profile_persistence():
       profile = create_test_profile()
       save_profile("test_id", profile)
       loaded = get_profile("test_id")
       assert loaded.income == profile.income
   ```

**Run tests:**
```bash
pytest tests/ -v
```

---

#### Step 5.2: Integration Tests

**Objective:** Test end-to-end conversation flow

**Create `tests/test_integration.py`:**
```python
import pytest
import asyncio
from src.agent.graph import chatbot, extract

@pytest.mark.asyncio
async def test_full_conversation_flow():
    """Test: Chat → Profile Update → Persistence"""
    user_id = "integration_test_user"
    
    # Step 1: User provides financial information
    messages = [HumanMessage("I'm saving 10000 INR monthly")]
    state = {"messages": messages, "user_id": user_id}
    
    # Step 2: Chatbot responds
    chat_result = await chatbot(state)
    state["messages"].append(chat_result["messages"][0])
    
    # Step 3: Extract updates
    extract_result = await extract(state)
    
    # Step 4: Verify profile was updated
    profile = get_profile(user_id)
    assert profile.savings >= 10000
    
    print("✓ Full conversation flow working")
```

**Run:**
```bash
pytest tests/test_integration.py -v
```

---

#### Step 5.3: Performance Comparison

**Objective:** Compare OpenAI vs Gemini on key metrics

**Create `benchmark.py`:**
```python
import time
import os
import json
from langchain_openai import ChatOpenAI
import google.generativeai as genai

# Test queries
test_queries = [
    "What's the best investment strategy for beginners?",
    "How should I allocate my 5 lakh INR savings?",
    "What's my risk tolerance based on my age?",
    "Recommend tax-saving investment options",
]

def benchmark_openai():
    model = ChatOpenAI(model="gpt-4o-mini")
    results = []
    
    for query in test_queries:
        start = time.time()
        response = model.invoke([HumanMessage(query)])
        elapsed = time.time() - start
        results.append({
            "query": query,
            "time": elapsed,
            "length": len(response.content)
        })
    
    return results

def benchmark_gemini():
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel("gemini-2.0-flash")
    results = []
    
    for query in test_queries:
        start = time.time()
        response = model.generate_content(query)
        elapsed = time.time() - start
        results.append({
            "query": query,
            "time": elapsed,
            "length": len(response.text)
        })
    
    return results

if __name__ == "__main__":
    print("Benchmarking OpenAI vs Gemini...\n")
    
    openai_results = benchmark_openai()
    gemini_results = benchmark_gemini()
    
    print("OpenAI GPT-4o-mini:")
    avg_time_openai = sum(r["time"] for r in openai_results) / len(openai_results)
    print(f"  Average latency: {avg_time_openai:.2f}s")
    
    print("\nGoogle Gemini 2.0 Flash:")
    avg_time_gemini = sum(r["time"] for r in gemini_results) / len(gemini_results)
    print(f"  Average latency: {avg_time_gemini:.2f}s")
    
    print(f"\nGemini is {avg_time_openai / avg_time_gemini:.1f}x faster")
    
    # Save results
    with open("benchmark_results.json", "w") as f:
        json.dump({
            "openai": openai_results,
            "gemini": gemini_results
        }, f, indent=2)
```

**Run:**
```bash
python benchmark.py
```

---

## Summary Checklist

### Phase 1: Foundation ✓
- [ ] Google API key obtained and stored in `.env`
- [ ] `google-generativeai` installed in `requirements.txt`
- [ ] `test_gemini.py` runs successfully
- [ ] Documented observations: latency, quality, cost

### Phase 2: Agent Logic ✓
- [ ] Chatbot node updated to use Gemini
- [ ] Extract node updated with Gemini structured output
- [ ] Message conversion function works (`convert_messages_to_gemini_format`)
- [ ] Both nodes tested independently
- [ ] No errors in `graph.py`

### Phase 3: Memory ✓
- [ ] Profile persistence verified
- [ ] Message history compatible with conversion
- [ ] Events logging unchanged

### Phase 4: Frontend ✓
- [ ] `app.py` imports updated
- [ ] Gemini model initialized with caching
- [ ] Streaming works in Streamlit UI
- [ ] Full conversation flow tested

### Phase 5: Testing ✓
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Benchmark results documented
- [ ] Ready for production

---

## Troubleshooting Guide

### Issue: "Invalid API Key"
**Solution:**
- Verify `GOOGLE_API_KEY` is set in `.env`
- Ensure API key has Generative AI API enabled in Cloud Console
- Run: `python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GOOGLE_API_KEY')[:10])"`

### Issue: "Response schema validation failed"
**Solution:**
- Check `ProfileUpdate` schema matches extraction prompt
- Verify response is valid JSON: `json.loads(response.text)`
- Add error handling and fallback to empty update: `{}`
- Test extraction independently (Step 2.4)

### Issue: "Streaming not working in Streamlit"
**Solution:**
- Use `st.write_stream()` with generator
- Ensure Gemini response has `stream=True`
- Test with simple message first before profile context
- Check Streamlit version: `pip install --upgrade streamlit`

### Issue: "Profile not updating after conversation"
**Solution:**
- Verify extract node completes without error (check logs)
- Ensure `merge_profile_update()` is called in extract node
- Check SQLite permissions on `data/profiles.db`
- Run `python -m sqlite3 data/profiles.db "SELECT * FROM profiles;"` to verify data

### Issue: "Gemini response quality differs from OpenAI"
**Solution:**
- Adjust system prompt for Gemini (may need different phrasing)
- Reduce temperature from 0.2 to 0.1 for more deterministic responses
- Add explicit instructions: "Be concise. Reference user's financial profile."
- Use `gemini-2.0-flash` (more powerful) instead of `gemini-1.5-pro`
- Test on same queries, compare outputs

---

## Next Steps After Migration

Once Phase 5 is complete, consider:

1. **Explore Google Agent Framework** (optional)
   - Refactor LangGraph nodes to use Google Agents
   - Learn function calling + tool-use patterns
   - Better for production deployments

2. **Deploy to Google Cloud**
   - Cloud Run for Streamlit frontend
   - Cloud SQL for SQLite replacement (optional)
   - Vertex AI for advanced monitoring

3. **Add Advanced Features**
   - Real-time market data via Google Search API
   - Multi-modal inputs (voice, documents)
   - Analytics dashboard for conversation insights

4. **Mobile App** (mentioned in initial discussion)
   - Android app calling backend API
   - Use same Gemini models with API routing

---

## Resources & References

- **Google Generative AI SDK:** https://ai.google.dev/tutorials/python_quickstart
- **Gemini API Docs:** https://cloud.google.com/vertex-ai/generative-ai/docs/get-started-llm
- **LangGraph Docs:** https://langchain-ai.github.io/langgraph/
- **Pydantic Structured Output:** https://docs.pydantic.dev/2.0/
- **Streamlit Chat UI:** https://docs.streamlit.io/develop/api-reference/chat

---

**Document Version:** 1.0  
**Last Updated:** June 30, 2026  
**Status:** Ready for Step-by-Step Implementation
