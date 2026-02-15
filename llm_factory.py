import os
from litellm import completion
import json
import logging
from typing import Optional, Dict, Any, Type
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class LLMFactory:
    def __init__(self, provider: str = "gemini", model_name: str = "gemini/gemini-1.5-pro-latest"):
        self.provider = provider
        self.model_name = model_name
        
        # Ensure API keys are present based on provider
        if provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
            logger.warning("GEMINI_API_KEY not found in environment variables.")
        elif provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY not found in environment variables.")
        elif provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
            logger.warning("ANTHROPIC_API_KEY not found in environment variables.")
            
    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generates text response from the LLM.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = completion(
                model=self.model_name,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM Generation Error: {e}")
            raise

    def generate_json(self, system_prompt: str, user_prompt: str, schema_class: Type[BaseModel]) -> BaseModel:
        """
        Generates a JSON response and parses it into a Pydantic model.
        """
        # Append JSON instruction to prompt if not implicit in the model capabilities
        # Use json.dumps to ensure the schema is formatted as a valid JSON string for the prompt
        
        # Pydantic v2 uses model_json_schema()
        schema_dump = json.dumps(schema_class.model_json_schema(), indent=2)
        json_instruction = f"\n\nRespond strictly in valid JSON format matching this schema:\n{schema_dump}"
        full_user_prompt = user_prompt + json_instruction
        
        messages = [
            {"role": "system", "content": system_prompt + " You must output valid JSON."},
            {"role": "user", "content": full_user_prompt}
        ]
        
        try:
            response = completion(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"} if any(x in self.model_name for x in ["gpt", "gemini", "ollama"]) else None
            )
            
            content = response.choices[0].message.content
            
            # Clean content if it has markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
                
            data = json.loads(content)
            return schema_class(**data)
            
        except Exception as e:
            logger.error(f"LLM JSON Generation Error: {e}")
            raise
