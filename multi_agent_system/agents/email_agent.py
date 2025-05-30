import re
import email
from email.parser import Parser
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class ToneType(Enum):
    POLITE = "polite"
    NEUTRAL = "neutral"
    URGENT = "urgent"
    ANGRY = "angry"
    THREATENING = "threatening"
    ESCALATION = "escalation"

class UrgencyLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class EmailAnalysis:
    sender: str
    recipient: str
    subject: str
    body: str
    tone: ToneType
    urgency: UrgencyLevel
    keywords: List[str]
    sentiment_score: float
    requires_escalation: bool
    suggested_action: str

class EmailAgent:
    """
    Email Agent that extracts structured fields from email content
    and determines appropriate actions based on tone and urgency
    """
    
    def __init__(self):
        self.name = "email_agent"
        self.tone_indicators = self._load_tone_indicators()
        self.urgency_indicators = self._load_urgency_indicators()
        
    def _load_tone_indicators(self) -> Dict[ToneType, List[str]]:
        """Load words/phrases that indicate different tones"""
        return {
            ToneType.POLITE: [
                'please', 'thank you', 'appreciate', 'kindly', 'grateful',
                'respectfully', 'sincerely', 'best regards', 'dear'
            ],
            ToneType.ANGRY: [
                'angry', 'furious', 'outraged', 'disgusted', 'appalled',
                'terrible', 'awful', 'horrible', 'worst', 'hate',
                'disgusting', 'unacceptable', 'ridiculous'
            ],
            ToneType.THREATENING: [
                'lawsuit', 'legal action', 'attorney', 'lawyer', 'sue',
                'court', 'bbb', 'better business bureau', 'media',
                'public', 'review', 'expose'
            ],
            ToneType.ESCALATION: [
                'manager', 'supervisor', 'escalate', 'higher up',
                'corporate', 'headquarters', 'ceo', 'president'
            ],
            ToneType.URGENT: [
                'urgent', 'asap', 'immediately', 'emergency', 'critical',
                'time sensitive', 'deadline', 'rush'
            ]
        }
    
    def _load_urgency_indicators(self) -> Dict[UrgencyLevel, List[str]]:
        """Load indicators for different urgency levels"""
        return {
            UrgencyLevel.CRITICAL: [
                'emergency', 'critical', 'urgent', 'asap', 'immediately',
                'deadline today', 'time sensitive', 'system down'
            ],
            UrgencyLevel.HIGH: [
                'important', 'priority', 'soon', 'quick', 'deadline',
                'time sensitive', 'please hurry'
            ],
            UrgencyLevel.MEDIUM: [
                'when possible', 'convenience', 'follow up', 'update'
            ],
            UrgencyLevel.LOW: [
                'whenever', 'no rush', 'when you can', 'at your convenience'
            ]
        }
    
    def parse_email_headers(self, email_content: str) -> Dict[str, str]:
        """Extract standard email headers"""
        headers = {}
        
        # Try to parse as actual email first
        try:
            if email_content.startswith('From:') or 'Message-ID:' in email_content:
                msg = Parser().parsestr(email_content)
                headers = {
                    'from': msg.get('From', ''),
                    'to': msg.get('To', ''),
                    'subject': msg.get('Subject', ''),
                    'date': msg.get('Date', ''),
                    'message_id': msg.get('Message-ID', '')
                }
            else:
                # Parse simple format
                lines = email_content.split('\n')
                for line in lines[:10]:  # Check first 10 lines for headers
                    if ':' in line:
                        key, value = line.split(':', 1)
                        headers[key.lower().strip()] = value.strip()
        except Exception as e:
            print(f"Error parsing email headers: {e}")
        
        return headers
    
    def extract_body(self, email_content: str) -> str:
        """Extract the main body content from email"""
        try:
            # If it's a proper email format
            if email_content.startswith('From:') or 'Message-ID:' in email_content:
                msg = Parser().parsestr(email_content)
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            return part.get_payload(decode=True).decode()
                else:
                    return msg.get_payload(decode=True).decode()
            else:
                # Simple format - assume everything after headers is body
                lines = email_content.split('\n')
                body_start = 0
                for i, line in enumerate(lines):
                    if line.strip() == '' and i > 0:  # Empty line after headers
                        body_start = i + 1
                        break
                    elif not ':' in line and i > 0:  # No more header-like lines
                        body_start = i
                        break
                
                return '\n'.join(lines[body_start:])
        except Exception as e:
            print(f"Error extracting email body: {e}")
            return email_content
    
    def analyze_tone(self, content: str) -> Tuple[ToneType, float]:
        """Analyze the tone of the email content"""
        content_lower = content.lower()
        tone_scores = {}
        
        for tone_type, indicators in self.tone_indicators.items():
            score = 0
            for indicator in indicators:
                if indicator in content_lower:
                    score += 1
            tone_scores[tone_type] = score
        
        # Additional analysis
        # Check for caps (indicates shouting/anger)
        caps_ratio = sum(1 for c in content if c.isupper()) / len(content) if content else 0
        if caps_ratio > 0.3:
            tone_scores[ToneType.ANGRY] += 2
        
        # Check for exclamation marks
        exclamation_count = content.count('!')
        if exclamation_count > 3:
            tone_scores[ToneType.ANGRY] += 1
        elif exclamation_count > 1:
            tone_scores[ToneType.URGENT] += 1
        
        # Find dominant tone
        if all(score == 0 for score in tone_scores.values()):
            return ToneType.NEUTRAL, 0.5
        
        best_tone = max(tone_scores.items(), key=lambda x: x[1])
        confidence = min(best_tone[1] / 3, 1.0)  # Normalize
        
        return best_tone[0], confidence
    
    def analyze_urgency(self, content: str, subject: str = "") -> Tuple[UrgencyLevel, float]:
        """Analyze the urgency level of the email"""
        full_content = (content + " " + subject).lower()
        urgency_scores = {}
        
        for urgency_level, indicators in self.urgency_indicators.items():
            score = 0
            for indicator in indicators:
                if indicator in full_content:
                    score += 1
            urgency_scores[urgency_level] = score
        
        # Additional urgency indicators
        if any(word in full_content for word in ['deadline', 'due date', 'expires']):
            urgency_scores[UrgencyLevel.HIGH] += 1
        
        if '!!!' in content or 'URGENT' in content:
            urgency_scores[UrgencyLevel.CRITICAL] += 2
        
        # Find highest urgency
        if all(score == 0 for score in urgency_scores.values()):
            return UrgencyLevel.MEDIUM, 0.5  # Default to medium
        
        best_urgency = max(urgency_scores.items(), key=lambda x: x[1])
        confidence = min(best_urgency[1] / 2, 1.0)
        
        return best_urgency[0], confidence
    
    def calculate_sentiment_score(self, content: str) -> float:
        """Calculate a simple sentiment score (-1 to 1)"""
        positive_words = [
            'good', 'great', 'excellent', 'amazing', 'wonderful',
            'fantastic', 'pleased', 'satisfied', 'happy', 'love'
        ]
        negative_words = [
            'bad', 'terrible', 'awful', 'horrible', 'disgusting',
            'hate', 'angry', 'disappointed', 'frustrated', 'upset'
        ]
        
        content_lower = content.lower()
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        total_words = len(content.split())
        if total_words == 0:
            return 0.0
        
        # Calculate sentiment score
        sentiment = (positive_count - negative_count) / max(total_words / 10, 1)
        return max(-1.0, min(1.0, sentiment))  # Clamp between -1 and 1
    
    def determine_action(self, tone: ToneType, urgency: UrgencyLevel, 
                        sentiment: float) -> Tuple[str, bool]:
        """Determine the suggested action based on analysis"""
        requires_escalation = False
        
        # Escalation logic
        if tone in [ToneType.THREATENING, ToneType.ESCALATION]:
            requires_escalation = True
            action = "escalate_to_manager"
        elif tone == ToneType.ANGRY and urgency in [UrgencyLevel.HIGH, UrgencyLevel.CRITICAL]:
            requires_escalation = True
            action = "escalate_to_crm"
        elif urgency == UrgencyLevel.CRITICAL:
            requires_escalation = True
            action = "emergency_response"
        elif sentiment < -0.5 and urgency == UrgencyLevel.HIGH:
            requires_escalation = True
            action = "priority_response"
        elif tone == ToneType.POLITE and urgency == UrgencyLevel.LOW:
            action = "log_and_acknowledge"
        else:
            action = "standard_response"
        
        return action, requires_escalation
    
    def extract_keywords(self, content: str) -> List[str]:
        """Extract important keywords from the email content"""
        # Remove common words
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
            'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        keywords = [word for word in words if word not in common_words]
        
        # Count frequency
        word_count = {}
        for word in keywords:
            word_count[word] = word_count.get(word, 0) + 1
        
        # Return top keywords
        sorted_keywords = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_keywords[:10]]
    
    def process_email(self, email_content: str) -> EmailAnalysis:
        """
        Main method to process an email and extract all relevant information
        """
        # Parse headers
        headers = self.parse_email_headers(email_content)
        
        # Extract body
        body = self.extract_body(email_content)
        
        # Get basic fields
        sender = headers.get('from', 'unknown@example.com')
        recipient = headers.get('to', 'support@company.com')
        subject = headers.get('subject', 'No Subject')
        
        # Analyze tone and urgency
        tone, tone_confidence = self.analyze_tone(body)
        urgency, urgency_confidence = self.analyze_urgency(body, subject)
        
        # Calculate sentiment
        sentiment_score = self.calculate_sentiment_score(body)
        
        # Determine action
        suggested_action, requires_escalation = self.determine_action(tone, urgency, sentiment_score)
        
        # Extract keywords
        keywords = self.extract_keywords(body)
        
        return EmailAnalysis(
            sender=sender,
            recipient=recipient,
            subject=subject,
            body=body,
            tone=tone,
            urgency=urgency,
            keywords=keywords,
            sentiment_score=sentiment_score,
            requires_escalation=requires_escalation,
            suggested_action=suggested_action
        )
    
    def get_extracted_fields(self, analysis: EmailAnalysis) -> Dict[str, Any]:
        """Convert analysis to dictionary for storage"""
        return {
            "sender": analysis.sender,
            "recipient": analysis.recipient,
            "subject": analysis.subject,
            "tone": analysis.tone.value,
            "urgency": analysis.urgency.value,
            "sentiment_score": analysis.sentiment_score,
            "keywords": ",".join(analysis.keywords),
            "requires_escalation": analysis.requires_escalation,
            "suggested_action": analysis.suggested_action,
            "body_length": len(analysis.body),
            "processed_at": datetime.now().isoformat()
        }

