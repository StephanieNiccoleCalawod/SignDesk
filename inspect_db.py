import sqlite3

def inspect_db():
    conn = sqlite3.connect('signdesk.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    print("Tables:", tables)
    
    for t in tables:
        print(f"\n--- {t} ---")
        c.execute(f"PRAGMA table_info({t})")
        for r in c.fetchall():
            print(dict(r))
            
    # Also fetch a few records from audit_log to see what it looks like
    if "audit_log" in tables:
        print("\n--- audit_log samples ---")
        c.execute("SELECT * FROM audit_log LIMIT 5")
        for r in c.fetchall():
            print(dict(r))

    if "gesture_history" in tables:
        print("\n--- gesture_history samples ---")
        c.execute("SELECT * FROM gesture_history LIMIT 5")
        for r in c.fetchall():
            print(dict(r))
            
    conn.close()

if __name__ == '__main__':
    inspect_db()
