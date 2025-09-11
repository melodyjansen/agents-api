"""
LLM Client for interacting with the Groq API
"""

import requests
import json
from typing import Optional


class GroqLLM:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate(self, prompt: str, max_tokens: int = 300, model: str = "gemma2-9b-it") -> str:
        """
        Generate text using Groqs API
        """
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "top_p": 0.9,
            "stream": False
        }

        try:
            response = requests.post(
                self.base_url, 
                headers=self.headers, 
                json=data, 
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

        except requests.exceptions.RequestException as e:
            raise Exception(f"API Error: {str(e)}")
        except KeyError as e:
            raise Exception(f"Response parsing error: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")

    def is_available(self) -> bool:
        """Check if the LLM service is available"""
        try:
            test_response = self.generate("Hello", max_tokens=5)
            return bool(test_response.strip())
        except:
            return False