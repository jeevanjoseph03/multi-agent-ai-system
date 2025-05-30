import json
import jsonschema
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class AnomalyType(Enum):
    FIELD_MISSING = "field_missing"
    TYPE_MISMATCH = "type_mismatch"
    VALUE_OUT_OF_RANGE = "value_out_of_range"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    SCHEMA_VIOLATION = "schema_violation"

@dataclass
class Anomaly:
    type: AnomalyType
    field: str
    expected: Any
    actual: Any
    severity: str
    description: str

@dataclass
class JSONAnalysis:
    is_valid: bool
    schema_compliance: bool
    anomalies: List[Anomaly]
    extracted_data: Dict[str, Any]
    risk_score: float
    suggested_action: str
    metadata: Dict[str, Any]

class JSONAgent:
    """
    JSON Agent that parses webhook data, validates schema,
    and flags anomalies for security/business logic
    """
    
    def __init__(self):
        self.name = "json_agent"
        self.expected_schemas = self._load_expected_schemas()
        self.business_rules = self._load_business_rules()
        self.suspicious_patterns = self._load_suspicious_patterns()
    
    def _load_expected_schemas(self) -> Dict[str, Dict]:
        """Load expected schemas for different types of webhook data"""
        return {
            "transaction": {
                "type": "object",
                "required": ["transaction_id", "amount", "user_id", "timestamp"],
                "properties": {
                    "transaction_id": {"type": "string"},
                    "amount": {"type": "number", "minimum": 0},
                    "user_id": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "currency": {"type": "string", "default": "USD"},
                    "status": {"type": "string", "enum": ["pending", "completed", "failed"]},
                    "metadata": {"type": "object"}
                }
            },
            "user_event": {
                "type": "object",
                "required": ["user_id", "event_type", "timestamp"],
                "properties": {
                    "user_id": {"type": "string"},
                    "event_type": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "ip_address": {"type": "string"},
                    "user_agent": {"type": "string"},
                    "session_id": {"type": "string"}
                }
            },
            "order": {
                "type": "object",
                "required": ["order_id", "customer_id", "total_amount"],
                "properties": {
                    "order_id": {"type": "string"},
                    "customer_id": {"type": "string"},
                    "total_amount": {"type": "number", "minimum": 0},
                    "items": {"type": "array"},
                    "shipping_address": {"type": "object"},
                    "payment_method": {"type": "string"}
                }
            }
        }
    
    def _load_business_rules(self) -> Dict[str, Any]:
        """Load business rules for validation"""
        return {
            "max_transaction_amount": 10000,
            "max_daily_transactions_per_user": 50,
            "suspicious_amount_threshold": 9999,
            "required_fields_transaction": ["transaction_id", "amount", "user_id"],
            "valid_currencies": ["USD", "EUR", "GBP", "CAD"],
            "max_string_length": 1000,
            "suspicious_user_patterns": ["test", "admin", "guest", "anonymous"]
        }
    
    def _load_suspicious_patterns(self) -> Dict[str, List[str]]:
        """Load patterns that might indicate fraudulent activity"""
        return {
            "suspicious_emails": [
                "test@", "admin@", "noreply@", "fake@", "spam@"
            ],
            "suspicious_user_ids": [
                "test", "admin", "guest", "user123", "anonymous", "temp"
            ],
            "suspicious_ip_patterns": [
                "127.0.0.1", "localhost", "0.0.0.0"
            ],
            "suspicious_amounts": [
                9999, 9999.99, 10000, 1234.56, 5555.55
            ]
        }
    
    def detect_schema_type(self, data: Dict[str, Any]) -> Optional[str]:
        """Automatically detect which schema this JSON data should follow"""
        if "transaction_id" in data and "amount" in data:
            return "transaction"
        elif "order_id" in data and "customer_id" in data:
            return "order"
        elif "user_id" in data and "event_type" in data:
            return "user_event"
        else:
            return None
    
    def validate_schema(self, data: Dict[str, Any], schema_type: str = None) -> Tuple[bool, List[str]]:
        """Validate JSON data against expected schema"""
        errors = []
        
        if not schema_type:
            schema_type = self.detect_schema_type(data)
        
        if not schema_type:
            return False, ["Cannot determine schema type for validation"]
        
        if schema_type not in self.expected_schemas:
            return False, [f"Unknown schema type: {schema_type}"]
        
        schema = self.expected_schemas[schema_type]
        
        try:
            jsonschema.validate(data, schema)
            return True, []
        except jsonschema.ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
            return False, errors
        except jsonschema.SchemaError as e:
            errors.append(f"Schema definition error: {e.message}")
            return False, errors
    
    def detect_anomalies(self, data: Dict[str, Any]) -> List[Anomaly]:
        """Detect various types of anomalies in the JSON data"""
        anomalies = []
        
        # Check for missing required fields
        schema_type = self.detect_schema_type(data)
        if schema_type and schema_type in self.expected_schemas:
            required_fields = self.expected_schemas[schema_type].get("required", [])
            for field in required_fields:
                if field not in data:
                    anomalies.append(Anomaly(
                        type=AnomalyType.FIELD_MISSING,
                        field=field,
                        expected=field,
                        actual="missing",
                        severity="high",
                        description=f"Required field '{field}' is missing"
                    ))
        
        # Check business rule violations
        if "amount" in data:
            amount = data["amount"]
            max_amount = self.business_rules["max_transaction_amount"]
            
            if isinstance(amount, (int, float)) and amount > max_amount:
                anomalies.append(Anomaly(
                    type=AnomalyType.VALUE_OUT_OF_RANGE,
                    field="amount",
                    expected=f"<= {max_amount}",
                    actual=amount,
                    severity="high",
                    description=f"Transaction amount {amount} exceeds maximum allowed {max_amount}"
                ))
            
            # Check for suspicious amounts
            if amount in self.suspicious_patterns["suspicious_amounts"]:
                anomalies.append(Anomaly(
                    type=AnomalyType.SUSPICIOUS_PATTERN,
                    field="amount",
                    expected="normal amount",
                    actual=amount,
                    severity="medium",
                    description=f"Amount {amount} matches suspicious pattern"
                ))
        
        # Check for suspicious user patterns
        if "user_id" in data:
            user_id = str(data["user_id"]).lower()
            for suspicious_pattern in self.suspicious_patterns["suspicious_user_ids"]:
                if suspicious_pattern in user_id:
                    anomalies.append(Anomaly(
                        type=AnomalyType.SUSPICIOUS_PATTERN,
                        field="user_id",
                        expected="normal user ID",
                        actual=data["user_id"],
                        severity="medium",
                        description=f"User ID contains suspicious pattern: {suspicious_pattern}"
                    ))
        
        # Check for type mismatches
        for field, value in data.items():
            if field == "amount" and not isinstance(value, (int, float)):
                anomalies.append(Anomaly(
                    type=AnomalyType.TYPE_MISMATCH,
                    field=field,
                    expected="number",
                    actual=type(value).__name__,
                    severity="medium",
                    description=f"Field '{field}' should be numeric but is {type(value).__name__}"
                ))
            
            # Check for suspiciously long strings
            if isinstance(value, str) and len(value) > self.business_rules["max_string_length"]:
                anomalies.append(Anomaly(
                    type=AnomalyType.VALUE_OUT_OF_RANGE,
                    field=field,
                    expected=f"<= {self.business_rules['max_string_length']} chars",
                    actual=f"{len(value)} chars",
                    severity="low",
                    description=f"String field '{field}' is suspiciously long ({len(value)} characters)"
                ))
        
        return anomalies
    
    def calculate_risk_score(self, anomalies: List[Anomaly]) -> float:
        """Calculate overall risk score based on anomalies"""
        if not anomalies:
            return 0.0
        
        severity_weights = {
            "low": 0.1,
            "medium": 0.3,
            "high": 0.6,
            "critical": 1.0
        }
        
        total_score = 0.0
        for anomaly in anomalies:
            weight = severity_weights.get(anomaly.severity, 0.1)
            total_score += weight
        
        # Normalize to 0-1 range
        max_possible_score = len(anomalies) * 1.0
        return min(total_score / max_possible_score, 1.0) if max_possible_score > 0 else 0.0
    
    def determine_action(self, risk_score: float, anomalies: List[Anomaly]) -> str:
        """Determine what action should be taken based on the analysis"""
        high_severity_count = sum(1 for a in anomalies if a.severity == "high")
        
        if risk_score >= 0.8 or high_severity_count >= 2:
            return "block_and_alert"
        elif risk_score >= 0.5 or high_severity_count >= 1:
            return "flag_for_review"
        elif risk_score >= 0.3:
            return "log_warning"
        else:
            return "process_normally"
    
    def extract_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract useful metadata from the JSON data"""
        metadata = {
            "field_count": len(data),
            "has_nested_objects": any(isinstance(v, dict) for v in data.values()),
            "has_arrays": any(isinstance(v, list) for v in data.values()),
            "estimated_size_kb": len(json.dumps(data)) / 1024,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add data type distribution
        type_counts = {}
        for value in data.values():
            type_name = type(value).__name__
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        metadata["type_distribution"] = type_counts
        
        return metadata
    
    def process_json(self, json_data: str) -> JSONAnalysis:
        """
        Main method to process JSON webhook data
        """
        try:
            # Parse JSON
            data = json.loads(json_data) if isinstance(json_data, str) else json_data
        except json.JSONDecodeError as e:
            return JSONAnalysis(
                is_valid=False,
                schema_compliance=False,
                anomalies=[Anomaly(
                    type=AnomalyType.SCHEMA_VIOLATION,
                    field="root",
                    expected="valid JSON",
                    actual="invalid JSON",
                    severity="critical",
                    description=f"JSON parsing failed: {str(e)}"
                )],
                extracted_data={},
                risk_score=1.0,
                suggested_action="reject_invalid_json",
                metadata={}
            )
        
        # Validate schema
        schema_valid, schema_errors = self.validate_schema(data)
        
        # Detect anomalies
        anomalies = self.detect_anomalies(data)
        
        # Add schema errors as anomalies
        for error in schema_errors:
            anomalies.append(Anomaly(
                type=AnomalyType.SCHEMA_VIOLATION,
                field="schema",
                expected="valid schema",
                actual="schema violation",
                severity="high",
                description=error
            ))
        
        # Calculate risk score
        risk_score = self.calculate_risk_score(anomalies)
        
        # Determine action
        suggested_action = self.determine_action(risk_score, anomalies)
        
        # Extract metadata
        metadata = self.extract_metadata(data)
        
        return JSONAnalysis(
            is_valid=True,
            schema_compliance=schema_valid,
            anomalies=anomalies,
            extracted_data=data,
            risk_score=risk_score,
            suggested_action=suggested_action,
            metadata=metadata
        )
    
    def get_extracted_fields(self, analysis: JSONAnalysis) -> Dict[str, Any]:
        """Convert analysis to dictionary for storage"""
        return {
            "is_valid_json": analysis.is_valid,
            "schema_compliant": analysis.schema_compliance,
            "anomaly_count": len(analysis.anomalies),
            "high_severity_anomalies": sum(1 for a in analysis.anomalies if a.severity == "high"),
            "risk_score": analysis.risk_score,
            "suggested_action": analysis.suggested_action,
            "field_count": analysis.metadata.get("field_count", 0),
            "estimated_size_kb": analysis.metadata.get("estimated_size_kb", 0),
            "has_nested_data": analysis.metadata.get("has_nested_objects", False),
            "processed_at": datetime.now().isoformat(),
            "anomaly_details": json.dumps([{
                "type": a.type.value,
                "field": a.field,
                "severity": a.severity,
                "description": a.description
            } for a in analysis.anomalies])
        }

# Example usage and testing
if __name__ == "__main__":
    json_agent = JSONAgent()
    
    # Test cases
    test_cases = [
        # Valid transaction
        {
            "transaction_id": "TXN-12345",
            "amount": 150.00,
            "user_id": "user_john_doe",
            "timestamp": "2024-01-15T10:30:00Z",
            "currency": "USD",
            "status": "completed"
        },
        
        # Suspicious high amount transaction
        {
            "transaction_id": "TXN-67890",
            "amount": 15000,  # Above threshold
            "user_id": "test_user",  # Suspicious pattern
            "timestamp": "2024-01-15T14:45:00Z"
        },
        
        # Invalid JSON structure
        '{"transaction_id": "TXN-99999", "amount": "not_a_number", "user_id": }',
        
        # Missing required fields
        {
            "amount": 100.00,
            "timestamp": "2024-01-15T16:20:00Z"
            # Missing transaction_id and user_id
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n=== JSON Test Case {i+1} ===")
        
        if isinstance(test_case, str):
            print(f"Input: {test_case}")
        else:
            print(f"Input: {json.dumps(test_case, indent=2)}")
        
        analysis = json_agent.process_json(test_case)
        
        print(f"Valid JSON: {analysis.is_valid}")
        print(f"Schema Compliant: {analysis.schema_compliance}")
        print(f"Risk Score: {analysis.risk_score:.2f}")
        print(f"Suggested Action: {analysis.suggested_action}")
        print(f"Anomalies Found: {len(analysis.anomalies)}")
        
        for anomaly in analysis.anomalies:
            print(f"  - {anomaly.severity.upper()}: {anomaly.description}")
        
        # Show extracted fields format
        fields = json_agent.get_extracted_fields(analysis)
        print(f"Extracted Fields: {len(fields)} fields captured")