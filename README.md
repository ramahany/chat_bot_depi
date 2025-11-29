# English Learning Chatbot

An intelligent multi-agent English learning chatbot built with Streamlit and LangGraph. ChatOBoto helps users practice English through conversational interactions, grammar explanations, and factual question answering, with per-user memory and persistent chat history.

## 🌟 Features

### Core Capabilities
- **🌐 Multi-Language Support**: Automatically detects and translates Arabic input to English.
- **🎯 Intent Classification**: Routes each message to the right agent (`chat`, `grammar_question`, `fact_question`).
- **📚 Grammar Explanations (RAG)**: Uses a ChromaDB knowledge base of books to answer grammar questions with citations.
- **🔍 Fact Search**: Uses Tavily search to answer factual / world-knowledge questions with sources.
- **💬 Conversational Practice with Grammar Help**: Google Gemini-based chat agent with a dedicated grammar-correction tool.
- **🧠 Memory & History**:
  - In-graph memory per chat thread via LangGraph checkpointer.
  - Conversation history and system prompts persisted in Firebase.
- **👤 User Management**: Login / signup and per-user chat threads.

### Agent / Tool Types (High Level)
1. **Language & Intent Classifier Agent** – Detects language (Arabic/English) and intent (`chat`, `grammar_question`, `fact_question`).
2. **Translator Agent** – Translates Arabic input to English.
3. **Grammar Explanation RAG Agent** – Retrieves context from a grammar KB and explains concepts.
4. **Fact Search Agent** – Calls Tavily to answer factual questions.
5. **Chat Agent** – Conversational Gemini-based agent that can call tools.
6. **Grammar Correction Tool** – External tool (Gemma-based) for sentence correction.

## 🏗️ Architecture & Memory

The application is built as a **LangGraph state machine** orchestrating multiple agents, with both short-term and long-term memory:

```text
User Input
  ↓
LangGraph Workflow (with InMemorySaver checkpointer)
  ↓
Language & Intent Classification  (Groq Qwen model)
  ├─ If Arabic → Translator (HF Helsinki-NLP)
  └─ If English → use directly
      ↓
Intent Router
  ├─ grammar_question → Grammar RAG Agent (HF SmolLM3-3B + ChromaDB)
  ├─ fact_question    → Fact Search Agent (Tavily)
  └─ chat             → Chat Agent (Gemini 2.0 Flash + Grammar Tool)
      └─ optional tool calls → `get_grammar_correction` (Gemma-based Gradio space)
             ↓
Final Composer → `final_output`
             ↓
Streamlit UI + Firebase (stores `hist` + `chat_bot_hist`)
```

- **In-graph memory**:
  - `Agents/graph.py` uses `InMemorySaver` from `langgraph.checkpoint.memory` and compiles the graph with `checkpointer=memory`.
  - In `pages/mainpage.py`, each chat uses `config={'configurable': {'thread_id': '<chat_id>'}}` when calling `graph.stream(...)`, so LangGraph keeps a separate memory thread per chat.
  - `Agents/state.py` defines a state with `messages: Annotated[list, add_messages]`, which LangGraph uses as a running message history for the chat agent.
- **Persistent memory (database)**:
  - `functions.py` (`DataBase` class) stores:
    - `hist`: User-visible chat history (plain messages used by Streamlit UI).
    - `chat_bot_hist`: LangChain/LLM message objects (including system prompt and internal conversation) serialized via `messages_to_dict` / `messages_from_dict`.
  - Data is stored in Firebase Firestore under `users/{username}/chats/{chat_id}`.

## 🛠️ Technologies Used

- **Frontend / UI**: Streamlit (multi-page navigation, chat UI, avatars).
- **Agent Orchestration**: LangGraph (`StateGraph`, conditional edges, `ToolNode`, `tools_condition`).
- **LLM Framework**: LangChain (`init_chat_model`, LangChain `tool` integration).
- **Vector DB / RAG**: ChromaDB Cloud (`Edu_KB` database, `books` collection).
- **Database / Auth**: Firebase Firestore (users, chats, message history).
- **Search API**: Tavily (via `tavily-python`).
- **Misc**: Gradio client, Groq API client, HuggingFace Inference client.

