# data-inspector
An MCP-Powered Analytics Agent paired with a lightweight UI that allows a user to ask complex questions and receive structured data analysis, complete with automated visualizations.

The dataset used can be found here: https://www.kaggle.com/datasets/rhuebner/human-resources-data-set

### How to run:

clone the project and then run `uv run streamlit run app.py` to start the app

🚀 Getting Started
Follow these steps to clone the repository, set up your local environment, and launch the Autonomous Data Inspector.

Prerequisites
Python 3.11 or 3.12 installed on your system.

uv (The ultra-fast Python package and project manager).

If you don't have uv installed, run: curl -LsSf https://astral.sh/uv/install.sh | sh (Linux/macOS) or powershell -c "irm https://astral.sh/uv/install.ps1 | iex" (Windows).

Step 1: Clone the Repository
Clone this repository to your local machine and navigate into the project directory:

Bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
Step 2: Add the Database File
Ensure that the hr_data.db SQLite file provided to you is placed directly in the root directory of this project:

Plaintext
your-repo-name/
├── app.py
├── mcp_server.py
├── hr_data.db  <-- Place the file here
└── pyproject.toml
Step 3: Configure Your API Key
The AI agent uses Groq for free, rapid inference.

Get a free API key from the Groq Console.

Export it as an environment variable in your terminal:

Bash
# On Linux / macOS
export GROQ_API_KEY="gsk_your_actual_api_key_here"

# On Windows (Command Prompt)
set GROQ_API_KEY=gsk_your_actual_api_key_here

# On Windows (PowerShell)
$env:GROQ_API_KEY="gsk_your_actual_api_key_here"
(Alternatively, you can skip this step and paste your API key directly into the application's sidebar UI once it launches).

Step 4: Launch the Application
Because this project utilizes uv, you do not need to manually create virtual environments or run separate pip install commands. uv will read the pyproject.toml file, automatically download the correct dependencies in milliseconds, and run the app safely isolated.

Simply execute:

Bash
uv run streamlit run app.py
Streamlit will boot up and provide a local web address (usually http://localhost:8501). Open this link in your browser to start interacting with your data agent!

### Demo
Prompt
<img width="720" height="350" alt="prompt_capture" src="https://github.com/user-attachments/assets/1cba26d9-e89f-40fe-9ddc-e8d455e3b7cc" />

Chart generation
<img width="1358" height="660" alt="prompt_chart" src="https://github.com/user-attachments/assets/f6596ce5-129e-48f5-bab6-3fe859cd7e60" />

### Architecture
The goal was to build an AI analytics agent that lets users ask natural-language questions about HR data stored in a local SQLite database. The architecture:
User Prompt → Streamlit Client → Groq API (Llama 3.3 70B)
                     ↑                              |
                     | (calls database tools)       | (decides to use tools)
                     v                              v
              FastMCP Python Server ←──────────────────+
                     |
                     v
              Local SQLite DB

The MCP server exposes database tools. Streamlit is the UI. Groq (Llama 3.3 70B) handles reasoning and tool selection.

Final Working Stack
Layer	Technology
UI
Streamlit
LLM
Groq — llama-3.3-70b-versatile with function calling
Tools
FastMCP-decorated functions (direct import)
Database
SQLite (hr_data.db)
Charts
matplotlib → PNG in static/
Dev/test
MCP Inspector, mcp dev
Environment
Python 3.12, uv, project venv

The MCP has the following tools:
Tool Purpose
list_tables()
Return SQLite schema
execute_read_query(sql_query)
Run read-only SELECT queries
generate_distribution_chart(table_name, column_name)
Build histogram/bar charts with matplotlib

Agent loop design
Define a tools manifest mirroring the MCP tools for Groq function calling
Send chat history + tools to Groq with tool_choice="auto"
Execute returned tool calls against the Python functions
Append tool results to message history
Loop until Groq stops requesting tools (multi-step: schema → query → synthesis)
Render the final assistant response (and any chart) in Streamlit

### Testing
Testing was done with the model contect protocol inspector

Test sequence
Call list_tables → verify schema
Call execute_read_query → e.g. SELECT * FROM hr_data LIMIT 5
Call generate_distribution_chart → confirm PNG under static/

### Lessons learned
Test the MCP server in isolation first — Inspector saves hours of debugging the full stack.
Mind the environment — Old Node/npx breaks Inspector; relative DB paths break when clients spawn servers from different cwd.
Groq message history is strict — Only standard fields go to the API; keep UI state elsewhere.
Session state is persistent — Streamlit survives failed API calls; bad history poisons later turns. A reset fixes more than you’d expect.
Llama tool calling on Groq is imperfect — Multi-turn tool loops need careful message formatting; expect occasional XML hallucinations.
MCP in architecture ≠ MCP at runtime — Direct imports are fine for a demo; true MCP stdio is better for composability and Inspector-driven dev.
