"""
FastAPI main application file
"""

import os
import datetime
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from uuid import uuid4
import uvicorn

from config import Config
from Orchestrator import Orchestrator
from api_models import (
    GeneralRequest, PresentationRequest, ContentRequest, PredictionRequest, 
    PresentationResponse, ContentResponse, PredictionResponse, 
    HelpResponse, HealthResponse
)

# Validate configuration on startup
Config.validate()

# Initialize FastAPI app
app = FastAPI(
    title="AI Agents API",
    description="API for PowerPoint generation, content writing, and predictions",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files 
if not os.path.exists(Config.OUTPUT_DIR):
    os.makedirs(Config.OUTPUT_DIR)

if not os.path.exists(Config.UPLOAD_DIR):
    os.makedirs(Config.UPLOAD_DIR)

app.mount("/files", StaticFiles(directory=Config.OUTPUT_DIR), name="files")
app.mount("/uploads", StaticFiles(directory=Config.UPLOAD_DIR), name="uploads")


# Initialize orchestrator
orchestrator = Orchestrator(Config.GROQ_API_KEY)


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI Agents API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    llm_available = orchestrator.llm.is_available()
    
    return HealthResponse(
        status="healthy" if llm_available else "degraded",
        timestamp=datetime.datetime.now().isoformat(),
        llm_available=llm_available
    )


@app.post("/chat", response_model=Dict[str, Any])
async def chat(request: GeneralRequest):
    """General chat endpoint that routes to the appropriate agents"""
    print(f"Message: {request.message}")
    print(f"Type: GeneralRequest")
    try:
        result = orchestrator.handle_request(request.message)
        print(f"Result success: {result.get('success')}")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_files(message: str = Form(...), files: List[UploadFile] = File(...)):
    """Upload files + message"""
    try:
        file_paths = []
        for f in files:
            unique_name = f"{uuid4()}_{f.filename}"
            path = os.path.join(Config.UPLOAD_DIR, unique_name)
            with open(path, "wb") as buffer:
                buffer.write(await f.read())
            file_paths.append(path)
        result = orchestrator.handle_request(message, file_paths)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/presentation", response_model=PresentationResponse)
async def create_presentation(request: PresentationRequest):
    """Create a PowerPoint presentation"""
    print(f"Type: PresentationRequest")
    try:
        result = orchestrator.powerpoint_agent.create_presentation(
            topic=request.topic,
            slides=request.slides
        )        
        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
            
        return PresentationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/content", response_model=ContentResponse)
async def write_content(request: ContentRequest):
    """Generate written content"""
    try:
        result = orchestrator.content_agent.write_content(
            topic=request.topic,
            type=request.type,
            length=request.length
        )
        
        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
            
        return ContentResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/prediction", response_model=PredictionResponse)
async def make_prediction(request: PredictionRequest):
    """Perform regression analysis and predictions"""
    try:
        result = orchestrator.predictor_agent.make_prediction(
            data=request.data,
            target=request.target
        )
        
        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
            
        return PredictionResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/help", response_model=HelpResponse)
async def get_help():
    """Get help information about API capabilities"""
    result = orchestrator._get_help_response()
    return HelpResponse(**result)


@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated files"""
    file_path = os.path.join(Config.OUTPUT_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type based on file extension
    media_types = {
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.txt': 'text/plain',
        '.pdf': 'application/pdf'
    }
    
    file_extension = os.path.splitext(filename)[1].lower()
    media_type = media_types.get(file_extension, 'application/octet-stream')
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )


@app.delete("/history")
async def clear_history():
    """Clear conversation history"""
    orchestrator.clear_history()
    return {"message": "Conversation history cleared"}


@app.get("/history")
async def get_history():
    """Get conversation history"""
    return {"history": orchestrator.get_conversation_history()}


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "message": "Check /docs for available endpoints"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc)}
    )


if __name__ == "__main__":
    print("Starting AI Agents API...")
    print(f"API Documentation: http://localhost:{Config.API_PORT}/docs")
    print(f"Health Check: http://localhost:{Config.API_PORT}/health")
    
    uvicorn.run(
        "main:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=Config.DEBUG,
        log_level="info"
    )