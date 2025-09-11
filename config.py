"""
Configuration file for API settings and secrets.
Keep this file private
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Get API key from environment variable
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your-api-key-here")
    
    # API Settings
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    DEBUG = True
    
    # File storage settings
    UPLOAD_DIR = "uploads"
    OUTPUT_DIR = "outputs"
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    @classmethod
    def validate(cls):
        """Validate that required configuration is present"""
        if not cls.GROQ_API_KEY or cls.GROQ_API_KEY == "your-api-key-here":
            raise ValueError("GROQ_API_KEY must be set in environment variables or .env file")
        
        # Create directories if they don't exist
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)