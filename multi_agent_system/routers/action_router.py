import requests
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import time
import logging
import random

from multi_agent_system.memory.memory_store import MemoryStore # Assuming MemoryStore is accessible

class ActionType(Enum):
    ESCALATE_TO_CRM = "escalate_to_crm"
    ESCALATE_TO_MANAGER = "escalate_to_manager"
    LOG_WARNING = "log_warning" # Generic logging for non-critical issues
    BLOCK_TRANSACTION = "block_transaction_and_alert" # For JSON fraud/risk
    COMPLIANCE_ALERT = "compliance_alert" # For PDF policy issues
    ARCHIVE_DOCUMENT = "archive_document" # For PDF
    STANDARD_RESPONSE = "standard_response_email" # For Email
    NO_ACTION = "no_action"

class ActionPriority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class ActionRequest:
    session_id: str
    action_type: ActionType
    priority: ActionPriority
    payload: Dict[str, Any] # Data needed to perform the action
    source_agent: str # Which agent suggested this action
    max_retries: int = 3
    retry_count: int = 0
    # To be filled by ActionRouter after execution attempt
    action_id_in_db: Optional[int] = None 


@dataclass
class ActionResult:
    action_type: ActionType
    status: str # e.g., "success", "failed", "retrying"
    message: str
    external_reference_id: Optional[str] = None # e.g., CRM ticket ID
    details: Optional[Dict[str, Any]] = None # e.g. API response

