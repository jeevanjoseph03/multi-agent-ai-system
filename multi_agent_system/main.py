from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json
import uuid
from datetime import datetime
import asyncio

# Import our agents and components
from multi_agent_system.memory.memory_store import MemoryStore, InputMetadata
from multi_agent_system.agents.classifier_agent import ClassifierAgent
from multi_agent_system.agents.email_agent import EmailAgent
from multi_agent_system.agents.json_agent import JSONAgent
from multi_agent_system.agents.pdf_agent import PDFAgent
from multi_agent_system.routers.action_router import ActionRouter

# Pydantic models for API
class ProcessingRequest(BaseModel):
    content: str
    content_type: Optional[str] = None
    filename: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ProcessingResponse(BaseModel):
    session_id: str
    classification: Dict[str, Any]
    agent_results: Dict[str, Any]
    actions_taken: List[Dict[str, Any]]
    processing_summary: Dict[str, Any]
    status: str

class SystemStatus(BaseModel):
    status: str
    agents_active: List[str]
    memory_store_connected: bool
    total_sessions_processed: int
    uptime_seconds: float

# Initialize FastAPI app
app = FastAPI(
    title="Multi-Agent AI System",
    description="AI system that processes Email, JSON, and PDF inputs with contextual decisioning & chained actions",
    version="1.0.0"
)

# Global components
memory_store = None
classifier_agent = None
email_agent = None
json_agent = None
pdf_agent = None
action_router = None
app_start_time = datetime.now()

@app.on_event("startup")
async def startup_event():
    """Initialize all system components on startup"""
    global memory_store, classifier_agent, email_agent, json_agent, pdf_agent, action_router
    
    print("🚀 Starting Multi-Agent AI System...")
    
    # Initialize memory store
    memory_store = MemoryStore()
    print("✅ Memory Store initialized")
    
    # Initialize agents
    classifier_agent = ClassifierAgent()
    email_agent = EmailAgent()
    json_agent = JSONAgent()
    pdf_agent = PDFAgent()
    print("✅ All agents initialized")
    
    # Initialize action router
    action_router = ActionRouter(memory_store)
    print("✅ Action Router initialized")
    
    print("🎉 Multi-Agent System ready!")

@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "message": "Multi-Agent AI System",
        "version": "1.0.0",
        "status": "active",
        "agents": ["classifier", "email", "json", "pdf"],
        "endpoints": {
            "process_text": "/process/text",
            "process_file": "/process/file", 
            "get_session": "/session/{session_id}",
            "system_status": "/status"
        }
    }

