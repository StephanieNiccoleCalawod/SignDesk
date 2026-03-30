"""
database.py - SignDesk Database Connection (Core)
Connects to Microsoft SQL Server (MSSQL) via pyodbc.
"""

import pyodbc

# ──────────────────────────────────────────────────────────────
# CONNECTION SETTINGS — Edit these to match your setup
# ──────────────────────────────────────────────────────────────

SERVER   = r"ZEPHHH\SQLEXPRESS"          # or your SQL Server IP / hostname
DATABASE = "SignDeskDB"


# ──────────────────────────────────────────────────────────────
# CHOOSE ONE: Windows Auth OR SQL Server Auth
# ──────────────────────────────────────────────────────────────

def get_connection():
    """
    Returns a live pyodbc connection to SignDeskDB.
    
    Use Option A if you're on Windows and logged into the same machine.
    Use Option B if you have a SQL Server username and password.
    """

    # ── Option A: Windows Authentication (recommended for local dev) ──
    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
    )

    # ── Option B: SQL Server Authentication ──
    # Uncomment below and comment out Option A if using SQL login:
    #
    # conn_str = (
    #     "DRIVER={ODBC Driver 17 for SQL Server};"
    #     f"SERVER={SERVER};"
    #     f"DATABASE={DATABASE};"
    #     f"UID={USERNAME};"
    #     f"PWD={PASSWORD};"
    # )

    return pyodbc.connect(conn_str)


# ──────────────────────────────────────────────────────────────
# TEST — Run this file directly to check your connection
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        conn = get_connection()
        print("✅ Connected to SignDeskDB successfully!")
        conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
