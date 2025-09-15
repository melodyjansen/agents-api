"""
Content Writer Agent for generating text content and outputting txt file (docx if markdown detected)
"""
import re
import os
from typing import Dict
import pandas as pd
import pypandoc

from GroqLLM import GroqLLM
from config import Config


class ContentWriterAgent:
    def __init__(self, llm: GroqLLM):
        self.llm = llm

    def write_content(self, topic: str = "General Topic", type: str = "article", length: str = "medium") -> Dict:
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
                
            # Decide file extension
            if self._looks_like_markdown(content):
                ext = ".docx"
            else:
                ext = ".txt"

            filename = f"{safe_topic}{ext}"
            filepath = os.path.join(Config.OUTPUT_DIR, filename)

            print(f"Saving to: {filepath}")

            if ext == ".docx":
                self._save_as_docx(content, filepath)
            else:
                with open(filepath, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(f"{type.title()}: on {topic}\n")
                    f.write("=" * 50 + "\n")
                    f.write(f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Length: {length}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(content)

            file_size = os.path.getsize(filepath)
            print(f"File size: {file_size} bytes")

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
        

    def write_content_from_files(self, processed_content: str, approach: str = "rewrite", content_type: str = "article", length: str = "medium", source_files: list = None) -> Dict:
        """
        Rewrite processed content (e.g. summaries from FileProcessor) into a more natural 
        article, report, or summary format.
        """
        try:
            topic = "Content from uploaded files"

            print(f"Rewriting processed content into {content_type} ({length} length)...")

            os.makedirs(Config.OUTPUT_DIR, exist_ok=True)

            # Define length parameters (reuse from before)
            length_specs = {
                "short": {"words": "300-500", "sections": 3},
                "medium": {"words": "500-800", "sections": 4},
                "long": {"words": "800-1200", "sections": 5}
            }
            spec = length_specs.get(length, length_specs["medium"])

            # Prompts to guide rewriting
            prompts = {
                "article": f"""Rewrite the following summary into a comprehensive article.

                Requirements:
                - Length: {spec['words']} words
                - Organize into {spec['sections']} main sections with clear headings (though no markdown)
                - Make it informative and engaging
                - Use examples and details when possible
                - Professional tone

                Formatting:
                - For bullet points: use "•" or "-" followed by a space
                - Do not use #, ##, ###, *, or ```
                - Do not use markdown formatting
                - Use simple text formatting only!

                Source summary:
                {processed_content}
                """,

                "report": f"""Rewrite the following summary into a professional report.

                Requirements:
                - Executive summary
                - Key findings and analysis
                - Data-driven insights where applicable
                - Recommendations
                - Length: {spec['words']} words
                - Formal business tone

                Formatting:
                - For bullet points: use "•" or "-" followed by a space
                - Do not use #, ##, ###, *, or ```
                - Do not use markdown formatting
                - Use simple text formatting only!

                Source summary:
                {processed_content}
                """,

                "summary": f"""Rewrite the following into a clear, comprehensive summary.

                Requirements:
                - Highlight key points and important facts
                - Easy to understand
                - Use bullet points where appropriate
                - Length: {spec['words']} words

                Formatting:
                - For bullet points: use "•" or "-" followed by a space
                - Do not use #, ##, ###, *, or ```
                - Do not use markdown formatting. 
                - Use simple text formatting only!

                Source summary:
                {processed_content} 
                """
            }

            prompt = prompts.get(content_type, f"Rewrite the following text into {spec['words']} words:\n{processed_content}")

            # Generate rewritten content
            print("Calling LLM for content rewriting...")
            content = self.llm.generate(prompt, max_tokens=1200)
            print(f"Rewritten content length: {len(content)} characters")

            # Decide file extension
            if self._looks_like_markdown(content):
                ext = ".docx"
            else:
                ext = ".txt"

            filename = f"{content_type}_from_files{ext}"
            filepath = os.path.join(Config.OUTPUT_DIR, filename)

            print(f"Saving to: {filepath}")

            if ext == ".docx":
                self._save_as_docx(content, filepath)
            else:
                with open(filepath, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(f"{content_type.title()} from Files\n")
                    f.write("=" * 50 + "\n")
                    f.write(f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Length: {length}\n")
                    if source_files:
                        f.write(f"Source files: {', '.join(source_files)}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(content)

            file_size = os.path.getsize(filepath)
            print(f"File size: {file_size} bytes")

            preview_lines = content.split('\n')[:5]
            preview = '\n'.join(preview_lines)

            return {
                "success": True,
                "message": f"Rewritten {length} {content_type} from files",
                "filename": filename,
                "filepath": filepath,
                "type": content_type,
                "length": length,
                "word_count_estimate": len(content.split()),
                "preview": preview + "..." if len(content.split('\n')) > 5 else preview,
                "sources": source_files or []
            }

        except Exception as e:
            print(f"Content rewriting error: {e}")
            return {
                "success": False,
                "error": f"Content rewriting failed: {str(e)}"
            }
        
    def _looks_like_markdown(self, text: str) -> bool:
        """Quick heuristic to detect markdown-style formatting"""
        patterns = [
            r"^#{1,6}\s",          # headings
            r"\*\*.*\*\*",         # bold
            r"\*[^*]+\*",          # italic
            r"`[^`]+`",            # inline code
            r"```[\s\S]*?```",     # code block
            r"^- ",                # bullet list
        ]
        return any(re.search(p, text, flags=re.MULTILINE) for p in patterns)

    def _save_as_docx(self, markdown_text: str, filepath: str):
        """Convert markdown text into a DOCX file using pypandoc"""
        pypandoc.convert_text(
            markdown_text,
            'docx',
            format='md',
            outputfile=filepath,
            extra_args=['--standalone']
        )
