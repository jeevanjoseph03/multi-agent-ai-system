# Multi-Format AI System

## What This Project Does

This AI system automatically handles different types of information like emails, JSON data (like from webhooks), and text from PDF documents. It figures out what the information is about and then decides what to do next, like flagging a risky transaction or escalating an angry customer email.

## Why I Built This

I built this to create a smart system where different AI "agents" work together. Each agent has a special job:
*   **Classifier Agent:** Identifies the type of input (email, JSON, PDF-text) and its main purpose (e.g., complaint, invoice).
*   **Email Agent:** Reads emails, checks for angry customers.
*   **JSON Agent:** Looks at data for anything suspicious (like fraud).
*   **PDF Agent:** Pulls out important info from documents.
*   **Action Router:** Decides the next step based on what the agents find.

## How It Works (Simplified)

1.  **Input:** The system gets some text or a file.
2.  **Classify:** The `ClassifierAgent` figures out what it is (e.g., "Email" + "Complaint").
3.  **Process:** The right specialized agent (e.g., `EmailAgent`) analyzes it.
4.  **Act:** The `ActionRouter` decides on a follow-up (e.g., "Escalate to CRM").
5.  **Log:** Everything is saved in a database (`memory_store.db`) so we can see what happened.

## How to Run It

### Prerequisites
*   Python 3.8+

### Setup & Run
1.  **Download:**
    ```bash
    git clone https://github.com/jeevanjoseph03/multi-agent-ai-system.git
    cd multi-agent-ai-system
    ```
2.  **Install (using a virtual environment is recommended):**
    ```bash
    # python -m venv venv
    # source venv/bin/activate  (or venv\Scripts\activate on Windows)
    pip install -r requirements.txt
    ```
    (The `start_system.py` script also tries to install key packages if you miss this.)
3.  **Start the System:**
    ```bash
    python start_system.py
    ```
    This usually starts the server at `http://localhost:8000`.

### Testing
*   **API Docs:** Go to `http://localhost:8000/docs` in your browser to try the API.
*   **Sample Tests:** Run `python test_samples.py` (after starting the server) to test with files in the `samples/` folder.

## Key Technologies
*   **Python**
*   **FastAPI** (for the web API)
*   **SQLite** (for the database)
*   **PyPDF2** (for reading text from actual PDF files when uploaded)

## Note on PDF Files
*   The system can read text directly from `.pdf` files you upload.
*   It can also process plain text that looks like it came from a PDF (like the `.txt` files in the `samples/pdfs/` folder).

---
Built by: Jeevan Joseph (jeevanjoseph03)
Purpose: Learning project for AI agent development
```// filepath: README.md
# Multi-Format AI System

## What This Project Does

This AI system automatically handles different types of information like emails, JSON data (like from webhooks), and text from PDF documents. It figures out what the information is about and then decides what to do next, like flagging a risky transaction or escalating an angry customer email.

## Why I Built This

I built this to create a smart system where different AI "agents" work together. Each agent has a special job:
*   **Classifier Agent:** Identifies the type of input (email, JSON, PDF-text) and its main purpose (e.g., complaint, invoice).
*   **Email Agent:** Reads emails, checks for angry customers.
*   **JSON Agent:** Looks at data for anything suspicious (like fraud).
*   **PDF Agent:** Pulls out important info from documents.
*   **Action Router:** Decides the next step based on what the agents find.

## How It Works (Simplified)

1.  **Input:** The system gets some text or a file.
2.  **Classify:** The `ClassifierAgent` figures out what it is (e.g., "Email" + "Complaint").
3.  **Process:** The right specialized agent (e.g., `EmailAgent`) analyzes it.
4.  **Act:** The `ActionRouter` decides on a follow-up (e.g., "Escalate to CRM").
5.  **Log:** Everything is saved in a database (`memory_store.db`) so we can see what happened.

## How to Run It

### Prerequisites
*   Python 3.8+

### Setup & Run
1.  **Download:**
    ```bash
    git clone https://github.com/jeevanjoseph03/multi-agent-ai-system.git
    cd multi-agent-ai-system
    ```
2.  **Install (using a virtual environment is recommended):**
    ```bash
    # python -m venv venv
    # source venv/bin/activate  (or venv\Scripts\activate on Windows)
    pip install -r requirements.txt
    ```
    (The `start_system.py` script also tries to install key packages if you miss this.)
3.  **Start the System:**
    ```bash
    python start_system.py
    ```
    This usually starts the server at `http://localhost:8000`.

### Testing
*   **API Docs:** Go to `http://localhost:8000/docs` in your browser to try the API.
*   **Sample Tests:** Run `python test_samples.py` (after starting the server) to test with files in the `samples/` folder.

## Key Technologies
*   **Python**
*   **FastAPI** (for the web API)
*   **SQLite** (for the database)
*   **PyPDF2** (for reading text from actual PDF files when uploaded)

## Note on PDF Files
*   The system can read text directly from `.pdf` files you upload.
*   It can also process plain text that looks like it came from a PDF (like the `.txt` files in the `samples/pdfs/` folder).

---
Built by: Jeevan Joseph (jeevanjoseph03)
Purpose: Learning project for AI agent development