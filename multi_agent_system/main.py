from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json
import uuid
from datetime import datetime
import asyncio
from dataclasses import asdict # For converting dataclasses to dict

# Import our agents and components
from multi_agent_system.memory.memory_store import MemoryStore, InputMetadata
from multi_agent_system.agents.classifier_agent import ClassifierAgent, ClassificationResult, FormatType, IntentType
from multi_agent_system.agents.email_agent import EmailAgent, EmailAnalysis
from multi_agent_system.agents.json_agent import JSONAgent, JSONAnalysis
from multi_agent_system.agents.pdf_agent import PDFAgent, PDFAnalysis # Assuming PDFAnalysis is defined here
from multi_agent_system.routers.action_router import ActionRouter, ActionRequest, ActionResult, ActionType, ActionPriority

app = FastAPI(title="Multi-Format Autonomous AI System")

# Initialize agents and components
memory_store = MemoryStore() # Uses default "memory_store.db"
classifier_agent = ClassifierAgent()
email_agent = EmailAgent()
json_agent = JSONAgent()
pdf_agent = PDFAgent()
action_router = ActionRouter(memory_store=memory_store)

# --- Pydantic Models for API ---
class ProcessingRequest(BaseModel):
    content: str = Field(..., description="Text content of the email, JSON string, or text extracted from PDF.")
    filename: Optional[str] = Field(None, description="Original filename, helps in format classification.")
    # content_type: Optional[str] = None # Can be inferred or less critical if content is always string
    # metadata: Optional[Dict[str, Any]] = None # For additional context if needed

class ClassificationResponseSchema(BaseModel): # Schema for the classification part of the response
    format_type: str # Using str for enum values
    intent: str    # Using str for enum values
    confidence: float
    reasoning: str

class ProcessingResponse(BaseModel):
    session_id: str
    classification: ClassificationResponseSchema
    agent_results: Dict[str, Any] = Field(default_factory=dict)
    actions_taken: List[Dict[str, Any]] = Field(default_factory=list)
    processing_summary: Dict[str, Any]
    status: str

class SessionTraceResponse(BaseModel):
    session_info: Dict[str, Any]
    agent_outputs: List[Dict[str, Any]]
    actions_taken: List[Dict[str, Any]]


