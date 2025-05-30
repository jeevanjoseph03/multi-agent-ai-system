# Multi-Agent AI System

## What This Project Does

This is an AI system I built that can automatically process different types of files and decide what to do with them. It can handle:
- **Emails** (like customer complaints)
- **JSON data** (like transaction records) 
- **PDF documents** (like invoices)

The system reads the content, figures out what it is, and then takes actions like creating support tickets or flagging suspicious activity.

## Why I Built This

I wanted to learn how to create AI agents that can work together. Instead of having one big program that does everything, I made separate "agents" that each have their own job:

1. **Classifier Agent** - Figures out what type of file it is
2. **Email Agent** - Reads emails and detects if customers are angry
3. **JSON Agent** - Checks transaction data for fraud
4. **PDF Agent** - Extracts information from documents
5. **Action Router** - Decides what to do based on what the agents found

## How It Works
Input File → Classifier → Specific Agent → Database → Actions


For example:
- Angry email comes in → Email agent detects anger → System creates support ticket
- Suspicious transaction → JSON agent flags it → System blocks the transaction

## What I Learned

- How to build AI agents in Python
- Working with different file formats (email, JSON, PDF)
- Using FastAPI to create web APIs
- Storing data in SQLite databases
- Making agents communicate with each other

## How to Run It

### Prerequisites
You need Python 3.8 or newer installed.

### Setup
```bash
# Download the project
git clone https://github.com/jeevanjoseph03/multi-agent-ai-system.git
cd multi-agent-ai-system

# Install required packages
pip install fastapi uvicorn PyPDF2 pydantic python-multipart requests jsonschema

# Start the system
python start_system.py

#Test It
Open your browser and go to: http://localhost:8000

You can also test it with the sample files I included in the samples/ folder.

## Project Structure
multi_agent_system/
├── agents/           # The AI agents
├── memory/          # Database stuff
├── routers/         # Action handling
├── main.py          # Main web server
samples/             # Test files
├── emails/          # Sample emails
├── jsons/           # Sample JSON data
└── pdfs/            # Sample documents (as text files)

## Sample Results
{
    "session_id": "abc123",
    "classification": {
        "format": "email",
        "intent": "complaint"
    },
    "agent_results": {
        "email_agent": {
            "tone": "angry",
            "urgency": "high",
            "suggested_action": "escalate_to_crm"
        }
    },
    "actions_taken": [
        {
            "action_type": "escalate_to_crm",
            "priority": "high"
        }
    ]
}

##Challenges I Faced
-Making agents talk to each other - Had to design a shared memory system
-Handling different file types - Each format needs different processing
-Deciding what actions to take - Created rules based on what agents find
-Testing everything - Made sample files to test different scenarios

##What's Cool About It
-Automatic email triage - Angry customers get escalated immediately
-Fraud detection - Suspicious transactions are blocked automatically
-Compliance monitoring - Documents with GDPR keywords get flagged
-Complete audit trail - Everything is logged in the database

##Future Improvements
If I had more time, I would add:

-Machine learning models instead of rule-based detection
-Integration with real CRM systems
-Better PDF processing with actual PDF files
-Email notifications when actions are taken
-A web dashboard to see all the activity

##Technologies Used
-Python - Main programming language
-FastAPI - Web framework for the API
-SQLite - Database for storing everything
-PyPDF2 - For PDF text extraction (though I used text files for demo)
-Pydantic - Data validation

##Demo
You can see it working by:

-Starting the system: python start_system.py
-Going to: http://localhost:8000/docs
-Trying the /process/text endpoint with the sample data

##About Me
I'm learning AI and Python development. This project helped me understand:

-How to structure larger Python projects
-Working with APIs and databases
-Building systems where different parts work together
-Processing different types of data.

**Note on PDF Files
I used text files instead of actual PDFs to keep things simple and focus on the AI logic rather than file parsing complexity. In a real system, you'd use proper PDF processing libraries.

Built by: Jeevan Joseph (jeevanjoseph03)
Created: May 2025
Purpose: Learning project for AI agent development
