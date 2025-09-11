"""
Content Writer Agent for generating text content and outputting txt file
"""

import re
import os
from typing import Dict
import pandas as pd

from GroqLLM import GroqLLM
from config import Config


class ContentWriterAgent:
    def __init__(self, llm: GroqLLM):
        self.llm = llm

    def write_content(self, topic: str = "General Topic", type: str = "article", 
                     length: str = "medium") -> Dict:
        """Generate written content"""
        try:
            print(f"Generating {type} about '{topic}' ({length} length)...")

            # Ensure output directory exists
            os.makedirs(Config.OUTPUT_DIR, exist_ok=True)

            # Define length parameters
            length_specs = {
                "short": {"words": "300-500", "sections": 3},
                "medium": {"words": "500-800", "sections": 4},
                "long": {"words": "800-1200", "sections": 5}
            }

            spec = length_specs.get(length, length_specs["medium"])

            # Create prompt based on content type
            prompts = {
                "article": f"""Write a comprehensive article about "{topic}".

                Requirements:
                - Length: {spec['words']} words
                - Include {spec['sections']} main sections
                - Make it informative and engaging
                - Use clear headings and structure
                - Include specific examples and details
                - Professional tone
                - Write in plain text format with clear section headers

                Do not use markdown formatting. Use simple text formatting only.""",
                
                "report": f"""Write a professional report about "{topic}".

                Requirements:
                - Executive summary
                - Key findings and analysis
                - Data-driven insights
                - Recommendations
                - Length: {spec['words']} words
                - Formal business tone
                - Write in plain text format with clear sections

                Do not use markdown formatting. Use simple text formatting only.""",
                
                "summary": f"""Write a comprehensive summary about "{topic}".

                Requirements:
                - Cover key points and concepts
                - Highlight important facts
                - Easy to understand
                - Length: {spec['words']} words
                - Use bullet points where appropriate
                - Write in plain text format

                Do not use markdown formatting. Use simple text formatting only."""
            }

            prompt = prompts.get(type, 
                f"Write detailed content about '{topic}' in {spec['words']} words with {spec['sections']} main points. Use plain text formatting only.")

            # Generate content using LLM
            print("Calling LLM for content generation...")
            content = self.llm.generate(prompt, max_tokens=1200)
            print(f"Generated content length: {len(content)} characters")

            # Create safe filename
            safe_topic = re.sub(r'[^\w\s-]', '', str(topic).strip())[:30]
            safe_topic = safe_topic.replace(' ', '_').strip('_')
            if not safe_topic:
                safe_topic = "content"
                
            filename = f"{type}_{safe_topic}.txt"
            filepath = os.path.join(Config.OUTPUT_DIR, filename)

            print(f"Saving to: {filepath}")

            # Write file with proper encoding and error handling
            try:
                with open(filepath, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(f"{type.title()}: {topic}\n")
                    f.write("=" * 50 + "\n")
                    f.write(f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Length: {length}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(content)
                    
                print(f"Successfully wrote file: {filename}")
                
                # Verify file was created
                if not os.path.exists(filepath):
                    raise Exception("File was not created successfully")
                    
                file_size = os.path.getsize(filepath)
                print(f"File size: {file_size} bytes")
                
            except Exception as file_error:
                print(f"File writing error: {file_error}")
                raise Exception(f"Failed to write file: {file_error}")

            # Extract preview (first few lines)
            preview_lines = content.split('\n')[:5]
            preview = '\n'.join(preview_lines)

            return {
                "success": True,
                "message": f"Generated {length} {type} about '{topic}'",
                "filename": filename,
                "filepath": filepath,
                "topic": topic,
                "type": type,
                "length": length,
                "word_count_estimate": len(content.split()),
                "preview": preview + "..." if len(content.split('\n')) > 5 else preview
            }

        except Exception as e:
            print(f"Content generation error: {e}")
            return {
                "success": False,
                "error": f"Content generation failed: {str(e)}"
            }