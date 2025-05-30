from typing import Dict, Any, Tuple, List
import json
import re
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class FormatType(Enum):
    EMAIL = "email"
    JSON = "json"
    PDF = "pdf" # Represents PDF-like text content or actual PDFs
    UNKNOWN = "unknown"

class IntentType(Enum):
    RFQ = "rfq"
    COMPLAINT = "complaint"
    INVOICE = "invoice"
    REGULATION = "regulation" # For policy documents, compliance checks
    FRAUD_RISK = "fraud_risk"
    GENERAL_QUERY = "general_query"
    TRANSACTION_DATA = "transaction_data" # For generic JSON data
    UNKNOWN = "unknown"

@dataclass
class ClassificationResult:
    format_type: FormatType
    intent: IntentType
    confidence: float
    reasoning: str

class ClassifierAgent:
    """
    Classifier Agent that detects format and business intent using
    few-shot examples and schema matching
    """
    
    def __init__(self):
        self.name = "classifier_agent"
        self.format_patterns = self._load_format_patterns()
        self.intent_keywords = self._load_intent_keywords()
        # self.few_shot_examples = self._load_few_shot_examples() # Present but not directly used in this rule-based version
    
    def _load_format_patterns(self) -> Dict[FormatType, List[str]]:
        """Load patterns to identify different formats"""
        return {
            FormatType.EMAIL: [
                r'^from\s*:\s*[\w\.-]+@[\w\.-]+',
                r'^to\s*:\s*[\w\.-]+@[\w\.-]+',
                r'^subject\s*:\s*.+',
                r'\b(dear|sincerely|best regards|yours truly)\b'
            ],
            FormatType.JSON: [
                r'^\s*\{.*\}\s*$', # Starts with { and ends with }
                r'^\s*\[.*\]\s*$'  # Starts with [ and ends with ]
            ],
            FormatType.PDF: [ # Patterns for text that looks like it came from a PDF document
                r'\binvoice\s*#',
                r'\b(bill\s+to|ship\s+to)\s*:',
                r'\b(total\s+amount|grand\s+total|total\s+due)\s*[:\s]*\$?\s*\d[\d,\.]*',
                r'\b(subtotal|sub-total)\s*[:\s]*\$?\s*\d[\d,\.]*',
                r'\b(due\s+date|payment\s+due)\s*:',
                r'\b(privacy\s+policy|terms\s+and\s+conditions|terms\s+of\s+service)\b',
                r'\b(gdpr|ccpa|hipaa|fda|regulation|compliance|article\s+\d+)\b',
                r'effective\s+date\s*:'
            ]
        }
    
    def _load_intent_keywords(self) -> Dict[IntentType, List[str]]:
        """Load keywords that indicate different business intents"""
        return {
            IntentType.RFQ: [r'\b(request\s+for\s+quotation|rfq|quote|proposal|pricing)\b'],
            IntentType.COMPLAINT: [r'\b(complaint|dissatisfied|unhappy|poor\s+service|issue|problem|escalate|refund)\b', r'\b(terrible|awful|furious|bad\s+experience)\b'],
            IntentType.INVOICE: [r'\b(invoice|bill|payment\s+due|statement\s+of\s+account)\b', r'invoice\s*#'],
            IntentType.REGULATION: [r'\b(regulation|compliance|policy|gdpr|ccpa|hipaa|fda|terms\s+of\s+service|privacy\s+statement|article\s+\d+)\b'],
            IntentType.FRAUD_RISK: [r'\b(fraud|suspicious|unauthorized|risk|alert|anomaly|potential\s+threat)\b', r'transaction_id.*(sus|test|risky)'],
            IntentType.TRANSACTION_DATA: [r'"transaction_id":', r'"amount":', r'"user_id":', r'"order_id":'],
            IntentType.GENERAL_QUERY: [r'\b(how\s+to|what\s+is|can\s+you|information|details|question)\b'],
        }
    
    # def _load_few_shot_examples(self) -> List[Dict[str, Any]]:
    #     # This would be used if a more advanced classification (e.g., LLM-based) was implemented
    #     return [
    #         {"text": "Subject: Urgent: Invoice #123 Payment Overdue", "format": FormatType.EMAIL, "intent": IntentType.INVOICE},
    #         {"text": "{\"user_id\": \"usr123\", \"action\": \"login_failed\", \"ip\": \"1.2.3.4\"}", "format": FormatType.JSON, "intent": IntentType.FRAUD_RISK},
    #         {"text": "Our company privacy policy has been updated...", "format": FormatType.PDF, "intent": IntentType.REGULATION}, # Assuming text from a PDF
    #     ]

    def classify_format(self, content: str) -> Tuple[FormatType, float]:
        content_lower = content.lower().strip()

        if not content_lower:
            return FormatType.UNKNOWN, 0.0

        # 1. JSON detection (high confidence if structure matches)
        if content_lower.startswith('{') and content_lower.endswith('}'):
            try:
                json.loads(content)
                return FormatType.JSON, 1.0 # Valid JSON
            except json.JSONDecodeError:
                return FormatType.JSON, 0.7 # Looks like JSON but invalid
        if content_lower.startswith('[') and content_lower.endswith(']'):
            try:
                json.loads(content)
                return FormatType.JSON, 1.0 # Valid JSON array
            except json.JSONDecodeError:
                return FormatType.JSON, 0.7 # Looks like JSON array but invalid

        # 2. Score PDF-like and Email content
        pdf_score = 0
        for pattern in self.format_patterns[FormatType.PDF]:
            if re.search(pattern, content_lower, re.IGNORECASE | re.MULTILINE):
                pdf_score += 1
        
        email_score = 0
        # Email headers are strong indicators
        if re.search(r'^from\s*:\s*[\w\.-]+@[\w\.-]+', content, re.IGNORECASE | re.MULTILINE): email_score += 2
        if re.search(r'^to\s*:\s*[\w\.-]+@[\w\.-]+', content, re.IGNORECASE | re.MULTILINE): email_score += 2
        if re.search(r'^subject\s*:\s*.+', content, re.IGNORECASE | re.MULTILINE): email_score += 2
        # Email body keywords
        for pattern in self.format_patterns[FormatType.EMAIL]:
             if re.search(pattern, content_lower, re.IGNORECASE | re.MULTILINE):
                email_score += 0.5 # Body keywords are weaker than headers

        # Decision Logic
        if pdf_score >= 2 and pdf_score > email_score: # Needs at least 2 strong PDF indicators
            return FormatType.PDF, min(pdf_score / 4.0, 1.0)
        if email_score >= 3: # Needs strong email header presence
            return FormatType.EMAIL, min(email_score / 5.0, 1.0)
        if pdf_score > 0: # Fallback if some PDF indicators exist
             return FormatType.PDF, min(pdf_score / 4.0, 1.0)
        if email_score > 0: # Fallback if some email indicators exist
            return FormatType.EMAIL, min(email_score / 5.0, 1.0)

        return FormatType.UNKNOWN, 0.0
    
    def classify_intent(self, content: str, classified_format: FormatType) -> Tuple[IntentType, float]:
        content_lower = content.lower().strip()
        intent_scores: Dict[IntentType, float] = {intent: 0.0 for intent in IntentType}
        
        if not content_lower:
            return IntentType.UNKNOWN, 0.0

        for intent, patterns in self.intent_keywords.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    intent_scores[intent] += 1
        
        # Adjust scores based on format
        if classified_format == FormatType.JSON:
            if intent_scores.get(IntentType.TRANSACTION_DATA, 0) > 0 or intent_scores.get(IntentType.FRAUD_RISK, 0) > 0:
                 # Prioritize these for JSON
                if intent_scores.get(IntentType.TRANSACTION_DATA, 0) >= intent_scores.get(IntentType.FRAUD_RISK, 0):
                    intent_scores[IntentType.TRANSACTION_DATA] += 1
                else:
                    intent_scores[IntentType.FRAUD_RISK] +=1
            elif not any(score > 0 for score in intent_scores.values()): # If no other intent, default to transaction
                intent_scores[IntentType.TRANSACTION_DATA] = 1


        if classified_format == FormatType.PDF:
            if intent_scores.get(IntentType.INVOICE, 0) > 0 or intent_scores.get(IntentType.REGULATION, 0) > 0:
                # Prioritize these for PDF
                if intent_scores.get(IntentType.INVOICE, 0) >= intent_scores.get(IntentType.REGULATION, 0):
                     intent_scores[IntentType.INVOICE] +=1
                else:
                    intent_scores[IntentType.REGULATION] +=1
            elif not any(score > 0 for score in intent_scores.values()): # Default for PDF if nothing else matches
                intent_scores[IntentType.REGULATION] = 1


        if classified_format == FormatType.EMAIL:
            # For emails, complaint, RFQ, or general query are common
            if not any(score > 0 for score in intent_scores.values()):
                intent_scores[IntentType.GENERAL_QUERY] = 1


        best_intent = IntentType.UNKNOWN
        max_score = 0.0
        if any(score > 0 for score in intent_scores.values()):
            # Sort by score, then alphabetically for tie-breaking (less important here)
            sorted_intents = sorted(intent_scores.items(), key=lambda item: item[1], reverse=True)
            best_intent = sorted_intents[0][0]
            max_score = sorted_intents[0][1]
            # Basic confidence, can be improved
            confidence = min(max_score / 3.0, 1.0) if max_score > 0 else 0.0
            return best_intent, confidence

        return IntentType.UNKNOWN, 0.0

    def classify(self, content: str, filename: str = None) -> ClassificationResult:
        """
        Main classification method that determines both format and intent
        """
        # Try to infer format from filename extension if content classification is weak
        file_format_from_ext = FormatType.UNKNOWN
        if filename:
            if filename.lower().endswith(".json"):
                file_format_from_ext = FormatType.JSON
            elif filename.lower().endswith(".eml") or filename.lower().endswith(".msg"):
                file_format_from_ext = FormatType.EMAIL
            elif filename.lower().endswith(".pdf") or filename.lower().endswith(".txt"): # Treat .txt as potential PDF content
                file_format_from_ext = FormatType.PDF

        format_type, format_confidence = self.classify_format(content)

        # If content-based classification is UNKNOWN or low confidence, and filename suggests a format, use it.
        if (format_type == FormatType.UNKNOWN or format_confidence < 0.5) and file_format_from_ext != FormatType.UNKNOWN:
            final_format_type = file_format_from_ext
            format_reasoning = f"Format inferred from filename '{filename}' as {final_format_type.value} (content analysis was {format_type.value} with conf {format_confidence:.2f})."
            format_confidence = 0.7 # Assign a moderate confidence for filename-based
        else:
            final_format_type = format_type
            format_reasoning = f"Format detected from content as {final_format_type.value} (confidence: {format_confidence:.2f})."


        intent, intent_confidence = self.classify_intent(content, final_format_type)
        intent_reasoning = f"Intent detected as {intent.value} (confidence: {intent_confidence:.2f} based on format {final_format_type.value})."

        overall_confidence = (format_confidence + intent_confidence) / 2
        
        reasoning = f"{format_reasoning} {intent_reasoning}"

        return ClassificationResult(
            format_type=final_format_type,
            intent=intent,
            confidence=overall_confidence,
            reasoning=reasoning
        )
    
    def get_routing_metadata(self, classification: ClassificationResult) -> Dict[str, Any]:
        """Generate routing metadata for other agents"""
        return {
            "agent_name": self.name,
            "format_type": classification.format_type.value,
            "intent": classification.intent.value,
            "confidence": classification.confidence,
            "reasoning": classification.reasoning,
            "timestamp": datetime.now().isoformat(),
            "route_to_agent": f"{classification.format_type.value}_agent"
        }

