import os
from pathlib import Path
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mcp.server.fastmcp import FastMCP

# 1. Initialize FastMCP Server
# The name provided here is how the server identifies itself to the LLM client.
mcp = FastMCP("Data-Inspector")

DB_PATH = Path(__file__).resolve().parent / "hr_data.db"

# ---------------------------------------------------------------------------
# Tool 1: List Tables & Schema
# ---------------------------------------------------------------------------
@mcp.tool()
def list_tables() -> str:
    """
    Returns the schema of the local SQLite database. 
    Use this tool first to understand what tables and columns are available before querying.
    """
    if not os.path.exists(DB_PATH):
        return f"Error: Database file '{DB_PATH}' not found. Please run your data ingestion script first."
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Query to get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            return "The database is empty (no tables found)."
        
        schema_output = "Database Schema:\n"
        for table in tables:
            table_name = table[0]
            schema_output += f"\nTable: {table_name}\nColumns:\n"
            
            # Query info for each specific table
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            for col in columns:
                # col[1] is column name, col[2] is data type
                schema_output += f"  - {col[1]} ({col[2]})\n"
                
        conn.close()
        return schema_output
    except Exception as e:
        return f"An error occurred while fetching the schema: {str(e)}"

# ---------------------------------------------------------------------------
# Tool 2: Execute SQL Read Query
# ---------------------------------------------------------------------------
@mcp.tool()
def execute_read_query(sql_query: str) -> str:
    """
    Executes a read-only SQL query against the SQLite database and returns the results as a string.
    Only SELECT statements are permitted. Do not attempt modification operations.
    """
    # Quick guard against destructive actions
    clean_query = sql_query.strip().lower()
    if not clean_query.startswith("select"):
        return "Error: This tool only supports read-only SELECT queries for safety."
        
    try:
        conn = sqlite3.connect(DB_PATH)
        # Use pandas to easily parse the query directly into a readable string format
        df = pd.read_sql_query(sql_query, conn)
        conn.close()
        
        if df.empty:
            return "Query executed successfully, but returned 0 rows."
            
        # Return a clean string or Markdown representation of the table data
        return df.to_string(index=False)
    except Exception as e:
        return f"SQL Execution Error: {str(e)}"

# ---------------------------------------------------------------------------
# Tool 3: Generate Distribution Chart
# ---------------------------------------------------------------------------
@mcp.tool()
def generate_distribution_chart(table_name: str, column_name: str) -> str:
    """
    Generates a simple distribution bar/histogram chart for a numerical or categorical column 
    in a given table, saves it locally as an image, and returns the path to the saved file.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        # Pull only the required column to save memory
        df = pd.read_sql_query(f"SELECT [{column_name}] FROM [{table_name}]", conn)
        conn.close()
        
        # Setup modern, clean plotting styles
        plt.figure(figsize=(8, 5))
        
        # Check if column is numeric or categorical to draw the right graph
        if pd.api.types.is_numeric_dtype(df[column_name]):
            df[column_name].hist(bins=15, color='skyblue', edgecolor='black')
            plt.ylabel("Frequency")
        else:
            # Categorical bar chart for top 10 values
            df[column_name].value_counts().head(10).plot(kind='bar', color='coral', edgecolor='black')
            plt.ylabel("Count")
            plt.xticks(rotation=45, ha='right')
            
        plt.title(f"Distribution of {column_name} in {table_name}")
        plt.tight_layout()
        
        # Ensure an assets directory exists to hold the generated imagery
        os.makedirs("static", exist_ok=True)
        output_path = f"static/{table_name}_{column_name}_distribution.png"
        plt.savefig(output_path)
        plt.close()
        
        return f"Success: Chart successfully generated and saved locally to: '{output_path}'"
    except Exception as e:
        return f"Chart Generation Error: {str(e)}"

# 5. Boot the server when script executes directly
if __name__ == "__main__":
    # Standard input/output (stdio) transport mechanism 
    mcp.run(transport="stdio")