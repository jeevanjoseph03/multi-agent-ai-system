import re
from PyPDF2 import PdfReader
from io import BytesIO
from typing import Dict, Any, List, Tuple, Union
from enum import Enum
from dataclasses import dataclass, asdict

class PDFDocumentType(Enum):
    INVOICE = "invoice"
    POLICY = "policy_document"
    REPORT = "report"
    UNKNOWN = "unknown"

class PDFFlagType(Enum):
    HIGH_INVOICE_AMOUNT = "high_invoice_amount"
    COMPLIANCE_KEYWORD_GDPR = "compliance_keyword_gdpr"
    COMPLIANCE_KEYWORD_FDA = "compliance_keyword_fda"
    COMPLIANCE_KEYWORD_OTHER = "compliance_keyword_other"
    MISSING_REQUIRED_FIELDS = "missing_required_fields_invoice" # Example
    NONE = "none"

class PDFActionType(Enum):
    REVIEW_INVOICE = "review_invoice"
    COMPLIANCE_ALERT = "compliance_alert"
    ARCHIVE_DOCUMENT = "archive_document"
    FLAG_FOR_LEGAL = "flag_for_legal_review"
    NO_ACTION = "no_action"

@dataclass
class PDFAnalysis:
    document_type: PDFDocumentType
    confidence: float
    extracted_fields: Dict[str, Any]
    compliance_keywords_found: List[str]
    flags: List[PDFFlagType]
    risk_score: float # 0.0 to 1.0
    suggested_action: PDFActionType
    raw_text_preview: str # For brevity in logs

