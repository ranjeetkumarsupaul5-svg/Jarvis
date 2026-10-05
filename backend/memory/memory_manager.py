import json
import re
import sqlite3
from typing import Any, Dict, List, Optional
from backend.db import get_db_connection


class MemoryManager:
    """
    Persistent SQLite memory store for JARVIS AI OS.
    Handles conversation history, user preferences, project context, and facts.
    """

    @staticmethod
    def _format_row(row: sqlite3.Row) -> Dict[str, Any]:
        """
        Format a raw SQLite row into a standardized memory record.
        """
        row_dict = dict(row)
        mem_id = row_dict.get("id")
        val = row_dict.get("value", "")
        key = row_dict.get("key", "")

        val_parsed = val
        if isinstance(val, str) and (val.startswith("{") or val.startswith("[")):
            try:
                val_parsed = json.loads(val)
            except Exception:
                pass

        fact_str = val if isinstance(val, str) else json.dumps(val)

        return {
            "memory_id": mem_id,
            "id": mem_id,
            "user_id": row_dict.get("user_id") or "default",
            "category": row_dict.get("category") or "user_fact",
            "key": key,
            "value": val_parsed,
            "fact": fact_str,
            "importance": row_dict.get("importance") if row_dict.get("importance") is not None else 1,
            "created_at": str(row_dict.get("created_at") or ""),
            "updated_at": str(row_dict.get("updated_at") or ""),
        }

    def add_conversation_turn(self, role: str, content: str) -> bool:
        """
        Record a conversational turn (user or assistant).
        """
        try:
            with get_db_connection() as conn:
                conn.execute(
                    "INSERT INTO conversation_history (role, content) VALUES (?, ?)",
                    (role, content)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"Failed to record conversation turn: {e}")
            return False

    def get_recent_conversation(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        Retrieve recent messages formatted for LLM context.
        """
        try:
            with get_db_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT role, content FROM conversation_history
                    ORDER BY id DESC LIMIT ?
                    """,
                    (limit,)
                ).fetchall()
                # Return in chronological order
                return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        except Exception as e:
            print(f"Failed to fetch conversation history: {e}")
            return []

    def clear_conversation_history(self) -> bool:
        """
        Clear short-term conversation history.
        """
        try:
            with get_db_connection() as conn:
                conn.execute("DELETE FROM conversation_history")
                conn.commit()
                return True
        except Exception as e:
            print(f"Failed to clear conversation history: {e}")
            return False

    # ---------------------------------------------------------
    # Long-Term Persistent Memory CRUD
    # ---------------------------------------------------------

    def add_memory(
        self,
        fact: Any,
        category: str = "user_fact",
        importance: int = 1,
        user_id: str = "default",
        key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store a new fact or preference, or update an existing one if the key matches.
        """
        if fact is None or (isinstance(fact, str) and not fact.strip()):
            return {
                "success": False,
                "message": "Cannot store empty fact.",
                "data": None,
                "error": "EmptyFact"
            }

        val_str = json.dumps(fact) if not isinstance(fact, str) else fact.strip()

        # Derive a sensible key if not explicitly supplied
        if not key or not str(key).strip():
            if isinstance(fact, str):
                cleaned = fact.strip()
                if " is " in cleaned:
                    key = cleaned.split(" is ", 1)[0].strip()
                elif " are " in cleaned:
                    key = cleaned.split(" are ", 1)[0].strip()
                elif " am " in cleaned:
                    key = cleaned.split(" am ", 1)[0].strip()
                else:
                    key = cleaned[:40]
            else:
                key = "fact"

        key = str(key).strip()

        try:
            with get_db_connection() as conn:
                existing = conn.execute(
                    """
                    SELECT id FROM memory
                    WHERE category = ? AND LOWER(key) = LOWER(?) AND user_id = ?
                    """,
                    (category, key, user_id)
                ).fetchone()

                if existing:
                    conn.execute(
                        """
                        UPDATE memory
                        SET value = ?, importance = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (val_str, importance, existing["id"])
                    )
                    mem_id = existing["id"]
                    action = "Updated"
                else:
                    cursor = conn.execute(
                        """
                        INSERT INTO memory (user_id, category, key, value, importance)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (user_id, category, key, val_str, importance)
                    )
                    mem_id = cursor.lastrowid
                    action = "Stored"

                conn.commit()
                row = conn.execute("SELECT * FROM memory WHERE id = ?", (mem_id,)).fetchone()
                record = self._format_row(row) if row else {"id": mem_id, "memory_id": mem_id}

            return {
                "success": True,
                "message": f"{action} memory successfully (ID: {mem_id}).",
                "data": record,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to add memory: {str(e)}",
                "data": None,
                "error": str(e)
            }

    def search_memory(
        self,
        query: str,
        category: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search memories by keyword across key, value, and category.
        Falls back to keyword matching if exact phrase returns no rows.
        """
        if not query or not query.strip():
            return self.list_memories(category=category, user_id=user_id, limit=limit)

        q_clean = query.strip().lower()

        try:
            with get_db_connection() as conn:
                # 1. Exact substring match
                sql = "SELECT * FROM memory WHERE (LOWER(key) LIKE ? OR LOWER(value) LIKE ?)"
                params: List[Any] = [f"%{q_clean}%", f"%{q_clean}%"]

                if category:
                    sql += " AND category = ?"
                    params.append(category)
                if user_id:
                    sql += " AND user_id = ?"
                    params.append(user_id)

                sql += " ORDER BY importance DESC, updated_at DESC LIMIT ?"
                params.append(limit)

                rows = conn.execute(sql, params).fetchall()
                if rows:
                    return [self._format_row(r) for r in rows]

                # 2. Significant keywords match fallback
                stopwords = {
                    "what", "is", "my", "the", "a", "an", "i", "am", "are", "do", "you",
                    "tell", "me", "about", "who", "where", "how", "that", "in", "to", "for"
                }
                words = [w for w in re.findall(r"\w+", q_clean) if len(w) > 1 and w not in stopwords]
                if not words:
                    return []

                clauses = []
                word_params: List[Any] = []
                for w in words:
                    clauses.append("(LOWER(key) LIKE ? OR LOWER(value) LIKE ?)")
                    word_params.extend([f"%{w}%", f"%{w}%"])

                sql2 = f"SELECT * FROM memory WHERE ({' OR '.join(clauses)})"
                if category:
                    sql2 += " AND category = ?"
                    word_params.append(category)
                if user_id:
                    sql2 += " AND user_id = ?"
                    word_params.append(user_id)

                sql2 += " ORDER BY importance DESC, updated_at DESC LIMIT ?"
                word_params.append(limit)

                rows2 = conn.execute(sql2, word_params).fetchall()
                return [self._format_row(r) for r in rows2]
        except Exception as e:
            print(f"Memory search error: {e}")
            return []

    def get_memory(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single memory record by primary key id.
        """
        try:
            with get_db_connection() as conn:
                row = conn.execute("SELECT * FROM memory WHERE id = ?", (memory_id,)).fetchone()
                return self._format_row(row) if row else None
        except Exception as e:
            print(f"Failed to get memory {memory_id}: {e}")
            return None

    def update_memory(
        self,
        memory_id: int,
        fact: Optional[Any] = None,
        category: Optional[str] = None,
        importance: Optional[int] = None,
        key: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing memory by its ID.
        """
        try:
            with get_db_connection() as conn:
                existing = conn.execute("SELECT * FROM memory WHERE id = ?", (memory_id,)).fetchone()
                if not existing:
                    return {
                        "success": False,
                        "message": f"Memory with ID {memory_id} does not exist.",
                        "data": None,
                        "error": "MemoryNotFound"
                    }

                updates = []
                params: List[Any] = []

                if fact is not None:
                    val_str = json.dumps(fact) if not isinstance(fact, str) else fact.strip()
                    updates.append("value = ?")
                    params.append(val_str)
                if category is not None:
                    updates.append("category = ?")
                    params.append(category)
                if importance is not None:
                    updates.append("importance = ?")
                    params.append(importance)
                if key is not None:
                    updates.append("key = ?")
                    params.append(key.strip())
                if user_id is not None:
                    updates.append("user_id = ?")
                    params.append(user_id)

                if not updates:
                    return {
                        "success": True,
                        "message": "No updates specified.",
                        "data": self._format_row(existing),
                        "error": None
                    }

                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(memory_id)

                conn.execute(f"UPDATE memory SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()

                updated_row = conn.execute("SELECT * FROM memory WHERE id = ?", (memory_id,)).fetchone()
                record = self._format_row(updated_row) if updated_row else None

                return {
                    "success": True,
                    "message": f"Updated memory {memory_id} successfully.",
                    "data": record,
                    "error": None
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to update memory: {str(e)}",
                "data": None,
                "error": str(e)
            }

    def delete_memory(
        self,
        memory_id: Optional[int] = None,
        key: Optional[str] = None,
        query: Optional[str] = None,
        category: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete a fact from persistent memory by ID, exact key, or matching query.
        """
        try:
            with get_db_connection() as conn:
                rowcount = 0
                if memory_id is not None:
                    sql = "DELETE FROM memory WHERE id = ?"
                    params: List[Any] = [memory_id]
                    if user_id:
                        sql += " AND user_id = ?"
                        params.append(user_id)
                    res = conn.execute(sql, params)
                    rowcount = res.rowcount
                elif key is not None:
                    sql = "DELETE FROM memory WHERE LOWER(key) = LOWER(?)"
                    params = [key.strip()]
                    if category:
                        sql += " AND category = ?"
                        params.append(category)
                    if user_id:
                        sql += " AND user_id = ?"
                        params.append(user_id)
                    res = conn.execute(sql, params)
                    rowcount = res.rowcount
                elif query is not None:
                    # Find candidate matches first
                    matches = self.search_memory(query=query, category=category, user_id=user_id, limit=5)
                    if matches:
                        ids_to_del = [m["id"] for m in matches]
                        placeholders = ",".join("?" for _ in ids_to_del)
                        res = conn.execute(f"DELETE FROM memory WHERE id IN ({placeholders})", ids_to_del)
                        rowcount = res.rowcount
                else:
                    return {
                        "success": False,
                        "message": "Specify memory_id, key, or query to delete memory.",
                        "data": None,
                        "error": "MissingIdentifier"
                    }

                conn.commit()

                if rowcount > 0:
                    return {
                        "success": True,
                        "message": f"Successfully deleted {rowcount} memory record(s).",
                        "data": {"deleted_count": rowcount},
                        "error": None
                    }
                return {
                    "success": False,
                    "message": "No matching memory found to delete.",
                    "data": {"deleted_count": 0},
                    "error": "MemoryNotFound"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to delete memory: {str(e)}",
                "data": None,
                "error": str(e)
            }

    def list_memories(
        self,
        category: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all stored memories ordered by importance and update recency.
        """
        try:
            with get_db_connection() as conn:
                sql = "SELECT * FROM memory"
                params: List[Any] = []
                conditions = []

                if category:
                    conditions.append("category = ?")
                    params.append(category)
                if user_id:
                    conditions.append("user_id = ?")
                    params.append(user_id)

                if conditions:
                    sql += " WHERE " + " AND ".join(conditions)

                sql += " ORDER BY importance DESC, updated_at DESC LIMIT ?"
                params.append(limit)

                rows = conn.execute(sql, params).fetchall()
                return [self._format_row(r) for r in rows]
        except Exception as e:
            print(f"Memory list error: {e}")
            return []

    # ---------------------------------------------------------
    # Backwards-Compatible Aliases
    # ---------------------------------------------------------

    def remember(
        self,
        category: str = "user_fact",
        key: str = "",
        value: Any = None,
        importance: int = 1,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Backwards-compatible alias for add_memory.
        """
        return self.add_memory(
            fact=value,
            category=category,
            importance=importance,
            user_id=user_id,
            key=key
        )

    def recall(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Backwards-compatible alias for search_memory / list_memories.
        """
        if query:
            return self.search_memory(query=query, category=category, user_id=user_id)
        return self.list_memories(category=category, user_id=user_id)

    def forget(self, key: str, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Backwards-compatible alias for delete_memory.
        """
        res = self.delete_memory(key=key, category=category)
        if res["success"]:
            return res
        return self.delete_memory(query=key, category=category)

    def save_memory(self, key: str, value: Any, category: str = "user_fact") -> Dict[str, Any]:
        """Convenience alias for remember."""
        return self.remember(category=category, key=key, value=value)

    def delete_memory_alias(self, key: str, category: Optional[str] = None) -> Dict[str, Any]:
        """Convenience alias for forget."""
        return self.forget(key=key, category=category)

    def get_all_memories(self) -> List[Dict[str, Any]]:
        """Convenience alias to list all memories."""
        return self.list_memories()


# Singleton memory instance
memory_manager = MemoryManager()
