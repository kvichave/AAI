from fastmcp import FastMCP
import sqlite3
from typing import List, Dict, Any
import sqlite_utils
import json

mcp = FastMCP(name="SQLite MCP Server")

# IMPORTANT: we’ll attach a global connection so tools can share it
_db_conn = None
_db_path = None


# =========================
# 🔹 HELPERS
# =========================
def resolve_input(primary: Optional[str], field_name: str):
    """
    Resolves input from either primary param or fallback 'input'.
    """
    value = primary if primary is not None else "fallback"
    if not value:
        raise ValueError(f"Missing required parameter: {field_name}")
    return value


def ensure_connection():
    if _db_conn is None:
        raise ValueError("No database connected")

# -------------------------
# MCP Tools
# -------------------------
@mcp.tool
def connect_to_database(
    database: Optional[str] = None,
    
) -> str:
    """
    Connect to a SQLite database file.

    Args:
        database: Path to SQLite DB file

    Returns:
        JSON string with connection status
    """
    global _db_conn, _db_path

    try:
        db_path = resolve_input(database, "database")

        _db_conn = sqlite3.connect(db_path, check_same_thread=False)
        _db_path = db_path

        return success({
            "message": "Connected successfully",
            "database": _db_path
        })

    except Exception as e:
        return error(str(e))


@mcp.tool
def get_current_database_info() -> str:
    """
    Returns info about the currently connected database.
    """
    if _db_conn is None:
        return json.dumps({"error": "No database connected"})
    return json.dumps({
        "type": "sqlite",
        "path": _db_path,
        "status": "connected"
    })

@mcp.tool
def list_tables() -> str:
    """
    List all tables in the connected database.
    """
    try:
        ensure_connection()
        cursor = _db_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        return json.dumps(tables)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool
def describe_table(table_name: str) -> str:
    """
    Describe a table schema.
    """
    try:
        ensure_connection()
        cursor = _db_conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [{
            "cid": col[0],
            "name": col[1],
            "type": col[2],
            "notnull": col[3],
            "default": col[4],
            "pk": col[5],
        } for col in cursor.fetchall()]
        return json.dumps(columns)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool
def execute_sql(query: str) -> str:
    """
    Execute a SQL query safely and return results as JSON string.
    """
    try:
        ensure_connection()
        forbidden = ["DROP", "DELETE", "ALTER", "TRUNCATE"]
        if any(word in query.upper() for word in forbidden):
            return json.dumps({"error": "Unsafe query detected"})

        cursor = _db_conn.cursor()
        cursor.execute(query)
        try:
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
        except Exception:
            rows = []
            columns = []
        return json.dumps({"columns": columns, "rows": rows})
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool
def query_database(question: str) -> str:
    """
    Stub for NL -> SQL conversion.
    Replace with LLM-based SQL generation for production.
    """
    sql = f"-- translate to SQL: {question}"
    return json.dumps({
        "question": question,
        "generated_sql": sql,
        "result": []
    })

@mcp.tool
def get_connection_examples() -> str:
    """
    Example connection strings for different databases.
    """
    examples = [
        "sqlite:///path/to/sqlite.db",
        "postgresql://user:pass@localhost:5432/dbname",
        "mysql://user:pass@localhost:3306/dbname"
    ]
    return json.dumps(examples)
if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8004
    )