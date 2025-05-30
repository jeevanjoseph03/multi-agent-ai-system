from datetime import datetime
from typing import Dict, List, Any, Optional
import json
import sqlite3
import threading
from dataclasses import dataclass, asdict
from enum import Enum

class ActionStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class InputMetadata:
    source: str
    timestamp: datetime
    format_type: str
    intent: str
    file_path: Optional[str] = None
    
    def to_dict(self):
        return {
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'format_type': self.format_type,
            'intent': self.intent,
            'file_path': self.file_path
        }

@dataclass
class AgentAction:
    agent_name: str
    action_type: str
    status: ActionStatus
    details: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self):
        return {
            'agent_name': self.agent_name,
            'action_type': self.action_type,
            'status': self.status.value,
            'details': json.dumps(self.details),
            'timestamp': self.timestamp.isoformat()
        }

class MemoryStore:
    """
    Shared memory store for all agents to read/write data
    Uses SQLite for persistence and in-memory dict for fast access
    """
    
    def __init__(self, db_path: str = "memory_store.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
        
    def _init_database(self):
        """Initialize the SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Input metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS input_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    format_type TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    file_path TEXT,
                    session_id TEXT
                )
            ''')
            
            # Extracted fields table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS extracted_fields (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    field_value TEXT,
                    timestamp TEXT NOT NULL
                )
            ''')
            
            # Agent actions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agent_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT,
                    timestamp TEXT NOT NULL
                )
            ''')
            
            conn.commit()
    
    def store_input_metadata(self, metadata: InputMetadata, session_id: str) -> int:
        """Store input metadata and return the ID"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO input_metadata 
                    (source, timestamp, format_type, intent, file_path, session_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    metadata.source,
                    metadata.timestamp.isoformat(),
                    metadata.format_type,
                    metadata.intent,
                    metadata.file_path,
                    session_id
                ))
                conn.commit()
                return cursor.lastrowid
    
    def store_extracted_fields(self, session_id: str, agent_name: str, 
                             fields: Dict[str, Any]) -> None:
        """Store extracted fields from an agent"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                timestamp = datetime.now().isoformat()
                
                for field_name, field_value in fields.items():
                    cursor.execute('''
                        INSERT INTO extracted_fields 
                        (session_id, agent_name, field_name, field_value, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        session_id,
                        agent_name,
                        field_name,
                        str(field_value),
                        timestamp
                    ))
                conn.commit()
    
    def store_agent_action(self, session_id: str, action: AgentAction) -> None:
        """Store an agent action"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO agent_actions 
                    (session_id, agent_name, action_type, status, details, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    session_id,
                    action.agent_name,
                    action.action_type,
                    action.status.value,
                    json.dumps(action.details),
                    action.timestamp.isoformat()
                ))
                conn.commit()
    
    def get_session_data(self, session_id: str) -> Dict[str, Any]:
        """Get all data for a session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get metadata
            cursor.execute(
                'SELECT * FROM input_metadata WHERE session_id = ?', 
                (session_id,)
            )
            metadata = cursor.fetchone()
            
            # Get extracted fields
            cursor.execute(
                'SELECT * FROM extracted_fields WHERE session_id = ?', 
                (session_id,)
            )
            fields = cursor.fetchall()
            
            # Get actions
            cursor.execute(
                'SELECT * FROM agent_actions WHERE session_id = ?', 
                (session_id,)
            )
            actions = cursor.fetchall()
            
            return {
                'metadata': dict(metadata) if metadata else None,
                'extracted_fields': [dict(field) for field in fields],
                'actions': [dict(action) for action in actions]
            }
    
    def clear_session(self, session_id: str) -> None:
        """Clear all data for a session"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM input_metadata WHERE session_id = ?', (session_id,))
                cursor.execute('DELETE FROM extracted_fields WHERE session_id = ?', (session_id,))
                cursor.execute('DELETE FROM agent_actions WHERE session_id = ?', (session_id,))
                conn.commit()

# Example usage and testing
if __name__ == "__main__":
    # Test the memory store
    memory = MemoryStore()
    
    # Create sample metadata
    metadata = InputMetadata(
        source="email",
        timestamp=datetime.now(),
        format_type="email",
        intent="complaint",
        file_path="sample_email.txt"
    )
    
    session_id = "test_session_123"
    
    # Store metadata
    metadata_id = memory.store_input_metadata(metadata, session_id)
    print(f"Stored metadata with ID: {metadata_id}")
    
    # Store some extracted fields
    fields = {
        "sender": "angry_customer@example.com",
        "urgency": "high",
        "tone": "angry"
    }
    memory.store_extracted_fields(session_id, "email_agent", fields)
    
    # Store an action
    action = AgentAction(
        agent_name="email_agent",
        action_type="escalate",
        status=ActionStatus.COMPLETED,
        details={"crm_ticket_id": "CRM-12345"},
        timestamp=datetime.now()
    )
    memory.store_agent_action(session_id, action)
    
    # Retrieve session data
    session_data = memory.get_session_data(session_id)
    print("Session data:", json.dumps(session_data, indent=2, default=str))