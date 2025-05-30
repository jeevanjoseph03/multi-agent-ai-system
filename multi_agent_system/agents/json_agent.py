import json
from enum import Enum
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict

class JSONAnomalyType(Enum):
    SCHEMA_VIOLATION = "schema_violation" # Missing required field, wrong type
    BUSINESS_RULE_VIOLATION = "business_rule_violation" # e.g. amount too high
    UNEXPECTED_FIELD = "unexpected_field"
    INVALID_VALUE = "invalid_value" # e.g. negative amount where not allowed
    NONE = "none"

class JSONActionType(Enum):
    PROCESS_NORMALLY = "process_normally"
    LOG_WARNING = "log_warning_and_proceed"
    BLOCK_AND_ALERT = "block_and_alert" # For critical issues
    FLAG_FOR_MANUAL_REVIEW = "flag_for_manual_review"

@dataclass
class JSONAnalysis:
    is_valid_json: bool
    schema_validated: bool # True if passed schema checks
    anomalies_detected: List[Tuple[JSONAnomalyType, str]] # (AnomalyType, description)
    extracted_data_preview: Dict[str, Any] # Preview of key fields or all if small
    risk_score: float # 0.0 to 1.0, based on anomalies
    suggested_action: JSONActionType

class JSONAgent:
    def __init__(self):
        self.name = "json_agent"
        self.business_rules = self._load_business_rules() # Load predefined schemas/rules

    def _load_business_rules(self) -> Dict[str, Any]:
        # Example rules, can be loaded from a config file
        return {
            "transaction_schema": {
                "required_fields": ["transaction_id", "amount", "user_id", "timestamp"],
                "field_types": {
                    "transaction_id": str,
                    "amount": (int, float),
                    "user_id": str,
                    "timestamp": str # Could add regex validation for timestamp format
                },
                "allowed_flags": ["high_amount", "suspicious_user", "new_device", "foreign_ip"] # Example
            },
            "user_profile_schema": {
                "required_fields": ["user_id", "email", "created_at"],
                "field_types": {"user_id": str, "email": str, "created_at": str}
            },
            "generic_webhook_min_fields": ["event_type", "payload", "received_at"]
        }

    def _validate_schema(self, data: Dict[str, Any], schema_name: str = "transaction_schema") -> List[Tuple[JSONAnomalyType, str]]:
        anomalies = []
        schema = self.business_rules.get(schema_name)
        if not schema:
            anomalies.append((JSONAnomalyType.SCHEMA_VIOLATION, f"Schema '{schema_name}' not found."))
            return anomalies

        # Check required fields
        for req_field in schema.get("required_fields", []):
            if req_field not in data:
                anomalies.append((JSONAnomalyType.SCHEMA_VIOLATION, f"Missing required field: '{req_field}'"))
        
        # Check field types
        field_types = schema.get("field_types", {})
        for field, expected_type in field_types.items():
            if field in data and not isinstance(data[field], expected_type):
                anomalies.append((JSONAnomalyType.SCHEMA_VIOLATION, f"Invalid type for field '{field}'. Expected {expected_type}, got {type(data[field])}"))

        # Check for unexpected fields (optional, based on strictness)
        # known_fields = set(schema.get("required_fields", [])) | set(field_types.keys())
        # for field in data.keys():
        #     if field not in known_fields:
        #         anomalies.append((JSONAnomalyType.UNEXPECTED_FIELD, f"Unexpected field: '{field}'"))
        
        return anomalies

    def _detect_business_anomalies(self, data: Dict[str, Any], schema_name: str = "transaction_schema") -> List[Tuple[JSONAnomalyType, str]]:
        anomalies = []
        # Example: Transaction specific rules
        if schema_name == "transaction_schema":
            amount = data.get("amount")
            if isinstance(amount, (int, float)):
                if amount < 0:
                    anomalies.append((JSONAnomalyType.INVALID_VALUE, "Transaction amount cannot be negative."))
                if amount > 50000: # Example high value threshold
                    anomalies.append((JSONAnomalyType.BUSINESS_RULE_VIOLATION, "Transaction amount exceeds high value threshold ($50,000)."))
            
            flags = data.get("flags")
            if flags and isinstance(flags, list):
                allowed_flags = self.business_rules.get(schema_name, {}).get("allowed_flags", [])
                for flag_val in flags:
                    if flag_val not in allowed_flags:
                         anomalies.append((JSONAnomalyType.INVALID_VALUE, f"Invalid flag '{flag_val}' detected in transaction."))


        # Add more business rule checks here based on schema_name or data content
        return anomalies

    def _calculate_risk_score(self, anomalies: List[Tuple[JSONAnomalyType, str]]) -> float:
        score = 0.0
        if not anomalies:
            return score
        
        for anomaly_type, _ in anomalies:
            if anomaly_type == JSONAnomalyType.SCHEMA_VIOLATION:
                score += 0.3
            elif anomaly_type == JSONAnomalyType.BUSINESS_RULE_VIOLATION:
                score += 0.5
            elif anomaly_type == JSONAnomalyType.INVALID_VALUE:
                score += 0.4
            elif anomaly_type == JSONAnomalyType.UNEXPECTED_FIELD:
                score += 0.1
        return min(score, 1.0)

    def _determine_action(self, risk_score: float, anomalies: List[Tuple[JSONAnomalyType, str]]) -> JSONActionType:
        if risk_score >= 0.7:
            return JSONActionType.BLOCK_AND_ALERT
        if risk_score >= 0.4:
            return JSONActionType.FLAG_FOR_MANUAL_REVIEW
        if anomalies: # Any anomaly, even low risk
            return JSONActionType.LOG_WARNING
        return JSONActionType.PROCESS_NORMALLY

    def process_json(self, json_string: str, schema_to_validate: Optional[str] = "transaction_schema") -> JSONAnalysis:
        try:
            data = json.loads(json_string)
            is_valid_json = True
        except json.JSONDecodeError as e:
            return JSONAnalysis(
                is_valid_json=False,
                schema_validated=False,
                anomalies_detected=[(JSONAnomalyType.SCHEMA_VIOLATION, f"Invalid JSON format: {e}")],
                extracted_data_preview={"error": "Invalid JSON string"},
                risk_score=1.0, # Max risk for unparseable JSON
                suggested_action=JSONActionType.BLOCK_AND_ALERT
            )

        all_anomalies = []
        schema_validated_successfully = False

        if schema_to_validate: # If a specific schema is provided for validation
            schema_anomalies = self._validate_schema(data, schema_to_validate)
            all_anomalies.extend(schema_anomalies)
            if not schema_anomalies: # Only true if no schema anomalies for the *specified* schema
                schema_validated_successfully = True
        else: # No specific schema, perhaps just generic checks or rely on business anomalies
            schema_validated_successfully = True # Or False if you expect a schema always

        business_anomalies = self._detect_business_anomalies(data, schema_to_validate if schema_to_validate else "generic_webhook_min_fields") # Fallback schema for business rules
        all_anomalies.extend(business_anomalies)
        
        risk_score = self._calculate_risk_score(all_anomalies)
        action = self._determine_action(risk_score, all_anomalies)

        # Create a preview (e.g., first 5 keys or specific important keys)
        preview_keys = list(data.keys())[:5]
        data_preview = {k: data[k] for k in preview_keys}
        if len(data.keys()) > 5:
            data_preview["..."] = f"{len(data.keys()) - 5} more fields"


        return JSONAnalysis(
            is_valid_json=is_valid_json,
            schema_validated=schema_validated_successfully,
            anomalies_detected=all_anomalies if all_anomalies else [(JSONAnomalyType.NONE, "No anomalies detected")],
            extracted_data_preview=data_preview,
            risk_score=risk_score,
            suggested_action=action
        )

    def get_extracted_fields(self, analysis_result: JSONAnalysis) -> Dict[str, Any]:
        """Converts JSONAnalysis to a dictionary for storage/response."""
        result_dict = asdict(analysis_result)
        # Convert enums to their string values
        result_dict["anomalies_detected"] = [(anomaly[0].value, anomaly[1]) for anomaly in analysis_result.anomalies_detected]
        result_dict["suggested_action"] = analysis_result.suggested_action.value
        return result_dict

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
        
        print(f"Valid JSON: {analysis.is_valid_json}")
        print(f"Schema Validated: {analysis.schema_validated}")
        print(f"Risk Score: {analysis.risk_score:.2f}")
        print(f"Suggested Action: {analysis.suggested_action}")
        print(f"Anomalies Found: {len(analysis.anomalies_detected)}")
        
        for anomaly in analysis.anomalies_detected:
            print(f"  - {anomaly[0].name}: {anomaly[1]}")
        
        # Show extracted fields format
        fields = json_agent.get_extracted_fields(analysis)
        print(f"Extracted Fields: {len(fields)} fields captured")