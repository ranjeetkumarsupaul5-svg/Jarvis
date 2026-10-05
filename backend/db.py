import csv
import json
import sqlite3
import time
from backend.config import DB_PATH
def get_db_connection():
    """
    Returns a new SQLite connection with thread safety.
    """
    connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection
# Global connection for backwards compatibility with existing legacy code
conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
cursor = conn.cursor()
def init_db():
    """
    Initializes all required tables without dropping or deleting existing data.
    """
    with get_db_connection() as c:
        # System applications command table
        c.execute("""
            CREATE TABLE IF NOT EXISTS sys_command(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) UNIQUE,
                path VARCHAR(1000)
            )
        """)
        # Web shortcuts command table
        c.execute("""
            CREATE TABLE IF NOT EXISTS web_command(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100),
                url VARCHAR(1000)
            )
        """)
        # Contacts table for communication
        c.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200),
                Phone VARCHAR(255),
                email VARCHAR(255) NULL
            )
        """)
        # Long-term & persistent memory table
        c.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(100) DEFAULT 'default',
                category VARCHAR(100) DEFAULT 'user_fact',
                key VARCHAR(255),
                value TEXT,
                importance INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Backward-compatible column migrations if table previously existed without them
        try:
            c.execute("ALTER TABLE memory ADD COLUMN user_id VARCHAR(100) DEFAULT 'default'")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE memory ADD COLUMN importance INTEGER DEFAULT 1")
        except Exception:
            pass
        # Conversation history table
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role VARCHAR(50),
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Real-time activity & command execution log
        c.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT,
                intent VARCHAR(100),
                tool VARCHAR(100),
                status VARCHAR(50),
                result TEXT,
                execution_time REAL DEFAULT 0.0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Application settings table
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT
            )
        """)
        # Scheduled automations table
        c.execute("""
            CREATE TABLE IF NOT EXISTS automations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200),
                trigger_type VARCHAR(100),
                command TEXT,
                interval_sec INTEGER DEFAULT 0,
                status VARCHAR(50) DEFAULT 'ACTIVE',
                last_run TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Populate default system commands if empty
        row = c.execute("SELECT COUNT(*) as count FROM sys_command").fetchone()
        if row["count"] == 0:
            default_sys_commands = [
                ("notepad", "notepad.exe"),
                ("calculator", "calc.exe"),
                ("calc", "calc.exe"),
                ("paint", "mspaint.exe"),
                ("explorer", "explorer.exe"),
                ("cmd", "cmd.exe"),
                ("powershell", "powershell.exe"),
                ("task manager", "taskmgr.exe"),
            ]
            c.executemany(
                "INSERT OR IGNORE INTO sys_command (name, path) VALUES (?, ?)",
                default_sys_commands
            )
        # Ensure default web commands exist only if table is completely empty
        web_row = c.execute("SELECT COUNT(*) as count FROM web_command").fetchone()
        if web_row["count"] == 0:
            default_web = [
                ("google", "https://www.google.com"),
                ("youtube", "https://www.youtube.com"),
                ("github", "https://github.com"),
                ("chatgpt", "https://chatgpt.com"),
            ]
            c.executemany(
                "INSERT INTO web_command (name, url) VALUES (?, ?)",
                default_web
            )

        c.commit()
# Run initialization on import
init_db()


def log_activity(command, intent, tool, status, result, execution_time=0.0):
    """
    Log command and tool activity for observability and debugging.
    """
    try:
        with get_db_connection() as c:
            c.execute(
                """
                INSERT INTO activity_log (command, intent, tool, status, result, execution_time)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (str(command), str(intent), str(tool), str(status), str(result), float(execution_time))
            )
            c.commit()
    except Exception as e:
        print(f"Failed to log activity: {e}")
def get_recent_activities(limit=25):
    """
    Fetch recent system activity logs.
    """
    try:
        with get_db_connection() as c:
            rows = c.execute(
                "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"Failed to retrieve activities: {e}")
        return []
def save_setting(key, value):
    """
    Persist a setting key-value pair.
    """
    try:
        val_str = json.dumps(value) if not isinstance(value, str) else value
        with get_db_connection() as c:
            c.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, val_str)
            )
            c.commit()
            return True
    except Exception as e:
        print(f"Failed to save setting {key}: {e}")
        return False
def get_setting(key, default=None):
    """
    Retrieve a setting value.
    """
    try:
        with get_db_connection() as c:
            row = c.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            if row:
                try:
                    return json.loads(row["value"])
                except Exception:
                    return row["value"]
            return default
    except Exception as e:
        print(f"Failed to get setting {key}: {e}")
        return default
def get_automations():
    """
    Fetch all registered automations.
    """
    try:
        with get_db_connection() as c:
            rows = c.execute("SELECT * FROM automations ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"Failed to fetch automations: {e}")
        return []
def add_automation(name: str, trigger_type: str, command: str, interval_sec: int = 0):
    """
    Register a new scheduled task/automation.
    """
    try:
        with get_db_connection() as c:
            c.execute(
                "INSERT INTO automations (name, trigger_type, command, interval_sec) VALUES (?, ?, ?, ?)",
                (name, trigger_type, command, interval_sec)
            )
            c.commit()
            return True
    except Exception as e:
        print(f"Failed to add automation: {e}")
        return False
def toggle_automation(automation_id: int):
    """
    Toggle automation active/disabled state.
    """
    try:
        with get_db_connection() as c:
            row = c.execute("SELECT status FROM automations WHERE id = ?", (automation_id,)).fetchone()
            if row:
                new_status = "DISABLED" if row["status"] == "ACTIVE" else "ACTIVE"
                c.execute("UPDATE automations SET status = ? WHERE id = ?", (new_status, automation_id))
                c.commit()
                return new_status
            return None
    except Exception as e:
        print(f"Failed to toggle automation {automation_id}: {e}")
        return None