class ActionRouter:
    """
    Action Router that triggers follow-up actions based on agent outputs
    Simulates calls to external systems like CRM, risk management, etc.
    """
    
    def __init__(self, memory_store: MemoryStore):
        self.name = "action_router"
        self.memory_store = memory_store
        self.api_endpoints = self._load_api_endpoints()

    def _load_api_endpoints(self) -> Dict[str, str]:
        """Load API endpoints for external systems (simulated)"""
        return {
            "crm_escalate": "http://localhost:9001/api/crm/escalate", # Simulated
            "manager_alert": "http://localhost:9001/api/alert/manager", # Simulated
            "risk_alert_system": "http://localhost:9001/api/risk/alert", # Simulated
            "compliance_log": "http://localhost:9001/api/compliance/log", # Simulated
            "archiving_service": "http://localhost:9001/api/archive/document" # Simulated
        }

    def _simulate_api_call(self, endpoint_key: str, payload: Dict[str, Any]) -> ActionResult:
        url = self.api_endpoints.get(endpoint_key)
        if not url:
            return ActionResult(action_type=ActionType[endpoint_key.upper()] if endpoint_key.upper() in ActionType.__members__ else ActionType.NO_ACTION, status="failed", message=f"API endpoint key '{endpoint_key}' not configured.")

        print(f"SIMULATING API CALL to {url} with payload: {payload}")
        # Simulate network latency and potential failure
        time.sleep(random.uniform(0.1, 0.5))
        
        # Simulate a chance of failure for retry demonstration
        if random.random() < 0.15: # 15% chance of failure
             print(f"SIMULATED API CALL FAILED for {url}")
             return ActionResult(action_type=ActionType[endpoint_key.upper()] if endpoint_key.upper() in ActionType.__members__ else ActionType.NO_ACTION, status="failed", message="Simulated API call failed: Network error or server unavailable.")

        # Simulate a successful API call
        print(f"SIMULATED API CALL SUCCESS for {url}")
        # Example: CRM might return a ticket ID
        external_id = None
        if "crm" in endpoint_key:
            external_id = f"CRM-TICKET-{random.randint(1000,9999)}"
        elif "risk" in endpoint_key:
            external_id = f"RISK-ALERT-{random.randint(100,999)}"
        
        return ActionResult(
            action_type=ActionType[endpoint_key.upper()] if endpoint_key.upper() in ActionType.__members__ else ActionType.NO_ACTION, # Map back to ActionType
            status="success",
            message=f"Successfully simulated API call to {endpoint_key}.",
            external_reference_id=external_id,
            details={"simulated_response_status": 200, "payload_sent": payload}
        )

    def _handle_crm_escalation(self, request: ActionRequest) -> ActionResult:
        # Payload might contain customer details, issue description from email_agent
        return self._simulate_api_call("crm_escalate", request.payload)

    def _handle_manager_escalation(self, request: ActionRequest) -> ActionResult:
        # Payload might contain critical issue details
        return self._simulate_api_call("manager_alert", request.payload)

    def _handle_log_warning(self, request: ActionRequest) -> ActionResult:
        # This might just log to console or a file, or a simple logging service
        print(f"LOGGING WARNING (Session: {request.session_id}): {request.payload.get('message', 'No details provided.')}")
        return ActionResult(action_type=ActionType.LOG_WARNING, status="success", message="Warning logged successfully.", details=request.payload)

    def _handle_block_transaction(self, request: ActionRequest) -> ActionResult:
        # Payload from json_agent with anomaly details
        print(f"BLOCKING TRANSACTION (Session: {request.session_id}): Reason - {request.payload.get('reason', 'Fraud risk detected')}")
        # This could also trigger an alert
        alert_result = self._simulate_api_call("risk_alert_system", {"transaction_id": request.payload.get("transaction_id"), "reason": "Blocked due to anomalies"})
        return ActionResult(action_type=ActionType.BLOCK_TRANSACTION, status="success", message="Transaction blocked and alert raised.", details=alert_result.details, external_reference_id=alert_result.external_reference_id)

    def _handle_compliance_alert(self, request: ActionRequest) -> ActionResult:
        # Payload from pdf_agent with compliance keywords found
        return self._simulate_api_call("compliance_log", request.payload)
        
    def _handle_archive_document(self, request: ActionRequest) -> ActionResult:
        # Payload might contain document ID or metadata
        return self._simulate_api_call("archiving_service", request.payload)

    def create_action_from_agent_output(self, agent_name: str, agent_output: Dict[str, Any], session_id: str) -> Optional[ActionRequest]:
        action_type = ActionType.NO_ACTION
        priority = ActionPriority.LOW
        payload = agent_output # Pass the whole agent output as payload initially

        # Logic to map agent's suggested_action or findings to an ActionType
        suggested_action_str = agent_output.get("suggested_action")

        if agent_name == "email_agent":
            if suggested_action_str == EmailActionType.ESCALATE_TO_CRM.value:
                action_type = ActionType.ESCALATE_TO_CRM
                priority = ActionPriority.HIGH
            elif suggested_action_str == EmailActionType.ESCALATE_TO_MANAGER.value:
                action_type = ActionType.ESCALATE_TO_MANAGER
                priority = ActionPriority.HIGH
            elif suggested_action_str == EmailActionType.LOG_AND_ACKNOWLEDGE.value:
                action_type = ActionType.LOG_WARNING # Map to generic log
                priority = ActionPriority.LOW
                payload = {"message": f"Email (Subject: {agent_output.get('subject')}) logged and acknowledged.", "details": agent_output}
            elif suggested_action_str == EmailActionType.FLAG_FOR_REVIEW.value:
                action_type = ActionType.LOG_WARNING # Or a more specific review action
                priority = ActionPriority.MEDIUM
                payload = {"message": f"Email (Subject: {agent_output.get('subject')}) flagged for review.", "details": agent_output}
            else: # Standard response or other
                action_type = ActionType.STANDARD_RESPONSE
                priority = ActionPriority.LOW

        elif agent_name == "json_agent":
            if suggested_action_str == JSONActionType.BLOCK_AND_ALERT.value:
                action_type = ActionType.BLOCK_TRANSACTION
                priority = ActionPriority.HIGH
                # Payload should include relevant data for blocking/alerting
                payload = {"transaction_id": agent_output.get("extracted_data_preview", {}).get("transaction_id"), 
                           "reason": "Anomalies detected", "details": agent_output.get("anomalies_detected")}
            elif suggested_action_str == JSONActionType.FLAG_FOR_MANUAL_REVIEW.value:
                action_type = ActionType.LOG_WARNING # Or a specific review queue
                priority = ActionPriority.MEDIUM
                payload = {"message": "JSON data flagged for manual review.", "details": agent_output}
            elif suggested_action_str == JSONActionType.LOG_WARNING.value:
                action_type = ActionType.LOG_WARNING
                priority = ActionPriority.LOW
                payload = {"message": "Warning for JSON processing.", "details": agent_output.get("anomalies_detected")}


        elif agent_name == "pdf_agent":
            if suggested_action_str == PDFActionType.REVIEW_INVOICE.value:
                action_type = ActionType.LOG_WARNING # Or a specific invoice review action
                priority = ActionPriority.MEDIUM
                payload = {"message": "Invoice requires review.", "details": agent_output}
            elif suggested_action_str == PDFActionType.FLAG_FOR_LEGAL.value:
                action_type = ActionType.COMPLIANCE_ALERT # Map to general compliance alert
                priority = ActionPriority.HIGH
                payload = {"message": "Document flagged for legal review due to compliance keywords.", "details": agent_output}
            elif suggested_action_str == PDFActionType.COMPLIANCE_ALERT.value:
                action_type = ActionType.COMPLIANCE_ALERT
                priority = ActionPriority.MEDIUM
                payload = {"message": "Compliance alert triggered by PDF content.", "details": agent_output}
            elif suggested_action_str == PDFActionType.ARCHIVE_DOCUMENT.value:
                action_type = ActionType.ARCHIVE_DOCUMENT
                priority = ActionPriority.LOW
        
        if action_type != ActionType.NO_ACTION:
            return ActionRequest(
                session_id=session_id,
                action_type=action_type,
                priority=priority,
                payload=payload,
                source_agent=agent_name
            )
        return None

    def route_action(self, request: ActionRequest):
        """Routes the action to the appropriate handler and manages retries."""
        
        # Store initial action attempt in DB
        if request.action_id_in_db is None: # First attempt
            self.memory_store.store_action_result(
                session_id=request.session_id,
                action_type=request.action_type.value,
                priority=request.priority.value,
                status="queued",
                details={"payload": request.payload, "source_agent": request.source_agent},
                retry_count=request.retry_count
            )
            # A bit of a hack: to get the ID, we'd ideally want store_action_result to return it.
            # For simplicity, we'll assume the last inserted ID for this session and action type.
            # This is NOT robust for concurrent systems.
            # A better way: conn.execute(...).lastrowid
            # For now, we'll skip setting request.action_id_in_db to avoid complexity of fetching last ID.

        action_result: Optional[ActionResult] = None
        
        while request.retry_count <= request.max_retries:
            print(f"Attempting action: {request.action_type.value} (Attempt: {request.retry_count + 1}) for session {request.session_id}")
            
            if request.action_type == ActionType.ESCALATE_TO_CRM:
                action_result = self._handle_crm_escalation(request)
            elif request.action_type == ActionType.ESCALATE_TO_MANAGER:
                action_result = self._handle_manager_escalation(request)
            elif request.action_type == ActionType.LOG_WARNING:
                action_result = self._handle_log_warning(request)
            elif request.action_type == ActionType.BLOCK_TRANSACTION:
                action_result = self._handle_block_transaction(request)
            elif request.action_type == ActionType.COMPLIANCE_ALERT:
                action_result = self._handle_compliance_alert(request)
            elif request.action_type == ActionType.ARCHIVE_DOCUMENT:
                action_result = self._handle_archive_document(request)
            elif request.action_type == ActionType.STANDARD_RESPONSE or request.action_type == ActionType.NO_ACTION:
                 action_result = ActionResult(action_type=request.action_type, status="success", message="Action completed (standard/no action).")
            else:
                action_result = ActionResult(action_type=request.action_type, status="failed", message="Unknown action type.")

            if action_result and action_result.status == "success":
                print(f"Action {request.action_type.value} SUCCEEDED for session {request.session_id}.")
                self.memory_store.store_action_result( # Log final success
                    session_id=request.session_id,
                    action_type=request.action_type.value,
                    priority=request.priority.value,
                    status=action_result.status,
                    details=action_result.details if action_result.details else {"message": action_result.message},
                    external_ref_id=action_result.external_reference_id,
                    retry_count=request.retry_count
                )
                return action_result # Exit retry loop on success
            
            # Handle failure
            request.retry_count += 1
            status_for_db = "retrying" if request.retry_count <= request.max_retries else "failed_max_retries"
            
            print(f"Action {request.action_type.value} FAILED for session {request.session_id}. Status: {status_for_db}")
            self.memory_store.store_action_result( # Log attempt (failed or retrying)
                session_id=request.session_id,
                action_type=request.action_type.value,
                priority=request.priority.value,
                status=status_for_db,
                details=action_result.details if action_result and action_result.details else {"message": action_result.message if action_result else "Action execution failed."},
                external_ref_id=action_result.external_reference_id if action_result else None,
                retry_count=request.retry_count -1 # Log the attempt number that failed
            )

            if request.retry_count <= request.max_retries:
                wait_time = (2 ** request.retry_count) * random.uniform(0.5, 1.5) # Exponential backoff
                print(f"Retrying action {request.action_type.value} in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Action {request.action_type.value} failed after max retries for session {request.session_id}.")
                return action_result # Return the last failed result

        return action_result # Should ideally be the last failed result

