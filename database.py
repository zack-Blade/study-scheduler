"""
Smart Exam-Prep Scheduler — Phase 3: Database

Stores topics so they persist between requests,
enabling the "mark complete -> recalculate" feature.
"""

import sqlite3

DB_PATH = "scheduler.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # lets us access columns by name, not just position
    return conn

def init_users_table():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def create_user(username, password_hash):
    conn = get_connection()
    existing_count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    is_admin = 1 if existing_count == 0 else 0
    conn.execute(
        "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
        (username, password_hash, is_admin)
    )
    conn.commit()
    conn.close()


def get_user_by_username(username):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def get_all_users():
    conn = get_connection()
    rows = conn.execute("SELECT id, username, is_admin FROM users").fetchall()
    conn.close()
    return rows

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            name TEXT NOT NULL,
            weight INTEGER NOT NULL,
            weakness INTEGER NOT NULL,
            exam_date TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def save_topics(user_id, subject, topics_data):
    """
    Replaces topics for ONE subject, for ONE user only.
    topics_data: list of dicts with keys name, weight, weakness, exam_date
    """
    conn = get_connection()
    conn.execute("DELETE FROM topics WHERE subject = ? AND user_id = ?", (subject, user_id))
    for t in topics_data:
        conn.execute(
            "INSERT INTO topics (user_id, subject, name, weight, weakness, exam_date, done) VALUES (?, ?, ?, ?, ?, ?, 0)",
            (user_id, subject, t["name"], t["weight"], t["weakness"], t["exam_date"])
        )
    conn.commit()
    conn.close()


def get_all_topics(user_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM topics WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return rows


def mark_topic_done(user_id, topic_id):
    conn = get_connection()
    conn.execute("UPDATE topics SET done = 1 WHERE id = ? AND user_id = ?", (topic_id, user_id))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")

def delete_subject(user_id, subject):
    conn = get_connection()
    conn.execute("DELETE FROM topics WHERE subject = ? AND user_id = ?", (subject, user_id))
    conn.commit()
    conn.close()


def get_all_subjects(user_id):
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT subject FROM topics WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return [row["subject"] for row in rows]

def init_settings_table():
    # settings are keyed by (user_id, subject) — each user's subject gets its own hours/pace
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subject_settings (
            user_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            hours_per_day REAL NOT NULL DEFAULT 4,
            pace INTEGER NOT NULL DEFAULT 2,
            PRIMARY KEY (user_id, subject)
        )
    """)
    conn.commit()
    conn.close()

def save_settings(user_id, subject, hours_per_day, pace):
    conn = get_connection()
    conn.execute("""
        INSERT INTO subject_settings (user_id, subject, hours_per_day, pace) VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, subject) DO UPDATE SET hours_per_day = excluded.hours_per_day, pace = excluded.pace
    """, (user_id, subject, hours_per_day, pace))
    conn.commit()
    conn.close()

def get_settings(user_id, subject):
    conn = get_connection()
    row = conn.execute(
        "SELECT hours_per_day, pace FROM subject_settings WHERE user_id = ? AND subject = ?", (user_id, subject)
    ).fetchone()
    conn.close()
    return {"hours_per_day": row["hours_per_day"], "pace": row["pace"]} if row else {"hours_per_day": 4, "pace": 2}

def update_topic(user_id, topic_id, weight, weakness):
    conn = get_connection()
    conn.execute("UPDATE topics SET weight = ?, weakness = ? WHERE id = ? AND user_id = ?", (weight, weakness, topic_id, user_id))
    conn.commit()
    conn.close()