### Models & Services (Detailed by Agent / Tool)

- **Language & Intent Classifier (Agent)** – in `Agents/components.py` → `classify_input`:
  - **Provider**: Groq.
  - **Model ID**: `qwen/qwen3-32b`.
  - **Usage**: Given a user message, returns a JSON object with:
    - `language`: `"english"` or `"arabic"`.
    - `intent`: `"chat"`, `"grammar_question"`, or `"fact_question"`.

- **Translator Agent** – in `Agents/components.py` → `translator`:
  - **Provider**: HuggingFace Inference API.
  - **Model ID**: `Helsinki-NLP/opus-mt-ar-en`.
  - **Usage**: Translates Arabic (`state['user_input']`) to English and stores it in `state['translated_input']`.

- **Grammar Explanation RAG Agent** – in `Agents/components.py` → `grammar_explanation_Rag` and `Agents/Rag.py`:
  - **LLM Provider**: HuggingFace Inference API (`InferenceClient`).
  - **LLM Model ID**: `HuggingFaceTB/SmolLM3-3B` (both in `call_model` and in `explain`).
  - **Vector DB**: ChromaDB Cloud:
    - Tenant: `2c00d764-53a9-4bad-9e5e-4f1bce13358d`.
    - Database: `Edu_KB`.
    - Collection: `books`.
  - **Behavior**:
    - Queries ChromaDB with the user’s question (`query_texts=[query]`, `n_results=1`).
    - Extracts document text and `file_name` metadata.
    - Builds a teaching-style prompt for SmolLM3-3B.
    - Removes `<think>...</think>` sections if present.
    - Appends a citation: `The answer was driven from [book]`.

- **Fact Search Agent** – in `Agents/components.py` → `fact_search`:
  - **Service**: Tavily (`TavilyClient`).
  - **Input**: English query (original or translated).
  - **Output**: Short answer + `url` for more info (stored in `state['fact_answer']`).

- **Chat Agent** – in `Agents/components.py` → `chat`:
  - **LLM Provider**: Google Generative AI via LangChain.
  - **Model ID**: `google_genai:gemini-2.0-flash` (`init_chat_model`).
  - **Tools**: Binds the `get_grammar_correction` tool (`llm_with_tools = llm.bind_tools(tools, enforce_tool_use=False)`).
  - **System Prompt / Policy**:
    - In `pages/mainpage.py` and `functions.py`, a system message describes an “English conversation partner” that must never correct grammar directly and must use the grammar tool when needed.
  - **Memory**:
    - Uses `state['messages']` (LangGraph `add_messages`) for ongoing context within the graph.
    - Full chat history is mirrored to Firestore via `DataBase.update_chat` (`chat_bot_hist`).

- **Grammar Correction Tool** – in `Agents/components.py` → `get_grammar_correction`:
  - **Decorator**: `@tool` (LangChain tool).
  - **Service**: Gradio client.
  - **Endpoint**: `Client("Hager-Mohamed/Gemma_Grammar_Correction")` with `api_name="/correct"`.
  - **Underlying Model**: Gemma-based grammar correction model (hosted on HuggingFace Spaces via Gradio).
  - **Behavior**:
    - Takes a raw sentence string (`statment`).
    - Calls the Gradio endpoint and strips the `"Corrected:"` prefix.
    - Returns only the corrected sentence, which the chat agent wraps in the specified template: `It would be better to say: "<Output>"`.

- **Generic HF Text Model Helper** – in `Agents/components.py` → `call_model` and in `Agents/Rag.py` → `call_model` / `explain`:
  - **Provider**: HuggingFace Inference API.
  - **Default Model ID**: `HuggingFaceTB/SmolLM3-3B`.
  - **Usage**: General text generation (classifiers, explanations, etc.), with `<think>` stripping when necessary.

## 📋 Prerequisites

- Python 3.8+
- Firebase project with Firestore enabled.
- ChromaDB Cloud account and collection.
- API keys / secrets in Streamlit:
  - `HF_token` – HuggingFace API token.
  - `Travily_token` – Tavily API key.
  - `Gemini_key` – Google Gemini API key.
  - `Chromadb_token` – ChromaDB Cloud token.
  - `Groq_api_key` – Groq API key.
  - Firebase service account JSON (as `FIREBASE_KEY` table).

