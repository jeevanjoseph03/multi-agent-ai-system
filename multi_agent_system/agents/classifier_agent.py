from typing import Dict, Any, Tuple, List
import json
import re
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class FormatType(Enum):
    EMAIL = "email"
    JSON = "json"
    PDF = "pdf"
    UNKNOWN = "unknown"

class IntentType(Enum):
    RFQ = "rfq"  # Request for Quote
    COMPLAINT = "complaint"
    INVOICE = "invoice"
    REGULATION = "regulation"
    FRAUD_RISK = "fraud_risk"
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
        self.few_shot_examples = self._load_few_shot_examples()
    
    def _load_format_patterns(self) -> Dict[FormatType, List[str]]:
        """Load patterns to identify different formats"""
        return {
            FormatType.EMAIL: [
                r'from:\s*[\w\.-]+@[\w\.-]+',
                r'to:\s*[\w\.-]+@[\w\.-]+',
                r'subject:\s*.+',
                r'dear\s+\w+',
                r'sincerely',
                r'best regards'
            ],
            FormatType.JSON: [
                r'^\s*\{.*\}\s*$',
                r'"[\w_]+"\s*:\s*',
                r'\[.*\]',
                r'null|true|false'
            ],
            FormatType.PDF: [
                r'%PDF-',
                r'invoice\s+#?\d+',
                r'total\s+amount',
                r'policy\s+document',
                r'regulation\s+\d+'
            ]
        }
    
    def _load_intent_keywords(self) -> Dict[IntentType, List[str]]:
        """Load keywords that indicate different business intents"""
        return {
            IntentType.RFQ: [
                'quote', 'quotation', 'proposal', 'bid', 'pricing',
                'cost estimate', 'request for proposal', 'rfp', 'rfq'
            ],
            IntentType.COMPLAINT: [
                'complaint', 'issue', 'problem', 'dissatisfied', 'angry',
                'upset', 'disappointed', 'terrible', 'awful', 'refund',
                'escalate', 'manager', 'unacceptable'
            ],
            IntentType.INVOICE: [
                'invoice', 'bill', 'payment', 'amount due', 'total',
                'subtotal', 'tax', 'billing', 'charge'
            ],
            IntentType.REGULATION: [
                'regulation', 'compliance', 'gdpr', 'fda', 'policy',
                'legal', 'regulatory', 'audit', 'standard'
            ],
            IntentType.FRAUD_RISK: [
                'fraud', 'suspicious', 'unauthorized', 'breach', 'security',
                'phishing', 'scam', 'identity theft', 'anomaly'
            ]
        }
    
    def _load_few_shot_examples(self) -> List[Dict[str, Any]]:
        """Load few-shot examples for better classification"""
        return [
            {
                "text": "Dear Sir, I am writing to request a quote for 100 units of your product X",
                "format": FormatType.EMAIL.value,
                "intent": IntentType.RFQ.value
            },
            {
                "text": "I am extremely dissatisfied with my recent purchase. The product arrived damaged.",
                "format": FormatType.EMAIL.value,
                "intent": IntentType.COMPLAINT.value
            },
            {
                "text": '{"order_id": "12345", "amount": 15000, "status": "suspicious"}',
                "format": FormatType.JSON.value,
                "intent": IntentType.FRAUD_RISK.value
            },
            {
                "text": "Invoice #INV-2024-001\nTotal Amount: $12,500.00\nDue Date: 2024-01-15",
                "format": FormatType.PDF.value,
                "intent": IntentType.INVOICE.value
            }
        ]
    
    def classify_format(self, content: str) -> Tuple[FormatType, float]:
        """Classify the format of the input content"""
        content_lower = content.lower().strip()
        format_scores = {}
        
        for format_type, patterns in self.format_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content_lower, re.IGNORECASE))
                score += matches
            
            # Normalize score
            format_scores[format_type] = score / len(patterns) if patterns else 0
        
        # Additional heuristics
        if content_lower.startswith('{') and content_lower.endswith('}'):
            format_scores[FormatType.JSON] += 2
        
        if 'from:' in content_lower and 'to:' in content_lower:
            format_scores[FormatType.EMAIL] += 2
            
        if '%pdf' in content_lower or 'invoice' in content_lower:
            format_scores[FormatType.PDF] += 1
        
        # Find best format
        best_format = max(format_scores.items(), key=lambda x: x[1])
        
        if best_format[1] > 0:
            return best_format[0], min(best_format[1] / 3, 1.0)  # Cap at 1.0
        else:
            return FormatType.UNKNOWN, 0.0
    
    def classify_intent(self, content: str) -> Tuple[IntentType, float]:
        """Classify the business intent of the content"""
        content_lower = content.lower()
        intent_scores = {}
        
        for intent_type, keywords in self.intent_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    score += 1
            
            # Normalize score
            intent_scores[intent_type] = score / len(keywords) if keywords else 0
        
        # Additional context-based scoring
        if any(word in content_lower for word in ['angry', 'terrible', 'awful']):
            intent_scores[IntentType.COMPLAINT] += 0.5
            
        if any(word in content_lower for word in ['$', 'amount', 'total']) and \
           any(word in content_lower for word in ['invoice', 'bill']):
            intent_scores[IntentType.INVOICE] += 0.5
        
        # Find best intent
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        
        if best_intent[1] > 0:
            return best_intent[0], min(best_intent[1], 1.0)
        else:
            return IntentType.UNKNOWN, 0.0
    
    def classify(self, content: str, filename: str = None) -> ClassificationResult:
        """
        Main classification method that determines both format and intent
        """
        # Classify format
        format_type, format_confidence = self.classify_format(content)
        
        # Classify intent
        intent_type, intent_confidence = self.classify_intent(content)
        
        # Use filename as additional hint
        if filename:
            filename_lower = filename.lower()
            if filename_lower.endswith('.json'):
                format_type = FormatType.JSON
                format_confidence = max(format_confidence, 0.8)
            elif filename_lower.endswith('.pdf'):
                format_type = FormatType.PDF
                format_confidence = max(format_confidence, 0.8)
            elif filename_lower.endswith(('.eml', '.msg', '.txt')):
                format_type = FormatType.EMAIL
                format_confidence = max(format_confidence, 0.7)
        
        # Calculate overall confidence
        overall_confidence = (format_confidence + intent_confidence) / 2
        
        # Generate reasoning
        reasoning = f"Format detected as {format_type.value} (confidence: {format_confidence:.2f}), " \
                   f"Intent detected as {intent_type.value} (confidence: {intent_confidence:.2f})"
        
        return ClassificationResult(
            format_type=format_type,
            intent=intent_type,
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