class PDFAgent:
    def __init__(self):
        self.name = "pdf_agent"
        self.MAX_INVOICE_AMOUNT = 10000.0
        self.COMPLIANCE_KEYWORDS = {
            "GDPR": [r'\b(gdpr|general\s+data\s+protection\s+regulation)\b'],
            "FDA": [r'\b(fda|food\s+and\s+drug\s+administration)\b'],
            "OTHER": [r'\b(hipaa|ccpa|sox|pipeda|compliance|regulation|policy|terms\s+of\s+service)\b']
        }
        self.INVOICE_PATTERNS = {
            "invoice_number": [r'invoice\s*(?:number|no\.?|#)\s*[:\s]*([A-Z0-9\-]+)', r'inv\s*-\s*([A-Z0-9\-]+)'],
            "invoice_date": [r'(?:invoice\s+)?date\s*[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\w+\s+\d{1,2},\s+\d{4})'],
            "due_date": [r'due\s+date\s*[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\w+\s+\d{1,2},\s+\d{4})'],
            "total_amount": [r'(?:total\s+amount|grand\s+total|total\s+due|amount\s+due)\s*[:\s]*\$?\s*([\d,]+\.\d{2})'],
            "subtotal": [r'subtotal\s*[:\s]*\$?\s*([\d,]+\.\d{2})'],
            "tax_amount": [r'tax(?:\s+\([\d\.]+%?\))?\s*[:\s]*\$?\s*([\d,]+\.\d{2})'],
            "bill_to": [r'bill\s+to\s*[:\s]*\n?([\s\S]*?)(?=\n\n|\nship\s+to|\nitem|\ndescription|payment\s+terms|notes|thank\s+you|subtotal)', r'customer\s*[:\s]*\n?([\s\S]*?)(?=\n\n|\nitem)'],
            # Basic line item capture (can be complex)
            "line_items_header": [r'(description|item)\s+(quantity|qty)\s+(unit\s+price|price)\s+(amount|total)'],
        }

    def _extract_text_from_bytes(self, pdf_bytes: bytes) -> str:
        text = ""
        try:
            reader = PdfReader(BytesIO(pdf_bytes))
            for page in reader.pages:
                text += page.extract_text() or ""
        except Exception as e:
            print(f"Error extracting text from PDF bytes: {e}")
        return text

    def _extract_text_from_file(self, file_path: str) -> str:
        text = ""
        try:
            with open(file_path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
        except Exception as e:
            print(f"Error extracting text from PDF file {file_path}: {e}")
        return text

    def _detect_document_type(self, text: str) -> Tuple[PDFDocumentType, float]:
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in ["invoice", "bill to", "total due", "statement of account"]):
            if any(keyword in text_lower for keyword in ["line item", "description", "qty", "unit price"]):
                return PDFDocumentType.INVOICE, 0.9
            return PDFDocumentType.INVOICE, 0.7
        if any(keyword in text_lower for keyword in ["policy", "terms and conditions", "privacy statement", "regulation", "gdpr", "fda"]):
            return PDFDocumentType.POLICY, 0.8
        if any(keyword in text_lower for keyword in ["report", "summary", "analysis", "findings"]):
            return PDFDocumentType.REPORT, 0.6
        return PDFDocumentType.UNKNOWN, 0.3

    def _extract_structured_data(self, text: str, doc_type: PDFDocumentType) -> Dict[str, Any]:
        data: Dict[str, Any] = {"raw_text_preview": text[:500] + "..."} # Store a preview
        text_lower_for_search = text # Keep original case for some captures if needed, but search lower
        
        if doc_type == PDFDocumentType.INVOICE:
            for field, patterns in self.INVOICE_PATTERNS.items():
                if field == "line_items_header": # Skip direct extraction of header
                    continue
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                    if match:
                        value = match.group(1).strip() if len(match.groups()) > 0 else match.group(0).strip()
                        if field in ["total_amount", "subtotal", "tax_amount"]:
                            try:
                                data[field] = float(value.replace(',', ''))
                            except ValueError:
                                data[field] = value # Store as string if conversion fails
                        else:
                            data[field] = value
                        break # Found pattern for this field
            # Basic line item extraction (example, very simplified)
            # A more robust solution would parse tables or use more advanced regex
            line_items = []
            # This is a placeholder for more complex line item logic
            # For simplicity, we'll just look for a few keywords if a header was found
            if re.search(self.INVOICE_PATTERNS["line_items_header"][0], text, re.IGNORECASE):
                # Example: find lines that look like "item description qty price total"
                # This is highly dependent on PDF structure and often requires OCR or table parsing tools for reliability
                # For now, we'll just indicate that line items might be present
                data["line_items_detected"] = True
                # A real implementation would iterate through lines after the header
                # and try to parse each column.
                # Example:
                # item_matches = re.findall(r"^(.*?)\s+(\d+)\s+\$?([\d\.,]+)\s+\$?([\d\.,]+)$", text, re.MULTILINE | re.IGNORECASE)
                # for item_match in item_matches:
                # line_items.append({"description": item_match[0].strip(), "quantity": int(item_match[1]), ...})
            data["line_items"] = line_items if line_items else "Line item extraction not fully implemented for this text structure."


        elif doc_type == PDFDocumentType.POLICY:
            data["title"] = "Policy Document" # Placeholder
            if match := re.search(r'effective\s+date\s*[:\s]*(.*)', text, re.IGNORECASE):
                data["effective_date"] = match.group(1).strip()
            # Could extract sections, etc.
        
        return data

    def _detect_compliance_issues(self, text: str) -> List[str]:
        found_keywords = []
        text_lower = text.lower()
        for category, patterns in self.COMPLIANCE_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    found_keywords.append(f"{category}_keyword_found") # More generic
                    # Or be specific:
                    # if category == "GDPR": found_keywords.append("GDPR")
                    # elif category == "FDA": found_keywords.append("FDA")
                    # else: found_keywords.append(pattern) # or a generic "OTHER_COMPLIANCE"
        return list(set(found_keywords)) # Unique keywords

    def _flag_risks(self, extracted_data: Dict[str, Any], compliance_keywords: List[str], doc_type: PDFDocumentType) -> List[PDFFlagType]:
        flags = []
        if doc_type == PDFDocumentType.INVOICE:
            total_amount = extracted_data.get("total_amount")
            if isinstance(total_amount, (float, int)) and total_amount > self.MAX_INVOICE_AMOUNT:
                flags.append(PDFFlagType.HIGH_INVOICE_AMOUNT)
            # Example: Check for missing essential invoice fields
            required_invoice_fields = ["invoice_number", "invoice_date", "total_amount", "bill_to"]
            if not all(field in extracted_data and extracted_data[field] for field in required_invoice_fields):
                flags.append(PDFFlagType.MISSING_REQUIRED_FIELDS)


        if any("GDPR_keyword_found" in kw for kw in compliance_keywords):
            flags.append(PDFFlagType.COMPLIANCE_KEYWORD_GDPR)
        if any("FDA_keyword_found" in kw for kw in compliance_keywords):
            flags.append(PDFFlagType.COMPLIANCE_KEYWORD_FDA)
        if any("OTHER_keyword_found" in kw for kw in compliance_keywords):
            flags.append(PDFFlagType.COMPLIANCE_KEYWORD_OTHER)
        
        if not flags:
            flags.append(PDFFlagType.NONE)
        return list(set(flags))

    def _calculate_risk_score(self, flags: List[PDFFlagType], doc_type: PDFDocumentType) -> float:
        score = 0.0
        if PDFFlagType.HIGH_INVOICE_AMOUNT in flags: score += 0.5
        if PDFFlagType.COMPLIANCE_KEYWORD_GDPR in flags: score += 0.3
        if PDFFlagType.COMPLIANCE_KEYWORD_FDA in flags: score += 0.4
        if PDFFlagType.COMPLIANCE_KEYWORD_OTHER in flags: score += 0.2
        if PDFFlagType.MISSING_REQUIRED_FIELDS in flags and doc_type == PDFDocumentType.INVOICE: score += 0.3
        return min(score, 1.0)

    def _determine_action(self, flags: List[PDFFlagType], risk_score: float, doc_type: PDFDocumentType) -> PDFActionType:
        if PDFFlagType.HIGH_INVOICE_AMOUNT in flags:
            return PDFActionType.REVIEW_INVOICE
        if PDFFlagType.COMPLIANCE_KEYWORD_GDPR in flags or PDFFlagType.COMPLIANCE_KEYWORD_FDA in flags:
            return PDFActionType.FLAG_FOR_LEGAL
        if PDFFlagType.COMPLIANCE_KEYWORD_OTHER in flags and doc_type == PDFDocumentType.POLICY:
            return PDFActionType.COMPLIANCE_ALERT
        if risk_score > 0.5:
            return PDFActionType.REVIEW_INVOICE # Generic review for high risk
        if doc_type != PDFDocumentType.UNKNOWN:
            return PDFActionType.ARCHIVE_DOCUMENT
        return PDFActionType.NO_ACTION

    def process_pdf(self, pdf_input: Union[str, bytes], input_type: str = "file") -> PDFAnalysis:
        """
        Main method to process a PDF document or PDF-like text.
        Args:
            pdf_input: File path (str), PDF bytes, or raw text content (str).
            input_type: "file", "bytes", or "text_content".
        """
        text = ""
        if input_type == "file":
            text = self._extract_text_from_file(str(pdf_input))
        elif input_type == "bytes":
            text = self._extract_text_from_bytes(bytes(pdf_input))
        elif input_type == "text_content":
            text = str(pdf_input)
        else:
            raise ValueError(f"Unsupported input_type for PDFAgent: {input_type}")

        if not text:
            return PDFAnalysis(
                document_type=PDFDocumentType.UNKNOWN,
                confidence=0.1,
                extracted_fields={"error": "Failed to extract text or empty content"},
                compliance_keywords_found=[],
                flags=[PDFFlagType.NONE],
                risk_score=0.0,
                suggested_action=PDFActionType.NO_ACTION,
                raw_text_preview="N/A"
            )

        doc_type, confidence = self._detect_document_type(text)
        extracted_data = self._extract_structured_data(text, doc_type)
        compliance_keywords = self._detect_compliance_issues(text)
        flags = self._flag_risks(extracted_data, compliance_keywords, doc_type)
        risk_score = self._calculate_risk_score(flags, doc_type)
        action = self._determine_action(flags, risk_score, doc_type)

        return PDFAnalysis(
            document_type=doc_type,
            confidence=confidence,
            extracted_fields=extracted_data,
            compliance_keywords_found=compliance_keywords,
            flags=flags,
            risk_score=risk_score,
            suggested_action=action,
            raw_text_preview=text[:200] + "..."
        )

    def get_extracted_fields(self, analysis_result: PDFAnalysis) -> Dict[str, Any]:
        """Converts PDFAnalysis to a dictionary for storage/response."""
        # Convert enums to their string values for JSON serialization
        result_dict = asdict(analysis_result)
        result_dict["document_type"] = analysis_result.document_type.value
        result_dict["flags"] = [flag.value for flag in analysis_result.flags]
        result_dict["suggested_action"] = analysis_result.suggested_action.value
        return result_dict

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