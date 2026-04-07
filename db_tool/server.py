from fastmcp import FastMCP
import sqlite3
import json
from typing import Optional

mcp = FastMCP(name="SQLite MCP Server")

# =========================
# 🔹 GLOBAL STATE
# =========================
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
        raise ValueError("No database connected. Call connect_to_database first.")


def success(data):
    return json.dumps({"success": True, "data": data})


def error(message):
    return json.dumps({"success": False, "error": message})


# =========================
# 🔹 MCP TOOLS
# =========================

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
    Get current DB connection info.
    """
    try:
        ensure_connection()

        return success({
            "type": "sqlite",
            "path": _db_path,
            "status": "connected"
        })

    except Exception as e:
        return error(str(e))


@mcp.tool
def list_tables() -> str:
    """
    List all tables in DB.
    """
    try:
        ensure_connection()

        cursor = _db_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")

        tables = [row[0] for row in cursor.fetchall()]

        return success(tables)

    except Exception as e:
        return error(str(e))


@mcp.tool
def describe_table(
    table_name: Optional[str] = None,
    input: Optional[str] = None
) -> str:
    """
    Get schema of a table.

    Args:
        table_name: Name of the table
        input: fallback
    """
    try:
        ensure_connection()

        table_name = resolve_input(table_name, input, "table_name")

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

        return success(columns)

    except Exception as e:
        return error(str(e))


@mcp.tool
def execute_sql(
    query: Optional[str] = None,
    input: Optional[str] = None
) -> str:
    """
    Execute SQL query safely.

    Args:
        query: SQL query
        input: fallback
    """
    try:
        ensure_connection()

        query = resolve_input(query, input, "query")

        forbidden = ["DROP", "DELETE", "ALTER", "TRUNCATE"]
        if any(word in query.upper() for word in forbidden):
            return error("Unsafe query detected")

        cursor = _db_conn.cursor()
        cursor.execute(query)

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        return success({
            "columns": columns,
            "rows": rows
        })

    except Exception as e:
        return error(str(e))


@mcp.tool
def query_database(
    question: Optional[str] = None,
    input: Optional[str] = None
) -> str:
    """
    Convert natural language to SQL (stub).

    Args:
        question: natural language query
        input: fallback
    """
    try:
        question = resolve_input(question, input, "question")

        # Placeholder logic
        sql = f"-- Convert this to SQL: {question}"

        return success({
            "question": question,
            "generated_sql": sql,
            "result": []
        })

    except Exception as e:
        return error(str(e))


@mcp.tool
def get_connection_examples() -> str:
    """
    Example DB connection formats.
    """
    try:
        examples = [
            "sqlite:///path/to/database.db",
            "postgresql://user:pass@localhost:5432/db",
            "mysql://user:pass@localhost:3306/db"
        ]

        return success(examples)

    except Exception as e:
        return error(str(e))


# =========================
# 🔹 RUN SERVER
# =========================
if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8004
    )