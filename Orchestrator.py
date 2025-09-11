"""
The orchestrator managing the AI agents & routing requests
"""

import json
import re
from typing import Dict, List

from GroqLLM import GroqLLM
from PowerPointAgent import PowerPointAgent
from ContentWriterAgent import ContentWriterAgent
from PredictorAgent import PredictorAgent


class Orchestrator:
    def __init__(self, api_key: str):
        self.llm = GroqLLM(api_key)
        
        # Initialize agents
        self.powerpoint_agent = PowerPointAgent(self.llm)
        self.content_agent = ContentWriterAgent(self.llm)
        self.predictor_agent = PredictorAgent()
        
        self.conversation_history = []

    def analyze_request(self, user_input: str) -> Dict:
        """Analyze user request and determine appropriate action"""
        system_prompt = """You are an AI orchestrator that routes user requests to specialized agents.

CRITICAL: Respond with ONLY valid JSON in this exact format:
{"action": "action_name", "parameters": {...}}

Available actions:
1. create_presentation - Creates PowerPoint presentations
   Parameters: {"topic": "string", "slides": number}

2. write_content - Write content
   Parameters: {"topic": "string", "type": "article|report|summary", "length": "short|medium|long"}

3. make_prediction - Performs regression analysis
   Parameters: {"data": [{"col1": val, "col2": val}], "target": "column_name"}

EXAMPLES:
User: "Make a 4-slide presentation about climate change"
{"action": "create_presentation", "parameters": {"topic": "climate change", "slides": 4}}

User: "Write a long article about machine learning"
{"action": "write_content", "parameters": {"topic": "machine learning", "type": "article", "length": "long"}}

Respond with JSON only, no additional text."""

        full_prompt = f"{system_prompt}\n\nUser Request: {user_input}\n\nJSON Response:"

        try:
            response = self.llm.generate(full_prompt, max_tokens=200)
            
            # Try to extract JSON from response
            json_patterns = [
                r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Nested JSON
                r'\{[^{}]+\}',  # Simple JSON
            ]

            for pattern in json_patterns:
                json_match = re.search(pattern, response, re.DOTALL)
                if json_match:
                    json_str = json_match.group().strip()
                    try:
                        parsed = json.loads(json_str)
                        if isinstance(parsed, dict) and "action" in parsed:
                            return parsed
                    except json.JSONDecodeError:
                        continue

            # If no valid JSON found, try to infer intent
            return self._fallback_intent_detection(user_input)

        except Exception as e:
            print(f"LLM Error: {e}")
            return {"action": "error", "parameters": {"error": str(e)}}

    def _fallback_intent_detection(self, user_input: str) -> Dict:
        """Simple rule-based fallback if JSON parsing fails"""
        user_lower = user_input.lower()

        if any(word in user_lower for word in ["powerpoint", "presentation", "slides", "ppt"]):
            # Extract number of slides if mentioned
            slides_match = re.search(r'(\d+)[\s-]*slide', user_input)
            slides = int(slides_match.group(1)) if slides_match else 3
            return {"action": "create_presentation", "parameters": {"topic": "Demo", "slides": slides}}
        
        elif any(word in user_lower for word in ["write", "article", "content", "essay", "report"]):
            type = "article"
            if "report" in user_lower:
                type = "report"
            elif "summary" in user_lower:
                type = "summary"
            return {"action": "write_content", "parameters": {"topic": "Demo", "type": type, "length": "medium"}}
        
        elif any(word in user_lower for word in ["predict", "regression", "model", "forecast"]):
            return {"action": "make_prediction", "parameters": {"data": [], "target": "y"}}
        
        else:
            return {"action": "help", "parameters": {}}

    def handle_request(self, user_input: str) -> Dict:
        """Handle a user request by analyzing it and routing to appropriate agent"""
        print(f"User: {user_input}")

        # Add to conversation history
        self.conversation_history.append({"user": user_input})

        # Get action plan from LLM
        plan = self.analyze_request(user_input)
        print(f"AI Plan: {plan}")

        action = plan.get("action", "help")
        params = plan.get("parameters", {})

        # Execute the action
        try:
            if action == "create_presentation":
                if not isinstance(params, dict):
                    params = {}
                slides = params.get("slides")
                try:
                    slides = int(slides)
                except (TypeError, ValueError):
                    slides = 4
                params["slides"] = slides
                result = self.powerpoint_agent.create_presentation(**params)
            elif action == "write_content":
                result = self.content_agent.write_content(**params)
            elif action == "make_prediction":
                result = self.predictor_agent.make_prediction(**params)
            elif action == "help":
                result = self._get_help_response()
            else:
                result = {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }

            # Add result to history
            self.conversation_history.append({
                "action": action,
                "params": params,
                "result": result
            })

            return result

        except Exception as e:
            error_result = {
                "success": False,
                "error": f"Agent '{action}' failed: {str(e)}"
            }
            print(f"Error: {error_result['error']}")
            return error_result

    def _get_help_response(self) -> Dict:
        """Return help information about available capabilities"""
        return {
            "success": True,
            "message": "AI Assistant - Available capabilities:",
            "capabilities": {
                "Presentations": [
                    "Create PowerPoint presentations on any topic",
                    "Specify number of slides (e.g., '5-slide presentation about AI')",
                    "Automatic content generation and formatting"
                ],
                "Content Writing": [
                    "Write articles, reports, or summaries",
                    "Choose length: short, medium, or long",
                    "Professional formatting and structure"
                ],
                "Data Analysis": [
                    "Perform regression analysis on your data",
                    "Make predictions based on patterns",
                    "Get model performance metrics"
                ]
            },
            "examples": [
                "Make a 6-slide presentation about renewable energy",
                "Write a long article about artificial intelligence",
                "Create a business report on market trends",
                "Predict sales from marketing data"
            ]
        }

    def get_conversation_history(self) -> List[Dict]:
        """Get the conversation history"""
        return self.conversation_history

    def clear_history(self):
        """Clear the conversation history"""
        self.conversation_history = []