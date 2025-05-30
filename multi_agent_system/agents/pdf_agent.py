import PyPDF2
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import io

class DocumentType(Enum):
    INVOICE = "invoice"
    POLICY = "policy"
    CONTRACT = "contract"
    REGULATION = "regulation"
    UNKNOWN = "unknown"

class RiskFlag(Enum):
    HIGH_AMOUNT = "high_amount"
    REGULATORY_MENTION = "regulatory_mention"
    COMPLIANCE_ISSUE = "compliance_issue"
    SUSPICIOUS_CONTENT = "suspicious_content"

@dataclass
class PDFFlag:
    flag_type: RiskFlag
    field: str
    value: Any
    threshold: Any
    severity: str
    description: str

@dataclass
class PDFAnalysis:
    document_type: DocumentType
    extracted_text: str
    structured_data: Dict[str, Any]
    flags: List[PDFFlag]
    compliance_keywords: List[str]
    risk_score: float
    suggested_action: str
    metadata: Dict[str, Any]

class PDFAgent:
    """
    PDF Agent that extracts fields from PDF documents,
    detects document types, and flags compliance/risk issues
    """
    
    def __init__(self):
        self.name = "pdf_agent"
        self.document_patterns = self._load_document_patterns()
        self.compliance_keywords = self._load_compliance_keywords()
        self.extraction_patterns = self._load_extraction_patterns()
        self.risk_thresholds = self._load_risk_thresholds()
    
    def _load_document_patterns(self) -> Dict[DocumentType, List[str]]:
        """Patterns to identify different document types"""
        return {
            DocumentType.INVOICE: [
                r'invoice\s*#?\s*\d+',
                r'bill\s+to',
                r'total\s+amount',
                r'due\s+date',
                r'subtotal',
                r'tax\s+amount',
                r'payment\s+terms'
            ],
            DocumentType.POLICY: [
                r'policy\s+document',
                r'terms\s+and\s+conditions',
                r'privacy\s+policy',
                r'data\s+protection',
                r'user\s+agreement',
                r'service\s+agreement'
            ],
            DocumentType.CONTRACT: [
                r'contract\s+agreement',
                r'party\s+of\s+the\s+first\s+part',
                r'whereas\s+clause',
                r'signature\s+date',
                r'terms\s+of\s+agreement',
                r'effective\s+date'
            ],
            DocumentType.REGULATION: [
                r'regulation\s+\d+',
                r'compliance\s+requirements',
                r'regulatory\s+framework',
                r'legal\s+obligations',
                r'statutory\s+requirements'
            ]
        }
    
    def _load_compliance_keywords(self) -> List[str]:
        """Keywords that indicate regulatory/compliance content"""
        return [
            'gdpr', 'general data protection regulation',
            'fda', 'food and drug administration',
            'sox', 'sarbanes-oxley',
            'hipaa', 'health insurance portability',
            'pci dss', 'payment card industry',
            'iso 27001', 'iso27001',
            'ccpa', 'california consumer privacy act',
            'ferpa', 'family educational rights',
            'glba', 'gramm-leach-bliley act',
            'compliance', 'regulatory', 'audit',
            'data protection', 'privacy policy',
            'information security', 'risk management'
        ]
    
    def _load_extraction_patterns(self) -> Dict[str, str]:
        """Regex patterns for extracting structured data"""
        return {
            # Invoice patterns
            'invoice_number': r'invoice\s*#?\s*:?\s*([A-Z0-9\-]+)',
            'invoice_date': r'(?:invoice\s+date|date)\s*:?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            'due_date': r'due\s+date\s*:?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            'total_amount': r'total\s+(?:amount\s+)?(?:due\s+)?:?\s*\$?\s*([\d,]+\.?\d*)',
            'subtotal': r'subtotal\s*:?\s*\$?\s*([\d,]+\.?\d*)',
            'tax_amount': r'tax\s*(?:amount\s*)?:?\s*\$?\s*([\d,]+\.?\d*)',
            
            # General patterns
            'email': r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            'phone': r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})',
            'amount': r'\$\s*([\d,]+\.?\d*)',
            'date': r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            'percentage': r'(\d+\.?\d*)\s*%',
            
            # Policy/Contract patterns
            'effective_date': r'effective\s+date\s*:?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            'expiration_date': r'expir(?:ation|y)\s+date\s*:?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})'
        }
    
    def _load_risk_thresholds(self) -> Dict[str, Any]:
        """Thresholds for flagging risks"""
        return {
            'max_invoice_amount': 10000,
            'suspicious_amounts': [9999, 9999.99, 10000, 5000],
            'compliance_flag_keywords': ['gdpr', 'fda', 'hipaa', 'sox'],
            'max_document_age_days': 365,
            'min_confidence_threshold': 0.7
        }
    
    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text content from PDF bytes"""
        try:
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            
            return text.strip()
        
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                return self.extract_text_from_pdf(file.read())
        except Exception as e:
            raise Exception(f"Failed to read PDF file {file_path}: {str(e)}")
    
    def detect_document_type(self, text: str) -> Tuple[DocumentType, float]:
        """Detect the type of document based on content"""
        text_lower = text.lower()
        type_scores = {}
        
        for doc_type, patterns in self.document_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                score += matches
            
            # Normalize score
            type_scores[doc_type] = score / len(patterns) if patterns else 0
        
        # Find best match
        if not type_scores or all(score == 0 for score in type_scores.values()):
            return DocumentType.UNKNOWN, 0.0
        
        best_type = max(type_scores.items(), key=lambda x: x[1])
        confidence = min(best_type[1], 1.0)
        
        return best_type[0], confidence
    
    def extract_structured_data(self, text: str, document_type: DocumentType) -> Dict[str, Any]:
        """Extract structured fields based on document type"""
        extracted_data = {}
        text_lower = text.lower()
        
        # Extract using regex patterns
        for field_name, pattern in self.extraction_patterns.items():
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                # Take the first match, clean it up
                value = matches[0].strip().replace(',', '')
                
                # Try to convert numbers
                if field_name.endswith('_amount') or field_name == 'total_amount':
                    try:
                        extracted_data[field_name] = float(value)
                    except ValueError:
                        extracted_data[field_name] = value
                else:
                    extracted_data[field_name] = value
        
        # Document-specific extraction
        if document_type == DocumentType.INVOICE:
            extracted_data.update(self._extract_invoice_line_items(text))
        elif document_type == DocumentType.POLICY:
            extracted_data.update(self._extract_policy_details(text))
        
        return extracted_data
    
    def _extract_invoice_line_items(self, text: str) -> Dict[str, Any]:
        """Extract line items from invoice"""
        line_items = []
        lines = text.split('\n')
        
        # Look for line item patterns
        item_pattern = r'(.+?)\s+(\d+)\s+\$?([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)'
        
        for line in lines:
            match = re.search(item_pattern, line.strip())
            if match:
                line_items.append({
                    'description': match.group(1).strip(),
                    'quantity': int(match.group(2)),
                    'unit_price': float(match.group(3).replace(',', '')),
                    'total': float(match.group(4).replace(',', ''))
                })
        
        return {
            'line_items': line_items,
            'line_item_count': len(line_items)
        }
    
    def _extract_policy_details(self, text: str) -> Dict[str, Any]:
        """Extract policy-specific information"""
        policy_data = {}
        
        # Look for policy sections
        sections = re.findall(r'(\d+\.?\s+[A-Z][^.]+)', text)
        policy_data['sections'] = sections[:10]  # First 10 sections
        
        # Look for data retention periods
        retention_pattern = r'retain.*?(\d+)\s+(days?|months?|years?)'
        retention_matches = re.findall(retention_pattern, text.lower())
        if retention_matches:
            policy_data['retention_periods'] = retention_matches
        
        return policy_data
    
    def detect_compliance_issues(self, text: str) -> List[str]:
        """Detect compliance-related keywords"""
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.compliance_keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def flag_risks(self, structured_data: Dict[str, Any], compliance_keywords: List[str]) -> List[PDFFlag]:
        """Flag potential risks based on extracted data"""
        flags = []
        
        # Check for high invoice amounts
        if 'total_amount' in structured_data:
            amount = structured_data['total_amount']
            if isinstance(amount, (int, float)) and amount > self.risk_thresholds['max_invoice_amount']:
                flags.append(PDFFlag(
                    flag_type=RiskFlag.HIGH_AMOUNT,
                    field='total_amount',
                    value=amount,
                    threshold=self.risk_thresholds['max_invoice_amount'],
                    severity='high',
                    description=f'Invoice amount ${amount:,.2f} exceeds threshold of ${self.risk_thresholds["max_invoice_amount"]:,.2f}'
                ))
        
        # Check for regulatory compliance mentions
        critical_compliance = ['gdpr', 'fda', 'hipaa', 'sox']
        for keyword in compliance_keywords:
            if keyword.lower() in critical_compliance:
                flags.append(PDFFlag(
                    flag_type=RiskFlag.REGULATORY_MENTION,
                    field='compliance_keywords',
                    value=keyword,
                    threshold='regulatory_keyword',
                    severity='medium',
                    description=f'Document mentions critical regulatory keyword: {keyword.upper()}'
                ))
        
        # Check for suspicious amounts
        for field_name, value in structured_data.items():
            if field_name.endswith('_amount') and isinstance(value, (int, float)):
                if value in self.risk_thresholds['suspicious_amounts']:
                    flags.append(PDFFlag(
                        flag_type=RiskFlag.SUSPICIOUS_CONTENT,
                        field=field_name,
                        value=value,
                        threshold='suspicious_pattern',
                        severity='medium',
                        description=f'Amount ${value} matches suspicious test pattern'
                    ))
        
        return flags
    
    def calculate_risk_score(self, flags: List[PDFFlag], document_type: DocumentType) -> float:
        """Calculate overall risk score"""
        if not flags:
            return 0.0
        
        severity_weights = {
            'low': 0.1,
            'medium': 0.3,
            'high': 0.6,
            'critical': 1.0
        }
        
        total_score = sum(severity_weights.get(flag.severity, 0.1) for flag in flags)
        
        # Document type modifiers
        type_multipliers = {
            DocumentType.INVOICE: 1.2,  # Financial docs are higher risk
            DocumentType.POLICY: 1.1,   # Compliance docs need attention
            DocumentType.CONTRACT: 1.1,
            DocumentType.REGULATION: 1.3,
            DocumentType.UNKNOWN: 0.8
        }
        
        multiplier = type_multipliers.get(document_type, 1.0)
        final_score = min(total_score * multiplier / len(flags), 1.0)
        
        return final_score
    
    def determine_action(self, risk_score: float, flags: List[PDFFlag]) -> str:
        """Determine suggested action based on analysis"""
        high_severity_count = sum(1 for flag in flags if flag.severity == 'high')
        
        if risk_score >= 0.8 or high_severity_count >= 2:
            return "escalate_compliance_review"
        elif risk_score >= 0.6 or high_severity_count >= 1:
            return "flag_for_manual_review"
        elif risk_score >= 0.3:
            return "log_for_audit"
        else:
            return "process_normally"
    
    def generate_metadata(self, text: str, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate metadata about the document"""
        lines = text.split('\n')
        words = text.split()
        
        return {
            'character_count': len(text),
            'word_count': len(words),
            'line_count': len(lines),
            'page_count_estimate': max(1, len(lines) // 50),  # Rough estimate
            'has_tables': bool(re.search(r'\|\s*\w+\s*\|', text)),
            'has_signatures': bool(re.search(r'signature|signed|_____', text.lower())),
            'contains_amounts': len([k for k in structured_data.keys() if 'amount' in k]),
            'contains_dates': len([k for k in structured_data.keys() if 'date' in k]),
            'processed_at': datetime.now().isoformat()
        }
    
    def process_pdf(self, pdf_input, input_type: str = "file") -> PDFAnalysis:
        """
        Main method to process a PDF document
        
        Args:
            pdf_input: Either file path (str) or PDF bytes
            input_type: "file" or "bytes"
        """
        try:
            # Extract text
            if input_type == "file":
                text = self.extract_text_from_file(pdf_input)
            else:  # bytes
                text = self.extract_text_from_pdf(pdf_input)
            
            # Detect document type
            document_type, type_confidence = self.detect_document_type(text)
            
            # Extract structured data
            structured_data = self.extract_structured_data(text, document_type)
            
            # Detect compliance issues
            compliance_keywords = self.detect_compliance_issues(text)
            
            # Flag risks
            flags = self.flag_risks(structured_data, compliance_keywords)
            
            # Calculate risk score
            risk_score = self.calculate_risk_score(flags, document_type)
            
            # Determine action
            suggested_action = self.determine_action(risk_score, flags)
            
            # Generate metadata
            metadata = self.generate_metadata(text, structured_data)
            metadata['document_type_confidence'] = type_confidence
            
            return PDFAnalysis(
                document_type=document_type,
                extracted_text=text[:1000] + "..." if len(text) > 1000 else text,  # Truncate for storage
                structured_data=structured_data,
                flags=flags,
                compliance_keywords=compliance_keywords,
                risk_score=risk_score,
                suggested_action=suggested_action,
                metadata=metadata
            )
            
        except Exception as e:
            # Return error analysis
            return PDFAnalysis(
                document_type=DocumentType.UNKNOWN,
                extracted_text="",
                structured_data={},
                flags=[PDFFlag(
                    flag_type=RiskFlag.SUSPICIOUS_CONTENT,
                    field="processing_error",
                    value=str(e),
                    threshold="no_errors",
                    severity="critical",
                    description=f"PDF processing failed: {str(e)}"
                )],
                compliance_keywords=[],
                risk_score=1.0,
                suggested_action="manual_review_required",
                metadata={"error": str(e), "processed_at": datetime.now().isoformat()}
            )
    
    def get_extracted_fields(self, analysis: PDFAnalysis) -> Dict[str, Any]:
        """Convert analysis to dictionary for storage"""
        return {
            "document_type": analysis.document_type.value,
            "text_length": len(analysis.extracted_text),
            "structured_fields_count": len(analysis.structured_data),
            "compliance_keywords_found": len(analysis.compliance_keywords),
            "compliance_keywords": ",".join(analysis.compliance_keywords),
            "flags_count": len(analysis.flags),
            "high_severity_flags": sum(1 for flag in analysis.flags if flag.severity == "high"),
            "risk_score": analysis.risk_score,
            "suggested_action": analysis.suggested_action,
            "word_count": analysis.metadata.get("word_count", 0),
            "contains_amounts": analysis.metadata.get("contains_amounts", 0),
            "contains_dates": analysis.metadata.get("contains_dates", 0),
            "processed_at": datetime.now().isoformat(),
            "structured_data": str(analysis.structured_data),
            "flag_details": str([{
                "type": flag.flag_type.value,
                "field": flag.field,
                "severity": flag.severity,
                "description": flag.description
            } for flag in analysis.flags])
        }

# Example usage and testing
if __name__ == "__main__":
    pdf_agent = PDFAgent()
    
    # Test with sample text (simulating PDF content)
    test_documents = [
        # Sample Invoice
        """
        INVOICE #INV-2024-001
        Date: January 15, 2024
        Due Date: February 15, 2024
        
        Bill To:
        ABC Company
        123 Main Street
        
        Description    Qty    Price    Total
        Product A      2      $5,000   $10,000
        Product B      1      $2,500   $2,500
        
        Subtotal: $12,500
        Tax: $1,000
        Total Amount: $13,500
        """,
        
        # Sample Policy with GDPR
        """
        PRIVACY POLICY DOCUMENT
        Effective Date: January 1, 2024
        
        1. Data Collection
        We collect personal data in accordance with GDPR regulations.
        
        2. Data Retention
        We retain personal data for 7 years as required by law.
        
        3. User Rights
        Users have the right to data portability under GDPR Article 20.
        """,
        
        # High-value invoice (should trigger flags)
        """
        INVOICE #INV-CRITICAL-999
        Date: May 30, 2024
        
        Emergency Equipment Purchase
        Total Amount: $25,000
        
        This invoice exceeds normal purchasing thresholds.
        """
    ]
    
    for i, doc_text in enumerate(test_documents):
        print(f"\n=== PDF Test Case {i+1} ===")
        print(f"Document Preview: {doc_text[:100]}...")
        
        # Simulate processing (normally would be actual PDF)
        # For testing, we'll directly analyze the text
        try:
            document_type, confidence = pdf_agent.detect_document_type(doc_text)
            structured_data = pdf_agent.extract_structured_data(doc_text, document_type)
            compliance_keywords = pdf_agent.detect_compliance_issues(doc_text)
            flags = pdf_agent.flag_risks(structured_data, compliance_keywords)
            risk_score = pdf_agent.calculate_risk_score(flags, document_type)
            
            print(f"Document Type: {document_type.value} (confidence: {confidence:.2f})")
            print(f"Structured Data: {structured_data}")
            print(f"Compliance Keywords: {compliance_keywords}")
            print(f"Risk Score: {risk_score:.2f}")
            print(f"Flags: {len(flags)} found")
            
            for flag in flags:
                print(f"  - {flag.severity.upper()}: {flag.description}")
                
        except Exception as e:
            print(f"Error processing document: {e}")