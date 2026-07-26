"""
Local Open-Source LLM Client Module.
Uses llama-cpp-python to perform completely local inference with Qwen2.5-0.5B-Instruct GGUF Q3_K_S.
"""

import os
import sys
import time
import json
import site
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Ensure user site-packages is in sys.path for llama_cpp import
user_site = site.getusersitepackages()
if user_site not in sys.path:
    sys.path.insert(0, user_site)

try:
    import llama_cpp
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "Qwen2.5-0.5B-Instruct-Q3_K_S.gguf"

class LocalQwenLLMClient:
    """
    Local LLM client loading Qwen2.5-0.5B-Instruct-Q3_K_S GGUF via llama-cpp-python.
    """

    def __init__(self, model_path: Optional[str] = None, n_ctx: int = 2048, n_threads: int = 4):
        self.model_path = Path(model_path) if model_path else MODEL_PATH
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.llm = None

    def load_model(self) -> Tuple[bool, str]:
        """Loads GGUF model into memory using llama-cpp-python."""
        if not LLAMA_CPP_AVAILABLE:
            return False, "llama-cpp-python is not installed."

        if not self.model_path.is_file():
            return False, f"Model file not found at '{self.model_path}'."

        try:
            t0 = time.time()
            self.llm = llama_cpp.Llama(
                model_path=str(self.model_path),
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=False
            )
            load_time = time.time() - t0
            return True, f"Loaded model successfully in {load_time:.2f}s."
        except Exception as e:
            return False, f"Failed to load GGUF model: {e}"

    def generate_decision(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 256
    ) -> Tuple[bool, Dict[str, Any], float, str]:
        """
        Generates structured JSON decision using local Qwen model.
        Returns (success: bool, raw_json_dict: Dict, latency_seconds: float, error_message: str).
        """
        if self.llm is None:
            loaded, msg = self.load_model()
            if not loaded:
                return False, {}, 0.0, msg

        t0 = time.time()
        try:
            # Format prompt using Qwen2.5 chat template
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = self.llm.create_chat_completion(
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens
            )

            latency = time.time() - t0
            content = response["choices"][0]["message"]["content"].strip()

            # Clean markdown formatting if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            raw_dict = json.loads(content)
            return True, raw_dict, latency, ""
        except json.JSONDecodeError as e:
            latency = time.time() - t0
            return False, {}, latency, f"JSON Decode Error: {e}"
        except Exception as e:
            latency = time.time() - t0
            return False, {}, latency, f"LLM Generation Error: {e}"
