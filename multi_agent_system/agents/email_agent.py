import re
from enum import Enum
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, asdict

class ToneType(Enum):
    NEUTRAL = "neutral"
    POLITE = "polite"
    ANGRY = "angry"
    THREATENING = "threatening"
    URGENT_POSITIVE = "urgent_positive" # e.g. urgent opportunity
    URGENT_NEGATIVE = "urgent_negative" # e.g. urgent problem

class EmailActionType(Enum):
    STANDARD_RESPONSE = "standard_response"
    ESCALATE_TO_MANAGER = "escalate_to_manager"
    ESCALATE_TO_CRM = "escalate_to_crm"
    LOG_AND_ACKNOWLEDGE = "log_and_acknowledge"
    FLAG_FOR_REVIEW = "flag_for_review"

@dataclass
class EmailAnalysis:
    sender: str
    recipient: str # Assuming a single primary recipient for simplicity
    subject: str
    body_preview: str # First N characters
    keywords: List[str]
    tone: ToneType
    urgency_score: float # 0.0 (low) to 1.0 (high)
    sentiment_score: float # -1.0 (negative) to 1.0 (positive)
    requires_escalation: bool
    suggested_action: EmailActionType

class EmailAgent:
    def __init__(self):
        self.name = "email_agent"
        # More sophisticated keyword sets can be loaded from a config file
        self.TONE_KEYWORDS = {
            ToneType.ANGRY: [r'\b(furious|angry|terrible|awful|unacceptable|outrageous|worst)\b'],
            ToneType.THREATENING: [r'\b(legal|lawyer|sue|court|action\s+will\s+be\s+taken)\b'],
            ToneType.POLITE: [r'\b(please|thank\s+you|kindly|appreciate|grateful)\b'],
            ToneType.URGENT_POSITIVE: [r'\b(urgent\s+opportunity|immediate\s+action\s+required\s+for\s+benefit)\b'],
            ToneType.URGENT_NEGATIVE: [r'\b(urgent\s+problem|critical\s+issue|immediate\s+attention|asap|now)\b']
        }
        self.URGENCY_KEYWORDS = {
            0.9: [r'\b(urgent|immediately|asap|now|critical|deadline)\b'],
            0.6: [r'\b(important|promptly|soon|needs\s+attention)\b'],
            0.3: [r'\b(reminder|follow-up|update)\b']
        }
        self.SENTIMENT_KEYWORDS = {
            "positive": [r'\b(good|great|excellent|happy|satisfied|pleased|wonderful|thanks|appreciate)\b'],
            "negative": [r'\b(bad|poor|terrible|awful|sad|angry|unhappy|issue|problem|complaint|concern|error)\b']
        }

    def _parse_email_headers(self, email_content: str) -> Dict[str, str]:
        headers = {}
        # Simple regex for common headers, assumes headers are at the beginning
        if match := re.search(r"^From:\s*(.+)", email_content, re.IGNORECASE | re.MULTILINE):
            headers["sender"] = match.group(1).strip()
        if match := re.search(r"^To:\s*(.+)", email_content, re.IGNORECASE | re.MULTILINE):
            headers["recipient"] = match.group(1).strip()
        if match := re.search(r"^Subject:\s*(.+)", email_content, re.IGNORECASE | re.MULTILINE):
            headers["subject"] = match.group(1).strip()
        return headers

    def _extract_body(self, email_content: str) -> str:
        # Simple body extraction: assumes body starts after the first double newline
        # or after all known headers. This is a simplification.
        match = re.search(r"\n\n(.*)", email_content, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Fallback: try to remove common headers
        body_candidate = email_content
        for header_pattern in [r"^From:.*\n?", r"^To:.*\n?", r"^Subject:.*\n?", r"^Date:.*\n?"]:
            body_candidate = re.sub(header_pattern, "", body_candidate, flags=re.IGNORECASE | re.MULTILINE)
        return body_candidate.strip()

    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        text_lower = text.lower()
        # Simple keyword extraction: split by non-alphanumeric, filter common words
        words = re.findall(r'\b[a-z]{3,15}\b', text_lower) # Words 3-15 chars long
        stopwords = set(["the", "a", "is", "to", "of", "and", "in", "it", "you", "for", "on", "with", "this", "that", "i", "me", "my", "we", "our", "not", "be", "at", "or", "as", "do", "if", "so", "me", "am"])
        
        # A more advanced approach would use TF-IDF or other NLP techniques
        # For now, simple frequency count after stopword removal
        from collections import Counter
        filtered_words = [word for word in words if word not in stopwords]
        if not filtered_words:
            return []
        
        most_common = [word for word, count in Counter(filtered_words).most_common(max_keywords)]
        return most_common

    def _analyze_tone(self, text: str) -> ToneType:
        text_lower = text.lower()
        scores = {tone: 0 for tone in ToneType}

        for tone, patterns in self.TONE_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    scores[tone] += 1
        
        # Prioritize more severe tones
        if scores[ToneType.THREATENING] > 0: return ToneType.THREATENING
        if scores[ToneType.ANGRY] > 0: return ToneType.ANGRY
        if scores[ToneType.URGENT_NEGATIVE] > 0: return ToneType.URGENT_NEGATIVE
        if scores[ToneType.URGENT_POSITIVE] > 0: return ToneType.URGENT_POSITIVE
        if scores[ToneType.POLITE] > 0: return ToneType.POLITE
        return ToneType.NEUTRAL

    def _analyze_urgency(self, text: str) -> float:
        text_lower = text.lower()
        max_urgency = 0.1 # Default low urgency

        for score_val, patterns in self.URGENCY_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    max_urgency = max(max_urgency, score_val)
        return max_urgency

    def _analyze_sentiment(self, text: str) -> float:
        text_lower = text.lower()
        positive_score = 0
        negative_score = 0

        for pattern in self.SENTIMENT_KEYWORDS["positive"]:
            positive_score += len(re.findall(pattern, text_lower))
        for pattern in self.SENTIMENT_KEYWORDS["negative"]:
            negative_score += len(re.findall(pattern, text_lower))
        
        if positive_score == 0 and negative_score == 0:
            return 0.0 # Neutral
        
        # Normalize: (P - N) / (P + N) - simple approach
        # More sophisticated sentiment analysis would use libraries like VADER or TextBlob
        return (positive_score - negative_score) / (positive_score + negative_score)


    def _determine_action(self, tone: ToneType, urgency: float, sentiment: float) -> Tuple[EmailActionType, bool]:
        requires_escalation = False
        action = EmailActionType.STANDARD_RESPONSE

        if tone == ToneType.THREATENING:
            action = EmailActionType.ESCALATE_TO_MANAGER
            requires_escalation = True
        elif tone == ToneType.ANGRY and urgency > 0.7:
            action = EmailActionType.ESCALATE_TO_CRM # Or manager depending on severity
            requires_escalation = True
        elif tone == ToneType.ANGRY:
            action = EmailActionType.FLAG_FOR_REVIEW
            requires_escalation = True # Still needs review
        elif tone == ToneType.URGENT_NEGATIVE and urgency > 0.5:
            action = EmailActionType.ESCALATE_TO_CRM
            requires_escalation = True
        elif urgency > 0.8: # General high urgency
            action = EmailActionType.FLAG_FOR_REVIEW
            requires_escalation = True
        elif sentiment < -0.5 and urgency > 0.5: # Very negative and somewhat urgent
            action = EmailActionType.ESCALATE_TO_CRM
            requires_escalation = True
        elif sentiment < -0.3: # Moderately negative
            action = EmailActionType.LOG_AND_ACKNOWLEDGE
        elif tone == ToneType.POLITE and urgency < 0.4:
            action = EmailActionType.STANDARD_RESPONSE
        
        return action, requires_escalation

    def process_email(self, email_content: str) -> EmailAnalysis:
        headers = self._parse_email_headers(email_content)
        body = self._extract_body(email_content)
        
        sender = headers.get("sender", "unknown@example.com")
        recipient = headers.get("recipient", "support@company.com") # Default or parse more robustly
        subject = headers.get("subject", "No Subject")

        # Use body for primary analysis, but subject can contribute
        analysis_text = subject + " " + body
        
        keywords = self._extract_keywords(analysis_text)
        tone = self._analyze_tone(analysis_text)
        urgency = self._analyze_urgency(analysis_text)
        sentiment = self._analyze_sentiment(analysis_text)
        
        action, escalation_needed = self._determine_action(tone, urgency, sentiment)

        return EmailAnalysis(
            sender=sender,
            recipient=recipient,
            subject=subject,
            body_preview=body[:200] + "...", # Preview of the extracted body
            keywords=keywords,
            tone=tone,
            urgency_score=urgency,
            sentiment_score=sentiment,
            requires_escalation=escalation_needed,
            suggested_action=action
        )

    def get_extracted_fields(self, analysis_result: EmailAnalysis) -> Dict[str, Any]:
        """Converts EmailAnalysis to a dictionary for storage/response."""
        result_dict = asdict(analysis_result)
        # Convert enums to their string values for JSON serialization
        result_dict["tone"] = analysis_result.tone.value
        result_dict["suggested_action"] = analysis_result.suggested_action.value
        return result_dict