# Example usage and testing
if __name__ == "__main__":
    email_agent = EmailAgent()
    
    # Test with different email examples
    test_emails = [
        # Angry complaint email
        """From: angry.customer@example.com
To: support@company.com
Subject: TERRIBLE SERVICE - DEMAND REFUND NOW!!!

I am absolutely FURIOUS with your company! The product I received is completely broken and your customer service is AWFUL. I have been waiting 2 weeks for a response and this is UNACCEPTABLE!

I want to speak to your manager immediately and if this isn't resolved today, I will be contacting my lawyer and posting negative reviews everywhere!

This is the WORST experience I've ever had!""",
        
        # Polite inquiry
        """From: polite.customer@example.com
To: support@company.com
Subject: Question about my recent order

Dear Support Team,

I hope this email finds you well. I recently placed an order (#12345) and wanted to kindly inquire about the expected delivery date.

I appreciate your time and look forward to your response at your convenience.

Best regards,
Jane Smith""",
        
        # Urgent technical issue
        """From: tech.user@example.com
To: support@company.com
Subject: URGENT: System Down - Critical Issue

Our production system is currently down and we need immediate assistance. This is affecting our ability to serve customers and is costing us money every minute.

Please prioritize this request as it's an emergency situation.

Thank you for your quick response."""
    ]
    
    for i, email_content in enumerate(test_emails):
        print(f"\n=== Email Test Case {i+1} ===")
        analysis = email_agent.process_email(email_content)
        
        print(f"Sender: {analysis.sender}")
        print(f"Subject: {analysis.subject}")
        print(f"Tone: {analysis.tone.value}")
        print(f"Urgency: {analysis.urgency.value}")
        print(f"Sentiment Score: {analysis.sentiment_score:.2f}")
        print(f"Requires Escalation: {analysis.requires_escalation}")
        print(f"Suggested Action: {analysis.suggested_action}")
        print(f"Keywords: {', '.join(analysis.keywords[:5])}")
        
        # Show extracted fields format
        fields = email_agent.get_extracted_fields(analysis)
        print(f"Extracted Fields: {len(fields)} fields captured")