@app.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Get current system status and health"""
    uptime = (datetime.now() - app_start_time).total_seconds()
    
    # Count total sessions (simplified)
    try:
        # This is a simplified count - in a real system you'd query the database
        total_sessions = 10  # Placeholder
    except:
        total_sessions = 0
    
    return SystemStatus(
        status="healthy",
        agents_active=["classifier_agent", "email_agent", "json_agent", "pdf_agent"],
        memory_store_connected=memory_store is not None,
        total_sessions_processed=total_sessions,
        uptime_seconds=uptime
    )

@app.post("/process/text", response_model=ProcessingResponse)
async def process_text_content(
    request: ProcessingRequest,
    background_tasks: BackgroundTasks
):
    """
    Process text content (email or JSON string)
    """
    try:
        session_id = str(uuid.uuid4())
        
        # Step 1: Classify the content
        classification_result = classifier_agent.classify(request.content, request.filename)
        
        # Store input metadata
        metadata = InputMetadata(
            source="text_input",
            timestamp=datetime.now(),
            format_type=classification_result.format_type.value,
            intent=classification_result.intent.value,
            file_path=request.filename
        )
        memory_store.store_input_metadata(metadata, session_id)
        
        # Step 2: Route to appropriate agent
        agent_results = {}
        
        if classification_result.format_type.value == "email":
            email_analysis = email_agent.process_email(request.content)
            agent_results["email_agent"] = email_agent.get_extracted_fields(email_analysis)
            memory_store.store_extracted_fields(session_id, "email_agent", agent_results["email_agent"])
            
        elif classification_result.format_type.value == "json":
            json_analysis = json_agent.process_json(request.content)
            agent_results["json_agent"] = json_agent.get_extracted_fields(json_analysis)
            memory_store.store_extracted_fields(session_id, "json_agent", agent_results["json_agent"])
        
        
        elif classification_result.format_type.value == "pdf":
            pdf_analysis = pdf_agent.process_pdf(request.content, "text")
            agent_results["pdf_agent"] = pdf_agent.get_extracted_fields(pdf_analysis)
            memory_store.store_extracted_fields(session_id, "pdf_agent", agent_results["pdf_agent"])
        
        actions_taken = []
        for agent_name, agent_output in agent_results.items():
            action_request = action_router.create_action_from_agent_output(
                agent_name, agent_output, session_id
            )
            
            if action_request:
                # Execute action in background for better performance
                background_tasks.add_task(execute_action_async, action_request)
                actions_taken.append({
                    "action_type": action_request.action_type.value,
                    "priority": action_request.priority,
                    "status": "queued"
                })
        
        # Step 4: Create response
        return ProcessingResponse(
            session_id=session_id,
            classification={
                "format": classification_result.format_type.value,
                "intent": classification_result.intent.value,
                "confidence": classification_result.confidence,
                "reasoning": classification_result.reasoning
            },
            agent_results=agent_results,
            actions_taken=actions_taken,
            processing_summary={
                "total_agents_involved": len(agent_results),
                "total_actions_queued": len(actions_taken),
                "processing_time_ms": 0,  # Could add timing
                "status": "completed"
            },
            status="success"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/process/file")
async def process_file_upload(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Process uploaded file (PDF or other formats)
    """
    try:
        session_id = str(uuid.uuid4())
        
        # Read file content
        file_content = await file.read()
        
        # Determine processing based on file type
        if file.filename.lower().endswith('.pdf'):
            # Process as PDF
            pdf_analysis = pdf_agent.process_pdf(file_content, "bytes")
            agent_results = {"pdf_agent": pdf_agent.get_extracted_fields(pdf_analysis)}
            
            # Store metadata
            metadata = InputMetadata(
                source="file_upload",
                timestamp=datetime.now(),
                format_type="pdf",
                intent=pdf_analysis.document_type.value,
                file_path=file.filename
            )
            
        elif file.filename.lower().endswith(('.txt', '.eml')):
            # Process as email
            content = file_content.decode('utf-8')
            classification_result = classifier_agent.classify(content, file.filename)
            
            if classification_result.format_type.value == "email":
                email_analysis = email_agent.process_email(content)
                agent_results = {"email_agent": email_agent.get_extracted_fields(email_analysis)}
            else:
                raise HTTPException(status_code=400, detail="File content not recognized as email")
            
            metadata = InputMetadata(
                source="file_upload",
                timestamp=datetime.now(),
                format_type=classification_result.format_type.value,
                intent=classification_result.intent.value,
                file_path=file.filename
            )
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        # Store metadata and results
        memory_store.store_input_metadata(metadata, session_id)
        
        for agent_name, agent_output in agent_results.items():
            memory_store.store_extracted_fields(session_id, agent_name, agent_output)
        
        # Execute actions
        actions_taken = []
        for agent_name, agent_output in agent_results.items():
            action_request = action_router.create_action_from_agent_output(
                agent_name, agent_output, session_id
            )
            
            if action_request:
                background_tasks.add_task(execute_action_async, action_request)
                actions_taken.append({
                    "action_type": action_request.action_type.value,
                    "priority": action_request.priority,
                    "status": "queued"
                })
        
        return {
            "session_id": session_id,
            "filename": file.filename,
            "file_size_bytes": len(file_content),
            "processing_results": agent_results,
            "actions_taken": actions_taken,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")

@app.get("/session/{session_id}")
async def get_session_data(session_id: str):
    """
    Get all data for a specific session
    """
    try:
        session_data = memory_store.get_session_data(session_id)
        
        if not session_data["metadata"]:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session_id,
            "metadata": session_data["metadata"],
            "extracted_fields": session_data["extracted_fields"],
            "actions": session_data["actions"],
            "summary": {
                "total_fields_extracted": len(session_data["extracted_fields"]),
                "total_actions_taken": len(session_data["actions"]),
                "processing_status": "completed"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session: {str(e)}")

@app.delete("/session/{session_id}")
async def clear_session_data(session_id: str):
    """
    Clear all data for a specific session
    """
    try:
        memory_store.clear_session(session_id)
        return {"message": f"Session {session_id} cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear session: {str(e)}")

@app.get("/demo/sample-data")
async def get_sample_data():
    """
    Get sample data for testing the system
    """
    return {
        "sample_email": """From: frustrated.customer@example.com
To: support@company.com
Subject: URGENT: Broken Product - Need Immediate Refund

I am absolutely FURIOUS with your company! The product I received is completely broken and your customer service is TERRIBLE. I have been waiting 2 weeks for a response and this is UNACCEPTABLE!

I want to speak to your manager immediately and if this isn't resolved today, I will be contacting my lawyer!

This is the WORST experience I've ever had!""",
        
        "sample_json": {
            "transaction_id": "TXN-SUSPICIOUS-999",
            "amount": 15000,
            "user_id": "test_user",
            "timestamp": "2025-05-30T06:20:54Z",
            "flags": ["high_amount", "suspicious_user"]
        },
        
        "sample_pdf_text": """
INVOICE #INV-2025-001
Date: May 30, 2025
Due Date: June 30, 2025

Bill To: ABC Company
Total Amount: $25,000.00

This invoice contains GDPR-regulated customer data.
""",
        
        "endpoints": {
            "process_email": "POST /process/text with the sample_email",
            "process_json": "POST /process/text with the sample_json as string",
            "process_pdf": "POST /process/file with a PDF file"
        }
    }

async def execute_action_async(action_request):
    """
    Execute action asynchronously in background
    """
    try:
        result = action_router.route_action(action_request)
        print(f"✅ Action completed: {result.external_reference_id}")
    except Exception as e:
        print(f"❌ Action failed: {str(e)}")

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)