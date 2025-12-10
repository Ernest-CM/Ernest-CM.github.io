from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import os
import json


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """Generate text from the LLM"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package is required for OpenAI provider")
    
    def generate(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """Generate text using OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful customer support assistant that creates structured action plans."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content


class LocalLLMProvider(LLMProvider):
    """Local LLM provider (placeholder for local models like llama.cpp, etc.)"""
    
    def __init__(self, model_path: str = None, endpoint: str = None):
        self.model_path = model_path
        self.endpoint = endpoint or os.getenv("LOCAL_LLM_ENDPOINT", "http://localhost:8080")
    
    def generate(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """Generate text using local LLM"""
        # This is a placeholder implementation
        # In production, this would call a local LLM service
        import httpx
        
        try:
            response = httpx.post(
                f"{self.endpoint}/v1/completions",
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()["choices"][0]["text"]
        except Exception as e:
            raise RuntimeError(f"Local LLM generation failed: {e}")


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing and development"""
    
    def generate(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """Generate a mock response based on the prompt"""
        # Parse the prompt to understand the ticket
        prompt_lower = prompt.lower()
        
        # Check for CSV/upload issues first (more specific)
        if ("csv" in prompt_lower and "upload" in prompt_lower) or ("crashes" in prompt_lower and "upload" in prompt_lower):
            return json.dumps([
                {
                    "step": 1,
                    "tool": "fetch_logs",
                    "args": {"user_id": "u123", "last_hours": 24}
                },
                {
                    "step": 2,
                    "tool": "check_known_issues",
                    "args": {"query": "CSV upload v2.1"}
                },
                {
                    "step": 3,
                    "tool": "run_diagnostic",
                    "args": {"session_id": "sess-abc"}
                },
                {
                    "step": 4,
                    "tool": "reply_ticket",
                    "args": {
                        "ticket_id": "t100",
                        "message": "Found bug, please update to v2.1.1. If you want, we can apply a temporary patch (requires approval)."
                    }
                }
            ])
        # Check for password reset (look for "password reset request" in subject/body area)
        elif ("subject: password reset" in prompt_lower) or ("body: i forgot my password" in prompt_lower):
            return json.dumps([
                {
                    "step": 1,
                    "tool": "get_account_info",
                    "args": {"user_id": "u456"}
                },
                {
                    "step": 2,
                    "tool": "reset_password",
                    "args": {"user_id": "u456"}
                },
                {
                    "step": 3,
                    "tool": "reply_ticket",
                    "args": {
                        "ticket_id": "t200",
                        "message": "Password reset initiated. Check your email for reset link."
                    }
                }
            ])
        else:
            return json.dumps([
                {
                    "step": 1,
                    "tool": "get_account_info",
                    "args": {"user_id": "u123"}
                },
                {
                    "step": 2,
                    "tool": "kb_search",
                    "args": {"query": "common issues", "top_k": 3}
                },
                {
                    "step": 3,
                    "tool": "reply_ticket",
                    "args": {
                        "ticket_id": "t100",
                        "message": "Thank you for your inquiry. We are investigating the issue."
                    }
                }
            ])


def get_llm_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """Factory function to get the appropriate LLM provider"""
    provider_name = provider_name or os.getenv("LLM_PROVIDER", "mock")
    
    if provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "local":
        return LocalLLMProvider()
    elif provider_name == "mock":
        return MockLLMProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
