import requests
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import time
import logging

class ActionType(Enum):
    ESCALATE_TO_CRM = "escalate_to_crm"
    ESCALATE_TO_MANAGER = "escalate_to_manager"
    CREATE_RISK_ALERT = "create_risk_alert"
    LOG_WARNING = "log_warning"
    BLOCK_TRANSACTION = "block_transaction"
    FLAG_FOR_REVIEW = "flag_for_review"
    EMERGENCY_RESPONSE = "emergency_response"
    COMPLIANCE_ALERT = "compliance_alert"
    PROCESS_NORMALLY = "process_normally"

class ActionStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

@dataclass
class ActionRequest:
    action_type: ActionType
    priority: str  # low, medium, high, critical
    source_agent: str
    session_id: str
    data: Dict[str, Any]
    context: Dict[str, Any]
    timestamp: datetime
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class ActionResult:
    action_request: ActionRequest
    status: ActionStatus
    response_data: Dict[str, Any]
    error_message: Optional[str]
    execution_time_ms: int
    external_reference_id: Optional[str]
    completed_at: datetime

class ActionRouter:
    """
    Action Router that triggers follow-up actions based on agent outputs
    Simulates calls to external systems like CRM, risk management, etc.
    """
    
    def __init__(self, memory_store=None):
        self.name = "action_router"
        self.memory_store = memory_store
        self.api_endpoints = self._load_api_endpoints()
        self.action_handlers = self._setup_action_handlers()
        self.logger = self._setup_logger()
    
    def _load_api_endpoints(self) -> Dict[str, str]:
        """Load API endpoints for external systems (simulated)"""
        return {
            "crm_escalation": "https://api.company.com/crm/escalate",
            "risk_alert": "https://api.company.com/risk/alert",
            "manager_notification": "https://api.company.com/notifications/manager",
            "compliance_system": "https://api.company.com/compliance/alert",
            "emergency_response": "https://api.company.com/emergency/trigger",
            "audit_log": "https://api.company.com/audit/log"
        }
    
    def _setup_action_handlers(self) -> Dict[ActionType, callable]:
        """Map action types to their handler functions"""
        return {
            ActionType.ESCALATE_TO_CRM: self._handle_crm_escalation,
            ActionType.ESCALATE_TO_MANAGER: self._handle_manager_escalation,
            ActionType.CREATE_RISK_ALERT: self._handle_risk_alert,
            ActionType.LOG_WARNING: self._handle_log_warning,
            ActionType.BLOCK_TRANSACTION: self._handle_block_transaction,
            ActionType.FLAG_FOR_REVIEW: self._handle_flag_review,
            ActionType.EMERGENCY_RESPONSE: self._handle_emergency_response,
            ActionType.COMPLIANCE_ALERT: self._handle_compliance_alert,
            ActionType.PROCESS_NORMALLY: self._handle_normal_processing
        }
    
    def _setup_logger(self):
        """Setup logging for action tracking"""
        logger = logging.getLogger('action_router')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def route_action(self, action_request: ActionRequest) -> ActionResult:
        """
        Main method to route and execute an action
        """
        start_time = datetime.now()
        self.logger.info(f"Routing action: {action_request.action_type.value} from {action_request.source_agent}")
        
        try:
            # Get the appropriate handler
            handler = self.action_handlers.get(action_request.action_type)
            if not handler:
                raise ValueError(f"No handler found for action type: {action_request.action_type}")
            
            # Execute the action
            response_data, external_ref = handler(action_request)
            
            # Calculate execution time
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Create successful result
            result = ActionResult(
                action_request=action_request,
                status=ActionStatus.COMPLETED,
                response_data=response_data,
                error_message=None,
                execution_time_ms=execution_time,
                external_reference_id=external_ref,
                completed_at=datetime.now()
            )
            
            self.logger.info(f"Action completed successfully: {external_ref}")
            
        except Exception as e:
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Create failed result
            result = ActionResult(
                action_request=action_request,
                status=ActionStatus.FAILED,
                response_data={},
                error_message=str(e),
                execution_time_ms=execution_time,
                external_reference_id=None,
                completed_at=datetime.now()
            )
            
            self.logger.error(f"Action failed: {str(e)}")
        
        # Store result in memory if available
        if self.memory_store:
            self._store_action_result(result)
        
        return result
    
    def _simulate_api_call(self, endpoint: str, payload: Dict[str, Any], 
                          method: str = "POST") -> Dict[str, Any]:
        """
        Simulate an API call to external system
        In a real implementation, this would make actual HTTP requests
        """
        # Simulate API response delay
        time.sleep(0.1)  # 100ms delay
        
        # Generate mock response based on endpoint
        if "crm" in endpoint:
            return {
                "ticket_id": f"CRM-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "status": "created",
                "priority": payload.get("priority", "medium"),
                "assigned_to": "support_team_lead"
            }
        elif "risk" in endpoint:
            return {
                "alert_id": f"RISK-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "risk_level": payload.get("risk_level", "medium"),
                "status": "active",
                "investigation_required": True
            }
        elif "manager" in endpoint:
            return {
                "notification_id": f"MGR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "sent_to": ["manager@company.com", "supervisor@company.com"],
                "delivery_status": "sent"
            }
        elif "compliance" in endpoint:
            return {
                "compliance_case_id": f"COMP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "regulatory_body": payload.get("regulatory_body", "internal"),
                "status": "under_review"
            }
        elif "emergency" in endpoint:
            return {
                "emergency_id": f"EMRG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "response_team_notified": True,
                "eta_minutes": 15
            }
        else:
            return {
                "log_id": f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "status": "logged"
            }
    
    def _handle_crm_escalation(self, request: ActionRequest) -> tuple[Dict[str, Any], str]:
        """Handle CRM escalation action"""
        payload = {
            "subject": f"Escalation from {request.source_agent}",
            "priority": request.priority,
            "description": request.data.get("description", "Automated escalation"),
            "customer_email": request.data.get("sender", "unknown@example.com"),
            "issue_type": request.data.get("issue_type", "complaint"),
            "urgency": request.data.get("urgency", "medium"),
            "tone": request.data.get("tone", "neutral"),
            "session_id": request.session_id,
            "source": "multi_agent_system"
        }
        
        response = self._simulate_api_call(self.api_endpoints["crm_escalation"], payload)
        return response, response.get("ticket_id")
    
    def _handle_manager_escalation(self, request: ActionRequest) -> tuple[Dict[str, Any], str]:
        """Handle manager escalation action"""
        payload = {
            "alert_type": "manager_escalation",
            "priority": request.priority,
            "source_agent": request.source_agent,
            "issue_summary": request.data.get("summary", "Issue requires manager attention"),
            "customer_info": request.data.get("customer_info", {}),
            "recommended_action": request.data.get("recommended_action", "immediate_review"),
            "session_id": request.session_id
        }
        
        response = self._simulate_api_call(self.api_endpoints["manager_notification"], payload)
        return response, response.get("notification_id")
    
    def _handle_risk_alert(self, request: ActionRequest) -> tuple[Dict[str, Any], str]:
        """Handle risk alert creation"""
        payload = {
            "risk_type": request.data.get("risk_type", "unknown"),
            "risk_level": request.priority,
            "source_data": request.data.get("source_data", {}),
            "anomalies": request.data.get("anomalies", []),
            "risk_score": request.data.get("risk_score", 0.5),
            "detection_agent": request.source_agent,
            "requires_investigation": request.priority in ["high", "critical"],
            "session_id": request.session_id
        }
        
        response = self._simulate_api_call(self.api_endpoints["risk_alert"], payload)
        return response, response.get("alert_id")
    
    def _handle_compliance_alert(self, request: ActionRequest) -> tuple[Dict[str, Any], str]:
        """Handle compliance alert"""
        payload = {
            "compliance_type": request.data.get("compliance_type", "general"),
            "regulatory_keywords": request.data.get("regulatory_keywords", []),
            "document_type": request.data.get("document_type", "unknown"),
            "severity": request.priority,
            "requires_audit": True,
            "session_id": request.session_id
        }
        
        response = self._simulate_api_call(self.api_endpoints["compliance_system"], payload)
        return response, response.get("compliance_case_id")
    
    def _handle_emergency_response(self, request: ActionRequest) -> tuple[Dict[str, Any], str]:
        """Handle emergency response action"""
        payload = {
            "emergency_type": request.data.get("emergency_type", "system_critical"),
            "severity": "critical",
            "impact_description": request.data.get("impact_description", "Critical system issue detected"),
            "immediate_action_required": True,
            "notify_on_call": True,
            "session_id": request.session_id
        }
        
        response = self._simulate_api_call(self.api_endpoints["emergency_response"], payload)
        return response, response.get("emergency_id")
    
    def _handle_block_transaction(self, request: ActionRequest) -> tuple[Dict[str, Any], str]:
        """Handle transaction blocking"""
        payload = {
            "transaction_id": request.data.get("transaction_id", "unknown"),
            "block_reason": request.data.get("block_reason", "risk_detected"),
            "risk_score": request.data.get("risk_score", 1.0),
            "anomalies": request.data.get("anomalies", []),
            "requires_manual_review": True,
            "session_id": request.session_id
        }
        
        # In a real system, this would call a payment processor API
        response = {
            "block_id": f"BLOCK-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "transaction_blocked": True,
            "customer_notified": True,
            "review_queue_added": True
        }
        
        return response, response.get("block_id")
    
    def _handle_flag_review(self, request: ActionRequest) -> tuple[Dict[str, Any], str]:
        """Handle flagging for manual review"""
        payload = {
            "review_type": request.data.get("review_type", "general"),
            "priority": request.priority,
            "flagged_content": request.data.get("content_summary", "Content flagged for review"),
            "flags": request.data.get("flags", []),
            "assigned_to": "review_team",
            "session_id": request.session_id
        }
        
        response = {
            "review_id": f"REV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "queue_position": 3,
            "estimated_review_time": "2-4 hours",
            "status": "queued"
        }
        
        return response, response.get("review_id")
    
    def _handle_log_warning(self, request: ActionRequest) -> tuple[Dict[str, Any], str]:
        """Handle warning logging"""
        payload = {
            "warning_type": request.data.get("warning_type", "general"),
            "message": request.data.get("message", "Warning detected by agent"),
            "source_agent": request.source_agent,
            "session_id": request.session_id,
            "metadata": request.context
        }
        
        response = self._simulate_api_call(self.api_endpoints["audit_log"], payload)
        return response, response.get("log_id")
    
    def _handle_normal_processing(self, request: ActionRequest) -> tuple[Dict[str, Any], str]:
        """Handle normal processing (no special action needed)"""
        response = {
            "status": "processed_normally",
            "message": "No special action required",
            "session_id": request.session_id,
            "processed_at": datetime.now().isoformat()
        }
        
        return response, f"NORMAL-{request.session_id}"
    
    def _store_action_result(self, result: ActionResult) -> None:
        """Store action result in memory store"""
        if not self.memory_store:
            return
        
        try:
            action_data = {
                "action_type": result.action_request.action_type.value,
                "status": result.status.value,
                "execution_time_ms": result.execution_time_ms,
                "external_reference_id": result.external_reference_id,
                "error_message": result.error_message,
                "response_data": json.dumps(result.response_data),
                "priority": result.action_request.priority,
                "source_agent": result.action_request.source_agent
            }
            
            from multi_agent_system.memory.memory_store import AgentAction, ActionStatus as MemoryActionStatus
            
            memory_action = AgentAction(
                agent_name=self.name,
                action_type=result.action_request.action_type.value,
                status=MemoryActionStatus.COMPLETED if result.status == ActionStatus.COMPLETED else MemoryActionStatus.FAILED,
                details=action_data,
                timestamp=result.completed_at
            )
            
            self.memory_store.store_agent_action(result.action_request.session_id, memory_action)
            
        except Exception as e:
            self.logger.error(f"Failed to store action result: {str(e)}")
    
    def retry_failed_action(self, failed_result: ActionResult) -> ActionResult:
        """Retry a failed action with exponential backoff"""
        request = failed_result.action_request
        
        if request.retry_count >= request.max_retries:
            self.logger.error(f"Max retries exceeded for action {request.action_type.value}")
            return failed_result
        
        # Exponential backoff
        wait_time = 2 ** request.retry_count
        time.sleep(wait_time)
        
        request.retry_count += 1
        self.logger.info(f"Retrying action {request.action_type.value} (attempt {request.retry_count})")
        
        return self.route_action(request)
    
    def create_action_from_agent_output(self, agent_name: str, agent_output: Dict[str, Any], 
                                      session_id: str) -> Optional[ActionRequest]:
        """
        Create an ActionRequest based on agent output
        This is the bridge between agent analysis and action execution
        """
        suggested_action = agent_output.get("suggested_action", "process_normally")
        
        # Map agent suggestions to action types
        action_mapping = {
            "escalate_to_crm": ActionType.ESCALATE_TO_CRM,
            "escalate_to_manager": ActionType.ESCALATE_TO_MANAGER,
            "escalate_compliance_review": ActionType.COMPLIANCE_ALERT,
            "emergency_response": ActionType.EMERGENCY_RESPONSE,
            "block_and_alert": ActionType.BLOCK_TRANSACTION,
            "flag_for_review": ActionType.FLAG_FOR_REVIEW,
            "flag_for_manual_review": ActionType.FLAG_FOR_REVIEW,
            "log_warning": ActionType.LOG_WARNING,
            "log_and_acknowledge": ActionType.LOG_WARNING,
            "process_normally": ActionType.PROCESS_NORMALLY
        }
        
        action_type = action_mapping.get(suggested_action, ActionType.PROCESS_NORMALLY)
        
        # Determine priority based on agent output
        priority = self._determine_priority(agent_output)
        
        # Create action request
        return ActionRequest(
            action_type=action_type,
            priority=priority,
            source_agent=agent_name,
            session_id=session_id,
            data=agent_output,
            context={"created_by": "action_router", "timestamp": datetime.now().isoformat()},
            timestamp=datetime.now()
        )
    
    def _determine_priority(self, agent_output: Dict[str, Any]) -> str:
        """Determine action priority based on agent output"""
        # Check for high-priority indicators
        if agent_output.get("requires_escalation", False):
            return "high"
        
        risk_score = agent_output.get("risk_score", 0.0)
        if risk_score >= 0.8:
            return "critical"
        elif risk_score >= 0.6:
            return "high"
        elif risk_score >= 0.3:
            return "medium"
        else:
            return "low"

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