# Example usage and testing
if __name__ == "__main__":
    from multi_agent_system.memory.memory_store import MemoryStore
    
    # Initialize components
    memory_store = MemoryStore()
    action_router = ActionRouter(memory_store)
    
    # Test different action scenarios
    test_scenarios = [
        # High-priority email escalation
        {
            "agent_name": "email_agent",
            "agent_output": {
                "suggested_action": "escalate_to_crm",
                "requires_escalation": True,
                "sender": "angry.customer@example.com",
                "tone": "angry",
                "urgency": "high",
                "risk_score": 0.9,
                "description": "Customer is extremely upset about product quality"
            }
        },
        
        # Suspicious transaction blocking
        {
            "agent_name": "json_agent",
            "agent_output": {
                "suggested_action": "block_and_alert",
                "risk_score": 0.95,
                "transaction_id": "TXN-SUSPICIOUS-123",
                "anomalies": ["high_amount", "suspicious_user"],
                "block_reason": "multiple_risk_factors"
            }
        },
        
        # Compliance document review
        {
            "agent_name": "pdf_agent",
            "agent_output": {
                "suggested_action": "escalate_compliance_review",
                "compliance_keywords": ["GDPR", "FDA"],
                "document_type": "policy",
                "risk_score": 0.7,
                "flags": ["regulatory_mention"]
            }
        }
    ]
    
    for i, scenario in enumerate(test_scenarios):
        print(f"\n=== Action Router Test {i+1} ===")
        print(f"Agent: {scenario['agent_name']}")
        print(f"Suggested Action: {scenario['agent_output']['suggested_action']}")
        
        # Create action request
        session_id = f"test_session_{i+1}"
        action_request = action_router.create_action_from_agent_output(
            scenario["agent_name"],
            scenario["agent_output"],
            session_id
        )
        
        print(f"Action Type: {action_request.action_type.value}")
        print(f"Priority: {action_request.priority}")
        
        # Execute action
        result = action_router.route_action(action_request)
        
        print(f"Execution Status: {result.status.value}")
        print(f"External Reference: {result.external_reference_id}")
        print(f"Execution Time: {result.execution_time_ms}ms")
        
        if result.error_message:
            print(f"Error: {result.error_message}")
        else:
            print(f"Response: {result.response_data}")