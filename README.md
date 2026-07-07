# data-inspector

An MCP-Powered Analytics Agent paired with a lightweight UI that allows a user to ask complex questions and receive structured data analysis, complete with automated visualizations.

The dataset used can be found here: [Human Resources Data Set (Kaggle)](https://www.kaggle.com/datasets/rhuebner/human-resources-data-set)

## Demo

**Prompt**

<img width="720" height="350" alt="prompt_capture" src="https://github.com/user-attachments/assets/1cba26d9-e89f-40fe-9ddc-e8d455e3b7cc" />

**Chart generation**

<img width="1358" height="660" alt="prompt_chart" src="https://github.com/user-attachments/assets/f6596ce5-129e-48f5-bab6-3fe859cd7e60" />

## How to Run

Follow these steps to clone the repository, set up your local environment, and launch the Autonomous Data Inspector.

### Prerequisites

- Python 3.11 or 3.12 installed on your system.
- `uv` (the ultra-fast Python package and project manager).

If you don't have `uv` installed, run:

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```powershell
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Step 1: Clone the Repository

```bash
git clone https://github.com/super-unknowledge/data-inspector.git
cd data-inspector
```

### Step 2: Configure Your API Key

Get a free API key from the [Groq Console](https://console.groq.com/).

Paste your API key directly into the application's sidebar UI once it launches.

### Step 3: Launch the Application

```bash
uv run streamlit run app.py
```

Streamlit will boot up and provide a local web address (usually `http://localhost:8501`). Open this link in your browser to start interacting with your data agent. Paste your Groq API key and you're ready to start interacting with the agent.

All charts that are generated are saved in the `static/` directory created inside the project folder.

## Architecture

The goal was to build an AI analytics agent that lets users ask natural-language questions about HR data stored in a local SQLite database.

The MCP server exposes database tools. Streamlit is the UI. Groq (Llama 3.3 70B) handles reasoning and tool selection.
```
User Prompt → Streamlit Client → Groq API (Llama 3.3 70B)
                     ↑                              |
                     | (calls database tools)       | (decides to use tools)
                     v                              v
              MCP Python Server ←──────────────────+
                     |
                     v
              Local SQLite DB
```

### Final Working Stack

| Layer      | Technology                                          |
|------------|------------------------------------------------------|
| UI         | Streamlit                                             |
| LLM        | Groq — `llama-3.3-70b-versatile` with function calling |
| Tools      | FastMCP-decorated functions (direct import)           |
| Database   | SQLite (`hr_data.db`)                                 |
| Charts     | matplotlib → PNG in `static/`                         |
| Dev/test   | MCP Inspector, `mcp dev`                              |
| Environment| Python 3.12, `uv`, project venv                       |

### MCP Tools

| Tool | Purpose |
|------|---------|
| `list_tables()` | Return SQLite schema |
| `execute_read_query(sql_query)` | Run read-only SELECT queries |
| `generate_distribution_chart(table_name, column_name)` | Build histogram/bar charts with matplotlib |

### Agent Loop Design

1. Define a tools manifest mirroring the MCP tools for Groq function calling.
2. Send chat history + tools to Groq with `tool_choice="auto"`.
3. Execute returned tool calls against the Python functions.
4. Append tool results to message history.
5. Loop until Groq stops requesting tools (multi-step: schema → query → synthesis).
6. Render the final assistant response (and any chart) in Streamlit.

## Testing

Testing was done with the Model Context Protocol Inspector.

**Test sequence**

1. Call `list_tables` → verify schema.
2. Call `execute_read_query` → e.g. `SELECT * FROM hr_data LIMIT 5`.
3. Call `generate_distribution_chart` → confirm PNG under `static/`.

## Lessons Learned

- Test the MCP server and its tools with the MCP Inspector first.
- Mind the environment — old Node/npx versions break the MCP Inspector; relative DB paths break when clients spawn servers from different cwd.
- Groq message history is strict — only standard fields go to the API; keep UI state elsewhere.
- Session state is persistent — Streamlit survives failed API calls; bad history poisons later turns. A reset fixes more than you'd expect.
- Llama tool calling on Groq is imperfect — multi-turn tool loops need careful message formatting; expect occasional XML hallucinations.
- MCP in architecture ≠ MCP at runtime — direct imports are fine for a demo, but true MCP stdio is better for composability and Inspector-driven dev.