## 🚀 Installation

1. **Clone the repository**

```bash
git clone https://github.com/nhahub/NHA-063.git
cd chatbot
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure Streamlit secrets**

Create `.streamlit/secrets.toml`:

```toml
HF_token = "your_huggingface_token"
Travily_token = "your_tavily_api_key"
Gemini_key = "your_google_gemini_api_key"
Chromadb_token = "your_chromadb_api_token"
Groq_api_key = "your_groq_api_key"

[FIREBASE_KEY]
type = "service_account"
project_id = "your_project_id"
private_key_id = "your_private_key_id"
private_key = "your_private_key"
client_email = "your_client_email"
client_id = "your_client_id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your_cert_url"
```

4. **Set up ChromaDB**

- Ensure your ChromaDB Cloud instance has:
  - Database: `Edu_KB`.
  - Collection: `books`.
- Insert your grammar/teaching documents with `file_name` metadata; these are used for RAG and shown in the citation.

5. **Set up Firebase**

- Create a Firestore database.
- First signup / login will auto-create:
  - `users/{username}` documents.
  - `chats/{chat_id}` subcollection per user with:
    - `title`
    - `hist` (plain UI history)
    - `chat_bot_hist` (LangChain messages with system prompt).

## 🎮 Usage

1. **Run the app**

```bash
streamlit run main.py
```

2. **Open in browser**

- Go to the URL shown in the terminal (typically `http://localhost:8501`).

3. **Login / Sign up**

- Use the login page to:
  - Create a new account (username, name, password), or
  - Log in with existing credentials.

4. **Chat**

- Create new chats from the sidebar.
- Type messages in English or Arabic in the chat input.
- Watch status updates like:
  - “🌐 Translator agent working...”
  - “🧩 Grammar explanation agent preparing answer...”
  - “🔎 Fact agent performing web search...”
  - “💬 Chat agent generating natural reply...”
- Responses are streamed node-by-node through the LangGraph workflow and persisted into Firestore.

## 📁 Project Structure

```text
chatbot/
├── main.py              # Streamlit entry point, page navigation and sidebar
├── Agents/
│   ├── graph.py         # LangGraph state machine + checkpointer/memory
│   ├── state.py         # Conversation state schema (LangGraph TypedDict)
│   ├── components.py    # All agent implementations + tools + models
│   └── Rag.py           # RAG helper (ChromaDB + HF model)
├── pages/
│   └── mainpage.py      # Chat page, streaming graph, UI message loop
├── widgets.py           # Login, logout, add_chat widgets
├── functions.py         # Firebase DataBase wrapper (users, chats, memory)
├── requirements.txt     # Python dependencies
└── icons/               # Avatar icons for chat interface
    ├── user.png
    ├── assistant1.png
    └── assistant2.png
```

## 🔧 Memory & Persistence (More Detail)

- **LangGraph Memory**:
  - `InMemorySaver` is attached as a `checkpointer` when compiling the graph.
  - `thread_id` is set per chat (`config={'configurable': {'thread_id': chat_id}}`), so each chat’s agent-side memory is isolated.
  - `State.messages` uses `add_messages` which automatically appends new messages over time.

- **Firebase Persistence**:
  - `hist` is the UI-friendly list of `{role, content}` messages rendered in Streamlit.
  - `chat_bot_hist` contains the full structured LangChain messages, including system prompt and possibly additional metadata.
  - On every turn, `DataBase.update_chat` converts these to a safe dict format (`messages_to_dict`) before writing to Firestore.

## 🔁 Changing Models Per Agent / Tool

This section explains **how to safely swap models** for each agent while keeping the system stable.

- **General Guidelines**
  - **Keep input/output contracts the same**:
    - Classifier must still return valid JSON with `language` and `intent` keys.
    - Grammar tool must still return a **plain corrected sentence** (no extra text).
    - RAG answer should still be plain text; you can keep or modify the citation format.
  - **Update API keys / endpoints** in `secrets.toml` if you change providers.
  - **Test each agent in isolation** before combining them in the full app.