# --- API Endpoints ---
@app.post("/process/text", response_model=ProcessingResponse, summary="Process Text Content")
async def process_text_content(
    request: ProcessingRequest,
    background_tasks: BackgroundTasks
):
    """
    Processes raw text content. The system will attempt to classify its format (Email, JSON, PDF-like text)
    and business intent, then route to the appropriate specialized agent for further analysis and action.
    """
    session_id = str(uuid.uuid4())
    start_time = datetime.now()
    memory_store.start_session(session_id, source="text_api", filename=request.filename)
    
    agent_results: Dict[str, Any] = {}
    actions_taken_response: List[Dict[str, Any]] = []
    processed_by_agent_name: Optional[str] = None
    final_status = "failed_pre_processing" # Default status

    try:
        # 1. Classify content
        classification_obj: ClassificationResult = classifier_agent.classify(request.content, request.filename)
        
        # Store initial classification
        input_meta = InputMetadata(
            source="text_api",
            timestamp=start_time,
            format_type=classification_obj.format_type.value,
            intent=classification_obj.intent.value,
            file_path=request.filename
        )
        memory_store.store_input_metadata(input_meta, session_id, classification_obj.reasoning)

        # Prepare classification part of the response
        classification_resp_dict = ClassificationResponseSchema(
            format_type=classification_obj.format_type.value,
            intent=classification_obj.intent.value,
            confidence=classification_obj.confidence,
            reasoning=classification_obj.reasoning
        )

        # 2. Route to specialized agent based on classification
        if classification_obj.format_type == FormatType.EMAIL:
            processed_by_agent_name = "email_agent"
            email_analysis_obj: EmailAnalysis = email_agent.process_email(request.content)
            agent_results[processed_by_agent_name] = email_agent.get_extracted_fields(email_analysis_obj)
        elif classification_obj.format_type == FormatType.JSON:
            processed_by_agent_name = "json_agent"
            # Determine schema for JSON agent if possible, or let it use a default
            schema_for_json = "transaction_schema" # Default, could be dynamic
            if classification_obj.intent == IntentType.FRAUD_RISK or classification_obj.intent == IntentType.TRANSACTION_DATA:
                schema_for_json = "transaction_schema"
            # elif classification_obj.intent == IntentType.USER_PROFILE_UPDATE: # Example
            #     schema_for_json = "user_profile_schema"

            json_analysis_obj: JSONAnalysis = json_agent.process_json(request.content, schema_to_validate=schema_for_json)
            agent_results[processed_by_agent_name] = json_agent.get_extracted_fields(json_analysis_obj)
        elif classification_obj.format_type == FormatType.PDF: # Handles text content classified as PDF
            processed_by_agent_name = "pdf_agent"
            pdf_analysis_obj: PDFAnalysis = pdf_agent.process_pdf(request.content, input_type="text_content")
            agent_results[processed_by_agent_name] = pdf_agent.get_extracted_fields(pdf_analysis_obj)
        else: # UNKNOWN or other types
            agent_results["classifier_agent"] = {"message": f"Content classified as {classification_obj.format_type.value}, no specific data processing agent assigned."}
            # No specific agent, so no agent-specific action will be triggered typically

        # Store agent results in memory
        if processed_by_agent_name and processed_by_agent_name in agent_results:
            memory_store.store_extracted_fields(session_id, processed_by_agent_name, agent_results[processed_by_agent_name])

        # 3. Determine and trigger follow-up actions
        action_request_obj: Optional[ActionRequest] = None
        if processed_by_agent_name and processed_by_agent_name in agent_results:
            action_request_obj = action_router.create_action_from_agent_output(
                processed_by_agent_name, agent_results[processed_by_agent_name], session_id
            )
        
        if action_request_obj:
            # Add to background tasks for actual execution
            background_tasks.add_task(action_router.route_action, action_request_obj)
            actions_taken_response.append({
                "action_type": action_request_obj.action_type.value,
                "priority": action_request_obj.priority.value,
                "status": "queued", # Initial status
                "payload_summary": str(action_request_obj.payload)[:100] + "..." # Summary
            })
        
        final_status = "completed"

    except HTTPException as e: # Re-raise HTTPExceptions directly
        memory_store.end_session(session_id, f"failed_http_{e.status_code}")
        raise e
    except Exception as e:
        print(f"ERROR during processing session {session_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        final_status = "failed_internal_error"
        memory_store.end_session(session_id, final_status)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
    processing_summary = {
        "total_agents_involved": 1 if processed_by_agent_name else 0,
        "total_actions_queued": len(actions_taken_response),
        "processing_time_ms": round(processing_time_ms, 2),
        "status": final_status
    }
    memory_store.end_session(session_id, final_status)

    return ProcessingResponse(
        session_id=session_id,
        classification=classification_resp_dict,
        agent_results=agent_results,
        actions_taken=actions_taken_response,
        processing_summary=processing_summary,
        status="success" # API call itself was successful, check processing_summary for internal status
    )

@app.post("/process/file", response_model=ProcessingResponse, summary="Process Uploaded File (PDF, EML, JSON, TXT)")
async def process_uploaded_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Processes an uploaded file. Supports PDF (parsed with PyPDF2), EML (processed as text),
    JSON files, and TXT files (treated as potential PDF-like text or general text).
    """
    session_id = str(uuid.uuid4())
    start_time = datetime.now()
    memory_store.start_session(session_id, source="file_upload_api", filename=file.filename)

    agent_results: Dict[str, Any] = {}
    actions_taken_response: List[Dict[str, Any]] = []
    processed_by_agent_name: Optional[str] = None
    final_status = "failed_pre_processing"
    content_to_process = ""

    try:
        file_content_bytes = await file.read()
        
        # Attempt to decode as UTF-8 text first, common for .eml, .json, .txt
        try:
            content_to_process = file_content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # If UTF-8 fails, it might be a binary PDF or other encoding.
            # For PDF, PDFAgent will handle bytes. For others, this might be an issue.
            if file.filename and file.filename.lower().endswith(".pdf"):
                content_to_process = file_content_bytes # Pass bytes to PDFAgent
            else:
                # Could try other encodings or raise error
                raise HTTPException(status_code=400, detail=f"Could not decode file {file.filename} as UTF-8 text. If it's a binary PDF, ensure the filename ends with .pdf.")

        # 1. Classify content
        classification_obj: ClassificationResult = classifier_agent.classify(
            content_to_process if isinstance(content_to_process, str) else "Binary PDF content, see filename.", 
            file.filename
        )
        
        input_meta = InputMetadata(
            source="file_api",
            timestamp=start_time,
            format_type=classification_obj.format_type.value,
            intent=classification_obj.intent.value,
            file_path=file.filename
        )
        memory_store.store_input_metadata(input_meta, session_id, classification_obj.reasoning)

        classification_resp_dict = ClassificationResponseSchema(
            format_type=classification_obj.format_type.value,
            intent=classification_obj.intent.value,
            confidence=classification_obj.confidence,
            reasoning=classification_obj.reasoning
        )

        # 2. Route to specialized agent
        if classification_obj.format_type == FormatType.EMAIL:
            processed_by_agent_name = "email_agent"
            if not isinstance(content_to_process, str): 
                raise HTTPException(status_code=400, detail="Email content must be text.")
            email_analysis_obj: EmailAnalysis = email_agent.process_email(content_to_process)
            agent_results[processed_by_agent_name] = email_agent.get_extracted_fields(email_analysis_obj)

        elif classification_obj.format_type == FormatType.JSON:
            processed_by_agent_name = "json_agent"
            if not isinstance(content_to_process, str):
                raise HTTPException(status_code=400, detail="JSON content must be text.")
            schema_for_json = "transaction_schema" # Default
            json_analysis_obj: JSONAnalysis = json_agent.process_json(content_to_process, schema_to_validate=schema_for_json)
            agent_results[processed_by_agent_name] = json_agent.get_extracted_fields(json_analysis_obj)

        elif classification_obj.format_type == FormatType.PDF:
            processed_by_agent_name = "pdf_agent"
            if isinstance(content_to_process, str): # Text classified as PDF
                pdf_analysis_obj: PDFAnalysis = pdf_agent.process_pdf(content_to_process, input_type="text_content")
            else: # Actual PDF bytes
                pdf_analysis_obj: PDFAnalysis = pdf_agent.process_pdf(file_content_bytes, input_type="bytes")
            agent_results[processed_by_agent_name] = pdf_agent.get_extracted_fields(pdf_analysis_obj)
        else:
            agent_results["classifier_agent"] = {"message": f"File content classified as {classification_obj.format_type.value}, no specific data processing agent assigned."}

        if processed_by_agent_name and processed_by_agent_name in agent_results:
            memory_store.store_extracted_fields(session_id, processed_by_agent_name, agent_results[processed_by_agent_name])

        # 3. Determine and trigger follow-up actions (same as /process/text)
        action_request_obj: Optional[ActionRequest] = None
        if processed_by_agent_name and processed_by_agent_name in agent_results:
            action_request_obj = action_router.create_action_from_agent_output(
                processed_by_agent_name, agent_results[processed_by_agent_name], session_id
            )
        
        if action_request_obj:
            background_tasks.add_task(action_router.route_action, action_request_obj)
            actions_taken_response.append({
                "action_type": action_request_obj.action_type.value,
                "priority": action_request_obj.priority.value,
                "status": "queued",
                "payload_summary": str(action_request_obj.payload)[:100] + "..."
            })
        final_status = "completed"

    except HTTPException as e:
        memory_store.end_session(session_id, f"failed_http_{e.status_code}")
        raise e
    except Exception as e:
        print(f"ERROR during file processing session {session_id} for file {file.filename}: {str(e)}")
        import traceback
        traceback.print_exc()
        final_status = "failed_internal_error"
        memory_store.end_session(session_id, final_status)
        raise HTTPException(status_code=500, detail=f"Internal server error processing file: {str(e)}")

    processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
    processing_summary = {
        "total_agents_involved": 1 if processed_by_agent_name else 0,
        "total_actions_queued": len(actions_taken_response),
        "processing_time_ms": round(processing_time_ms, 2),
        "status": final_status
    }
    memory_store.end_session(session_id, final_status)

    return ProcessingResponse(
        session_id=session_id,
        classification=classification_resp_dict,
        agent_results=agent_results,
        actions_taken=actions_taken_response,
        processing_summary=processing_summary,
        status="success"
    )


@app.get("/session/{session_id}", response_model=SessionTraceResponse, summary="Get Session Trace")
async def get_session_trace(session_id: str):
    """
    Retrieves the full trace for a given processing session, including input metadata,
    agent extractions, and actions taken.
    """
    trace_data = memory_store.get_session_trace(session_id)
    if "error" in trace_data:
        raise HTTPException(status_code=404, detail=trace_data["error"])
    return SessionTraceResponse(**trace_data)

@app.get("/status", summary="System Health Check")
async def get_status():
    return {"status": "healthy", "timestamp": datetime.now().isoformat(), "message": "Multi-Agent AI System is operational."}

# To run the app (e.g., in start_system.py or directly):
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)