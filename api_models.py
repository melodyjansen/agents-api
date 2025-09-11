"""
Pydantic models for the API request/response validation
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


# Request Models
class GeneralRequest(BaseModel):
    message: str = Field(..., description="User request message", min_length=1)


class PresentationRequest(BaseModel):
    topic: str = Field(..., description="Topic of the presentation")
    slides: int = Field(default=4, ge=1, le=20, description="Number of slides")


class ContentRequest(BaseModel):
    topic: str = Field(..., description="Topic for content generation")
    type: str = Field(default="article", description="Type of content: article, report, or summary")
    length: str = Field(default="medium", description="Content length: short, medium, or long")


class PredictionRequest(BaseModel):
    data: List[Dict[str, Any]] = Field(..., description="Data for prediction")
    target: str = Field(..., description="Target column name for prediction")


# Response Models
class BaseResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


class PresentationResponse(BaseResponse):
    filename: Optional[str] = None
    filepath: Optional[str] = None
    slides_count: Optional[int] = None
    topic: Optional[str] = None


class ContentResponse(BaseResponse):
    filename: Optional[str] = None
    filepath: Optional[str] = None
    topic: Optional[str] = None
    content_type: Optional[str] = None
    length: Optional[str] = None
    word_count_estimate: Optional[int] = None
    preview: Optional[str] = None


class PredictionResponse(BaseResponse):
    model_info: Optional[Dict] = None
    performance: Optional[Dict] = None
    coefficients: Optional[Dict] = None
    sample_predictions: Optional[List[Dict]] = None
    data_used: Optional[List[Dict]] = None


class HelpResponse(BaseResponse):
    capabilities: Optional[Dict] = None
    examples: Optional[List[str]] = None


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    llm_available: bool