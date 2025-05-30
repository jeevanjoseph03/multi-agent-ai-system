import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional, List
import json # For serializing complex data like dictionaries/lists

# Define data structures for what will be stored (can also use Pydantic models)
class InputMetadata:
    def __init__(self, source: str, timestamp: datetime, format_type: str, intent: str, file_path: Optional[str] = None):
        self.source = source
        self.timestamp = timestamp
        self.format_type = format_type
        self.intent = intent
        self.file_path = file_path

class MemoryStore:
    def __init__(self, db_path="memory_store.db"):
        self.db_path = db_path
        self._create_tables()

    def _get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row # Access columns by name
        return conn

    def _create_tables(self):
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # Table for overall session/processing events
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS processing_sessions (
            session_id TEXT PRIMARY KEY,
            start_time TEXT NOT NULL,
            input_source TEXT,
            input_filename TEXT,
            classified_format TEXT,
            classified_intent TEXT,
            classification_reasoning TEXT,
            end_time TEXT,
            status TEXT 
        )
        """)
        
        # Table for data extracted by each agent
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_extractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            extracted_data TEXT NOT NULL, -- JSON string of extracted fields
            FOREIGN KEY (session_id) REFERENCES processing_sessions (session_id)
        )
        """)
        
        # Table for actions triggered by the ActionRouter
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS triggered_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            priority TEXT,
            status TEXT, -- e.g., queued, success, failed, retrying
            details TEXT, -- JSON string of action details or API response
            external_reference_id TEXT, -- e.g., CRM ticket ID
            retry_count INTEGER DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES processing_sessions (session_id)
        )
        """)
        conn.commit()
        conn.close()

    def start_session(self, session_id: str, source: str, filename: Optional[str]) -> None:
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO processing_sessions (session_id, start_time, input_source, input_filename, status)
        VALUES (?, ?, ?, ?, ?)
        """, (session_id, datetime.now().isoformat(), source, filename, "started"))
        conn.commit()
        conn.close()

    def store_input_metadata(self, metadata: InputMetadata, session_id: str, classification_reasoning: str = ""):
        """Stores initial classification and input metadata for a session."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        # Update existing session record if it was started, or insert if this is the first point
        cursor.execute("""
        UPDATE processing_sessions 
        SET classified_format = ?, classified_intent = ?, classification_reasoning = ?, input_source = ?, input_filename = ?
        WHERE session_id = ?
        """, (metadata.format_type, metadata.intent, classification_reasoning, metadata.source, metadata.file_path, session_id))
        
        if cursor.rowcount == 0: # If session wasn't pre-started
             cursor.execute("""
            INSERT INTO processing_sessions (session_id, start_time, input_source, input_filename, classified_format, classified_intent, classification_reasoning, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, metadata.timestamp.isoformat(), metadata.source, metadata.file_path, metadata.format_type, metadata.intent, classification_reasoning, "classified"))
        conn.commit()
        conn.close()

    def store_extracted_fields(self, session_id: str, agent_name: str, extracted_data: Dict[str, Any]):
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO agent_extractions (session_id, agent_name, timestamp, extracted_data)
        VALUES (?, ?, ?, ?)
        """, (session_id, agent_name, datetime.now().isoformat(), json.dumps(extracted_data)))
        conn.commit()
        conn.close()

    def store_action_result(self, session_id: str, action_type: str, priority: str, status: str, details: Optional[Dict[str, Any]] = None, external_ref_id: Optional[str] = None, retry_count: int = 0):
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO triggered_actions (session_id, action_type, timestamp, priority, status, details, external_reference_id, retry_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, action_type, datetime.now().isoformat(), priority, status, json.dumps(details) if details else None, external_ref_id, retry_count))
        conn.commit()
        conn.close()
    
    def update_action_status(self, action_id: int, status: str, details: Optional[Dict[str, Any]] = None, external_ref_id: Optional[str] = None, retry_count: Optional[int] = None):
        conn = self._get_db_connection()
        cursor = conn.cursor()
        updates = []
        params = []
        if details is not None:
            updates.append("details = ?")
            params.append(json.dumps(details))
        if external_ref_id is not None:
            updates.append("external_reference_id = ?")
            params.append(external_ref_id)
        if retry_count is not None:
            updates.append("retry_count = ?")
            params.append(retry_count)
        
        if not updates and status is None: # Nothing to update
            conn.close()
            return

        if status is not None:
            updates.append("status = ?") # Always update status if provided
            params.append(status)

        query = f"UPDATE triggered_actions SET {', '.join(updates)} WHERE id = ?"
        params.append(action_id)
        
        cursor.execute(query, tuple(params))
        conn.commit()
        conn.close()


    def end_session(self, session_id: str, final_status: str):
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE processing_sessions
        SET end_time = ?, status = ?
        WHERE session_id = ?
        """, (datetime.now().isoformat(), final_status, session_id))
        conn.commit()
        conn.close()

    def get_session_trace(self, session_id: str) -> Dict[str, Any]:
        conn = self._get_db_connection()
        session_data = conn.execute("SELECT * FROM processing_sessions WHERE session_id = ?", (session_id,)).fetchone()
        
        if not session_data:
            return {"error": "Session not found"}
            
        agent_extractions_raw = conn.execute("SELECT * FROM agent_extractions WHERE session_id = ? ORDER BY timestamp ASC", (session_id,)).fetchall()
        agent_extractions = []
        for row in agent_extractions_raw:
            extraction = dict(row)
            extraction['extracted_data'] = json.loads(extraction['extracted_data']) # Deserialize JSON
            agent_extractions.append(extraction)

        triggered_actions_raw = conn.execute("SELECT * FROM triggered_actions WHERE session_id = ? ORDER BY timestamp ASC", (session_id,)).fetchall()
        triggered_actions = []
        for row in triggered_actions_raw:
            action = dict(row)
            if action['details']:
                action['details'] = json.loads(action['details']) # Deserialize JSON
            triggered_actions.append(action)

        conn.close()
        
        return {
            "session_info": dict(session_data),
            "agent_outputs": agent_extractions,
            "actions_taken": triggered_actions
        }