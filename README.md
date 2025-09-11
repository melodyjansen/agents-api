# AI Agents API

FastAPI-based LLM-powered content generation through specialized agents for creating PowerPoint presentations, writing content, and performing basic predictions.

## Features

- **PowerPoint Agent**: Creates formatted presentations on any topic
- **Content Writer Agent**: Generates articles, reports, and summaries
- **Predictor Agent**: Performs (very) basic linear regression analysis
- **Orchestrator**: Routes requests to appropriate agents via natural language

## Setup

### Requirements

Install the required dependencies:

```bash
pip install fastapi uvicorn python-pptx pandas scikit-learn python-dotenv pydantic requests
```

### API Key Configuration

This application uses the Groq API and requires a valid API key. You have two options:

#### Option 1: Environment File 
You can create a `.env` file in the project root:

```
GROQ_API_KEY=your-actual-api-key-here
```

#### Option 2: Direct Configuration
Or you can edit `config.py` and replace the default value:

```python
GROQ_API_KEY = "your-actual-api-key-here"
```

### Running the Application

Start the API server:

```bash
python main.py
```

The API will be available at:
- Main API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## API Endpoints

### General Chat
- `POST /chat` - Natural language requests routed to appropriate agents

### Specialized Endpoints
- `POST /presentation` - Create PowerPoint presentations
- `POST /content` - Generate written content
- `POST /prediction` - Perform regression analysis

### Utility
- `GET /health` - Check API and LLM status
- `GET /help` - List capabilities and examples
- `GET /download/{filename}` - Download generated files

## Usage Examples

### Chat Endpoint
```json
POST /chat
{
  "message": "Create a 5-slide presentation about renewable energy"
}
```

### Direct Presentation Creation
```json
POST /presentation
{
  "topic": "Machine Learning",
  "slides": 6
}
```

### Content Generation
```json
POST /content
{
  "topic": "Artificial Intelligence",
  "type": "article",
  "length": "long"
}
```

### Linear Regression Analysis
```json
POST /prediction
{
  "data": [
    {"x": 1, "y": 2.1},
    {"x": 2, "y": 3.9},
    {"x": 3, "y": 6.1},
    {"x": 4, "y": 7.8},
    {"x": 5, "y": 10.2}
  ],
  "target": "y"
}
```

## Output

Generated files are saved in the `outputs/` directory. When trying out any of the POST endpoints generating docs in `/docs` you can find `filename` in the response body, and subsequently, download the file via the `/download/{filename}` endpoint.

## File Structure

- `main.py` - FastAPI application entry point
- `Orchestrator.py` - Main request router and agent coordinator
- `PowerPointAgent.py` - PowerPoint presentation generator
- `ContentWriterAgent.py` - Text content generator
- `PredictorAgent.py` - Basic regression analysis
- `GroqLLM.py` - Groq API client
- `config.py` - Configuration settings
- `api_models.py` - Pydantic request/response models
