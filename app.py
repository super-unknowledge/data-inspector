import json
import os
import re
from pathlib import Path

import streamlit as st
from groq import Groq

from mcp_server import execute_read_query, generate_distribution_chart, list_tables

PROJECT_ROOT = Path(__file__).resolve().parent
STATIC_DIR = PROJECT_ROOT / "static"
MAX_TOOL_ROUNDS = 10
MAX_TOOL_OUTPUT_CHARS = 8000
MODEL = "llama-3.3-70b-versatile"

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Autonomous Data Inspector", page_icon="📊", layout="wide")
st.title("📊 Autonomous Data Inspector")
st.caption("An AI Analytics Agent powered by Groq (Llama 3.3 70B) and a Local MCP Server")

if "GROQ_API_KEY" not in st.session_state:
    st.session_state["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")

with st.sidebar:
    st.header("Configuration")
    api_key_input = st.text_input(
        "Groq API Key",
        value=st.session_state["GROQ_API_KEY"],
        type="password",
    )
    if api_key_input:
        st.session_state["GROQ_API_KEY"] = api_key_input

    st.markdown("---")
    st.markdown("### Available MCP Tools")
    st.code(
        "list_tables()\n"
        "execute_read_query(sql_query)\n"
        "generate_distribution_chart(table_name, column_name)"
    )

if not st.session_state["GROQ_API_KEY"]:
    st.warning("Please enter your Groq API Key in the sidebar to begin.")
    st.stop()

client = Groq(api_key=st.session_state["GROQ_API_KEY"])

TOOLS_MANIFEST = [
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "Returns the schema and tables available in the local SQLite database.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_read_query",
            "description": (
                "Executes a read-only SELECT SQL query against the SQLite database "
                "and returns the text results."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "The complete, valid SELECT SQL query to execute.",
                    }
                },
                "required": ["sql_query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_distribution_chart",
            "description": (
                "Generates a distribution bar/histogram chart for a column in a table "
                "and saves it locally."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the target table.",
                    },
                    "column_name": {
                        "type": "string",
                        "description": "Name of the specific column to chart.",
                    },
                },
                "required": ["table_name", "column_name"],
            },
        },
    },
]

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": (
                "You are an expert AI data analyst. You have access to a local SQLite "
                "database via tools. If you do not know the schema, call list_tables first. "
                "Use execute_read_query for data questions. Use generate_distribution_chart "
                "when the user asks for a visual distribution. Be concise and ground answers "
                "in tool outputs."
            ),
        }
    ]

if "chart_by_index" not in st.session_state:
    st.session_state.chart_by_index = {}


def truncate_output(text: str) -> str:
    if len(text) <= MAX_TOOL_OUTPUT_CHARS:
        return text
    return text[:MAX_TOOL_OUTPUT_CHARS] + "\n\n...[truncated]..."


def extract_chart_path(tool_output: str) -> Path | None:
    match = re.search(r"static/[^\s']+\.png", tool_output)
    if not match:
        return None
    chart_path = PROJECT_ROOT / match.group(0)
    return chart_path if chart_path.exists() else None


def execute_tool(function_name: str, function_args: dict) -> str:
    if function_name == "list_tables":
        return list_tables()
    if function_name == "execute_read_query":
        return execute_read_query(sql_query=function_args.get("sql_query", ""))
    if function_name == "generate_distribution_chart":
        return generate_distribution_chart(
            table_name=function_args.get("table_name", ""),
            column_name=function_args.get("column_name", ""),
        )
    return f"Error: Unknown tool '{function_name}'."


def assistant_message_to_dict(message) -> dict:
    payload = {
        "role": "assistant",
        "content": message.content or "",
    }
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }
            for tool_call in message.tool_calls
        ]
    return payload


def run_agent(user_prompt: str) -> tuple[str, Path | None]:
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    chart_path: Path | None = None

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=st.session_state.messages,
                tools=TOOLS_MANIFEST,
                tool_choice="auto",
            )
        except Exception as exc:
            st.session_state.messages.pop()
            raise RuntimeError(f"Groq API error: {exc}") from exc

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if not tool_calls:
            assistant_output = response_message.content or "I could not generate a response."
            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_output}
            )
            return assistant_output, chart_path

        st.session_state.messages.append(assistant_message_to_dict(response_message))

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            try:
                function_args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                function_args = {}

            tool_output = truncate_output(execute_tool(function_name, function_args))

            if function_name == "generate_distribution_chart":
                maybe_chart = extract_chart_path(tool_output)
                if maybe_chart is not None:
                    chart_path = maybe_chart

            st.session_state.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": tool_output,
                }
            )

    try:
        final_response = client.chat.completions.create(
            model=MODEL,
            messages=st.session_state.messages,
            tools=TOOLS_MANIFEST,
            tool_choice="none",
        )
    except Exception as exc:
        raise RuntimeError(f"Groq API error during final synthesis: {exc}") from exc

    assistant_output = (
        final_response.choices[0].message.content
        or "I reached the tool-use limit before finishing the analysis."
    )
    st.session_state.messages.append({"role": "assistant", "content": assistant_output})
    return assistant_output, chart_path


# ---------------------------------------------------------------------------
# Render chat history (user/assistant only)
# ---------------------------------------------------------------------------
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] not in ("user", "assistant"):
        continue
    if not msg.get("content"):
        continue

    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if i in st.session_state.chart_by_index:
            st.image(st.session_state.chart_by_index[i])


# ---------------------------------------------------------------------------
# Main interaction
# ---------------------------------------------------------------------------
if user_prompt := st.chat_input("Ask me anything about your HR data..."):
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                assistant_output, chart_path = run_agent(user_prompt)

            st.markdown(assistant_output)

            if chart_path is not None:
                st.image(str(chart_path))
                st.session_state.chart_by_index[len(st.session_state.messages) - 1] = str(chart_path)

        except RuntimeError as exc:
            st.error(str(exc))