### 1. Change the Language & Intent Classifier Model

- **Current code**: `Agents/components.py` → `classify_input` (uses Groq `qwen/qwen3-32b`).
- **Steps**:
  1. Replace the `groq_client.chat.completions.create(...)` call with your new provider’s chat/completion call.
  2. Ensure the final `content` string is JSON and parsed via `json.loads(content)` into `{"language": "...", "intent": "..."}`.
  3. Keep the same keys (`language`, `intent`) and allowed values (`english`/`arabic`; `chat`/`grammar_question`/`fact_question`).
  4. Keep setting `state["intent"]` and `state["language"]` exactly as now.

### 2. Change the Translator Model

- **Current code**: `translator` in `Agents/components.py` uses `InferenceClient(...).translation(..., model="Helsinki-NLP/opus-mt-ar-en")`.
- **Steps**:
  1. Swap `"Helsinki-NLP/opus-mt-ar-en"` with your new translation model ID (HF or another provider).
  2. Ensure the new client call returns a `.translation_text`-like field or adapt the code to extract the translated string.
  3. Leave the rest of the function intact so that `state['translated_input']` and `state['status_message']` behave the same.

### 3. Change the Grammar Explanation RAG Model

- **Current code**: `Agents/Rag.py` uses `HuggingFaceTB/SmolLM3-3B` for `explain`.
- **Steps**:
  1. In `Rag.call_model` and the `self.client.chat.completions.create(...)` inside `explain`, replace the `model=` parameter with your desired model ID.
  2. If the new model may emit `<think>...</think>` or other control tokens, update the regex that strips them.
  3. Keep the ChromaDB query logic (unless you also change the vector DB).
  4. Keep returning a string (plus optional citation) to be stored in `state['grammar_explanation']`.

### 4. Change the Chat Agent Model

- **Current code**: `llm = init_chat_model("google_genai:gemini-2.0-flash", ...)` in `Agents/components.py`.
- **Steps**:
  1. Replace the first argument to `init_chat_model` with your new LangChain-compatible model ID (e.g., an OpenAI, Groq, or local model name).
  2. Ensure your environment / secrets include whatever keys the new model requires.
  3. Keep the `llm_with_tools = llm.bind_tools(tools, enforce_tool_use=False)` line, so tool-calling continues to work.
  4. Confirm that the model follows the system prompt contract (never corrects grammar directly; uses the tool).

### 5. Change the Grammar Correction Tool Model

- **Current code**: `get_grammar_correction` in `Agents/components.py`, using `Client("Hager-Mohamed/Gemma_Grammar_Correction")`.
- **Steps**:
  1. If using a different Gradio Space, update the `Client("<space_name>")` and `api_name` accordingly.
  2. If using a raw LLM instead of Gradio:
     - Replace the Gradio call with your LLM client’s call.
     - Make sure the function returns **only** the corrected sentence string.
  3. Keep the docstring and function name the same so the chat agent’s instructions remain valid.

### 6. Change the Fact Search Backend

- **Current code**: `fact_search` in `Agents/components.py` uses `TavilyClient`.
- **Steps**:
  1. Replace the Tavily call with your own search API (e.g., SerpAPI, custom backend).
  2. Ensure you still set `state['fact_answer']` to a human-readable answer string, ideally with a URL for more info.

### 7. Change the Generic HF Text Model

- **Current code**: `call_model` in both `Agents/components.py` and `Agents/Rag.py` defaults to `"HuggingFaceTB/SmolLM3-3B"`.
- **Steps**:
  1. Update the `model_name` default or the `model=` parameter where these helpers are called.
  2. Keep the function interface the same: input `prompt` (string) and output a string `raw_output` (with optional `<think>` stripping).

## 🔐 Security Notes

- Passwords are currently stored in plain text in Firestore (for real production use, add hashing).
- All API keys must be stored only in `secrets.toml` (never committed to Git).
- ChromaDB tenant/database IDs and Firebase config are sensitive and should not be leaked in public repos without care.

## 🚧 Known Limitations

- Translation currently supports only Arabic → English.
- Model-specific behaviors (like `<think>` tags) are handled via regex and may require updates when models change.





