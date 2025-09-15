"""
The orchestrator managing the AI agents & routing requests with file processing if necessary
"""

import json
import re
import os
from typing import Dict, List, Optional

from GroqLLM import GroqLLM
from PowerPointAgent import PowerPointAgent
from ContentWriterAgent import ContentWriterAgent
from PredictorAgent import PredictorAgent
from FileProcessor import FileProcessor


class Orchestrator:
    def __init__(self, api_key: str):
        self.llm = GroqLLM(api_key)
        
        # Initialize agents
        self.powerpoint_agent = PowerPointAgent(self.llm)
        self.content_agent = ContentWriterAgent(self.llm)
        self.predictor_agent = PredictorAgent()
        self.file_processor = FileProcessor(self.llm)
        
        self.conversation_history = []

    def analyze_request_with_files(self, user_input: str, file_paths: List[str]) -> Dict:
        """Analyze user request when files are uploaded"""
        system_prompt = """You are an AI orchestrator that routes user requests involving uploaded files.

CRITICAL: Respond with ONLY valid JSON in this exact format:
{"action": "action_name", "parameters": {...}}

Available actions for file processing:
1. process_files_for_presentation - Create presentation from files
   Parameters: {"task": "user_request", "slides": number, "query": "specific_search_or_null"}

2. process_files_for_content - Write content based on files
   Parameters: {"task": "user_request", "type": "article|report|summary", "length": "short|medium|long", "query": "specific_search_or_null"}

3. process_files_general - General file analysis
   Parameters: {"task": "user_request", "query": "specific_search_or_null"}

Rules:
- If user mentions "presentation", "slides", "powerpoint", use process_files_for_presentation
- If user mentions "write", "article", "report", "summary", use process_files_for_content  
- If the user has a specific question or a specific topic they want covered in relation to the files, set "query" to that question or topic.
- If user wants general overview/analysis, set "query" to null
- Extract number of slides if mentioned for presentations

EXAMPLES:
User: "Make a 5-slide presentation about the key findings in these files"
{"action": "process_files_for_presentation", "parameters": {"task": "key findings presentation", "slides": 5, "query": null}}

User: "What do these documents say about AI trends?"
{"action": "process_files_general", "parameters": {"task": "analyze AI trends", "query": "AI trends"}}

User: "Write a report summarizing the financial data"
{"action": "process_files_for_content", "parameters": {"task": "financial data report", "type": "report", "length": "medium", "query": "financial data"}}"""

        full_prompt = f"{system_prompt}\n\nUser Request: {user_input}\n\nJSON Response:"

        try:
            response = self.llm.generate(full_prompt, max_tokens=300)
            
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

            # Fallback for file processing
            return self._fallback_file_intent_detection(user_input)

        except Exception as e:
            print(f"LLM Error: {e}")
            return {"action": "error", "parameters": {"error": str(e)}}

    def analyze_request(self, user_input: str) -> Dict:
        """Analyze user request and determine appropriate action (no files)"""
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

    def _fallback_file_intent_detection(self, user_input: str) -> Dict:
        """Simple rule-based fallback for file processing if JSON parsing fails"""
        user_lower = user_input.lower()

        if any(word in user_lower for word in ["powerpoint", "presentation", "slides", "ppt"]):
            slides_match = re.search(r'(\d+)[\s-]*slide', user_input)
            slides = int(slides_match.group(1)) if slides_match else 4
            return {"action": "process_files_for_presentation", "parameters": {"task": "file analysis presentation", "slides": slides, "query": None}}
        
        elif any(word in user_lower for word in ["write", "article", "content", "essay", "report"]):
            content_type = "report" if "report" in user_lower else "article"
            return {"action": "process_files_for_content", "parameters": {"task": "file analysis content", "type": content_type, "length": "medium", "query": None}}
        
        else:
            return {"action": "process_files_general", "parameters": {"task": "analyze uploaded files", "query": None}}

    def _fallback_intent_detection(self, user_input: str) -> Dict:
        """Simple rule-based fallback if JSON parsing fails"""
        user_lower = user_input.lower()

        if any(word in user_lower for word in ["powerpoint", "presentation", "slides", "ppt"]):
            slides_match = re.search(r'(\d+)[\s-]*slide', user_input)
            slides = int(slides_match.group(1)) if slides_match else 3
            return {"action": "create_presentation", "parameters": {"topic": "Demo", "slides": slides}}
        
        elif any(word in user_lower for word in ["write", "article", "content", "essay", "report"]):
            content_type = "article"
            if "report" in user_lower:
                content_type = "report"
            elif "summary" in user_lower:
                content_type = "summary"
            return {"action": "write_content", "parameters": {"topic": "Demo", "type": content_type, "length": "medium"}}
        
        elif any(word in user_lower for word in ["predict", "regression", "model", "forecast"]):
            return {"action": "make_prediction", "parameters": {"data": [], "target": "y"}}
        
        else:
            return {"action": "help", "parameters": {}}
        
    def handle_request(self, user_input: str, file_paths: Optional[List[str]] = None) -> Dict:
        """Main entry point to handle user requests, with optional file uploads"""
        if file_paths:
            return self.handle_request_with_files(user_input, file_paths)
        else:
            return self.handle_request_no_files(user_input)
        
    def handle_request_with_files(self, user_input: str, file_paths: List[str]) -> Dict:
        """Handle a user request with uploaded files"""
        print(f"User: {user_input}")
        print(f"Files: {[os.path.basename(f) for f in file_paths]}")

        # Add to conversation history
        self.conversation_history.append({"user": user_input, "files": [os.path.basename(f) for f in file_paths]})

        # Get action plan for file processing
        plan = self.analyze_request_with_files(user_input, file_paths)
        print(f"AI Plan: {plan}")

        action = plan.get("action", "process_files_general")
        params = plan.get("parameters", {})

        try:
            if action == "process_files_for_presentation":
                result = self._handle_files_for_presentation(file_paths, params)
            elif action == "process_files_for_content":
                result = self._handle_files_for_content(file_paths, params)
            elif action == "process_files_general":
                result = self._handle_files_general(file_paths, params)
            else:
                result = {"success": False, "error": f"Unknown file processing action: {action}"}

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
                "error": f"File processing failed: {str(e)}"
            }
            print(f"Error: {error_result['error']}")
            return error_result

    def handle_request_no_files(self, user_input: str) -> Dict:
        """Handle a user request without files"""
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

    
    def _handle_files_for_presentation(self, file_paths: List[str], params: Dict) -> Dict:
        """Process files and create presentation"""
        task = params.get("task", "File analysis presentation")
        slides = params.get("slides", 4)
        query = params.get("query")

        # Determine task type for file processor
        task_type = "presentation"
        if query:
            task_type = "query"

        # Process files
        file_result = self.file_processor.process_files_for_task(file_paths, task, task_type)
        
        if not file_result.get("success", False):
            return file_result

        processed_content = file_result.get("processed_content", "")
        print(f"Processed content length: {processed_content[:4000]}")
        approach = file_result.get("approach", "unknown")

        # Create presentation from processed content
        presentation_result = self.powerpoint_agent.create_presentation_from_content(
            processed_content=processed_content,
            approach=approach,
            slides=slides,
            source_files=[os.path.basename(f) for f in file_paths],
            query=query
        )

        # Add file processing info to result
        if presentation_result.get("success", False):
            presentation_result["file_processing"] = {
                "approach": approach,
                "files_processed": len(file_paths),
                "query_used": query is not None
            }

        return presentation_result

    def _handle_files_for_content(self, file_paths: List[str], params: Dict) -> Dict:
        """Process files and write content"""
        task = params.get("task", "File analysis content")
        content_type = params.get("type", "article")
        length = params.get("length", "medium")
        query = params.get("query")

        # Determine task type for file processor
        task_type = "content"
        if query:
            task_type = "query"

        # Process files
        file_result = self.file_processor.process_files_for_task(file_paths, task, task_type)
        
        if not file_result.get("success", False):
            return file_result

        processed_content = file_result.get("processed_content", "")
        approach = file_result.get("approach", "unknown")

        # Write content from processed files
        content_result = self.content_agent.write_content_from_files(
            processed_content=processed_content,
            approach=approach,
            content_type=content_type,
            length=length,
            source_files=[os.path.basename(f) for f in file_paths]
        )

        # Add file processing info to result
        if content_result.get("success", False):
            content_result["file_processing"] = {
                "approach": approach,
                "files_processed": len(file_paths),
                "query_used": query is not None
            }

        return content_result

    def _handle_files_general(self, file_paths: List[str], params: Dict) -> Dict:
        """General file processing and analysis"""
        task = params.get("task", "Analyze uploaded files")
        query = params.get("query")

        # Determine task type for file processor
        task_type = "general"
        if query:
            task_type = "query"

        # Process files
        file_result = self.file_processor.process_files_for_task(file_paths, task, task_type)
        
        if not file_result.get("success", False):
            return file_result

        processed_content = file_result.get("processed_content", "")
        approach = file_result.get("approach", "unknown")

        # For general analysis, return processed content directly with some formatting
        summary_prompt = f"""Based on the following processed file content, provide a clear and comprehensive summary:

{processed_content}

Provide a well-structured summary that highlights key points, findings, and insights."""

        try:
            summary = self.llm.generate(summary_prompt, max_tokens=800)
            
            return {
                "success": True,
                "message": "File analysis completed",
                "summary": summary,
                "file_processing": {
                    "approach": approach,
                    "files_processed": len(file_paths),
                    "source_files": [os.path.basename(f) for f in file_paths],
                    "query_used": query is not None,
                    "query": query
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to generate summary: {str(e)}"
            }

    def _get_help_response(self) -> Dict:
        """Return help information about available capabilities"""
        return {
            "success": True,
            "message": "AI Assistant - Available capabilities:",
            "capabilities": {
                "Presentations": [
                    "Create PowerPoint presentations on any topic",
                    "Create presentations from uploaded files",
                    "Specify number of slides (e.g., '5-slide presentation about AI')",
                    "Automatic content generation and formatting"
                ],
                "Content Writing": [
                    "Write articles, reports, or summaries",
                    "Create content based on uploaded files",
                    "Choose length: short, medium, or long",
                    "Professional formatting and structure"
                ],
                "File Processing": [
                    "Upload and analyze multiple document types (PDF, Word, TXT)",
                    "Intelligent content extraction and summarization",
                    "Query-based information retrieval from files",
                    "Automatic processing approach selection based on content size"
                ],
                "Data Analysis": [
                    "Perform regression analysis on your data",
                    "Make predictions based on patterns",
                    "Get model performance metrics"
                ]
            },
            "examples": [
                "Make a 6-slide presentation about renewable energy",
                "Create a presentation from these uploaded documents",
                "What do these files say about AI trends?",
                "Write a report based on the uploaded data",
                "Summarize the key findings in these documents"
            ]
        }

    def get_conversation_history(self) -> List[Dict]:
        """Get the conversation history"""
        return self.conversation_history

    def clear_history(self):
        """Clear the conversation history"""
        self.conversation_history = []