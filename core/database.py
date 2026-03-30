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
# SCHEMA MIGRATION
# ──────────────────────────────────────────────────────────────

def update_database_schema():
    """Safely adds missing verification columns to the users table."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Safely add email_verified (BIT) - note we do not set DEFAULT 0 WITH VALUES 
        # so old legacy accounts stay NULL, but we will deal with that in login.
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'email_verified')
            BEGIN
                ALTER TABLE dbo.users ADD email_verified BIT DEFAULT 0;
            END
        """)

        # Safely add verification_code (NVARCHAR)
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'verification_code')
            BEGIN
                ALTER TABLE dbo.users ADD verification_code NVARCHAR(10) NULL;
            END
        """)

        # Safely add verification_expiry (DATETIME)
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'verification_expiry')
            BEGIN
                ALTER TABLE dbo.users ADD verification_expiry DATETIME NULL;
            END
        """)

        conn.commit()
        conn.close()
        print("Database schema verified/updated successfully.")
    except Exception as e:
        print(f"Error updating schema: {e}")


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