# Example usage and testing
if __name__ == "__main__":
    classifier = ClassifierAgent()
    
    # Test different types of content
    test_cases = [
        {
            "content": """From: angry.customer@example.com
To: support@company.com
Subject: Terrible Product Quality

Dear Support Team,

I am extremely dissatisfied with my recent purchase. The product arrived damaged and doesn't work as advertised. This is completely unacceptable and I demand a full refund immediately.

Best regards,
John Doe""",
            "filename": "complaint.eml"
        },
        {
            "content": '{"transaction_id": "TXN-123456", "amount": 15000, "user_id": "suspicious_user", "flags": ["high_amount", "new_user"]}',
            "filename": "webhook_data.json"
        },
        {
            "content": """Invoice #INV-2024-001
Date: January 15, 2024
Total Amount: $12,500.00
Due Date: February 15, 2024

Line Items:
- Product A: $10,000.00
- Product B: $2,500.00""",
            "filename": "invoice.pdf"
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n--- Test Case {i+1} ---")
        print(f"Content: {test_case['content'][:100]}...")
        print(f"Filename: {test_case['filename']}")
        
        result = classifier.classify(test_case['content'], test_case['filename'])
        print(f"Classification Result:")
        print(f"  Format: {result.format_type.value}")
        print(f"  Intent: {result.intent.value}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Reasoning: {result.reasoning}")
        
        routing_metadata = classifier.get_routing_metadata(result)
        print(f"  Route to: {routing_metadata['route_to_agent']}")