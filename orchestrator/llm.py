import json
import os
from llama_cpp import Llama
from tools import TOOL_DEFINITIONS

MODEL_PATH = os.environ.get("LLM_MODEL_PATH", "/app/models/qwen2.5-1.5b-instruct-q4_k_m.gguf")

_llm = None


def get_llm() -> Llama:
    global _llm
    if _llm is None:
        _llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=4096,
            n_threads=4,
            chat_format="chatml-function-calling",
            verbose=False,
        )
    return _llm


def chat(messages: list) -> dict:
    """Devuelve {'type': 'text', 'content': str} o {'type': 'tool_call', 'name': str, 'args': dict}."""
    llm = get_llm()
    result = llm.create_chat_completion(
        messages=messages,
        tools=[{"type": "function", "function": t} for t in TOOL_DEFINITIONS],
        tool_choice="auto",
        temperature=0.3,
        max_tokens=200,
    )
    choice = result["choices"][0]["message"]

    if choice.get("tool_calls"):
        call = choice["tool_calls"][0]
        return {
            "type": "tool_call",
            "name": call["function"]["name"],
            "args": json.loads(call["function"]["arguments"]),
        }

    return {"type": "text", "content": choice.get("content", "").strip()}
