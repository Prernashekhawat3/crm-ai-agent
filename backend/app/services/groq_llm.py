import os
import time
from typing import List, Dict, Any, Optional
from groq import Groq
from ..core.interfaces import ILLMService
from ..core.logger import ReasoningLogManager

class GroqLLMService(ILLMService):
    """
    Groq API provider implementation of ILLMService.
    Integrates with Groq SDK using Llama models for high-performance tool calling.
    """
    def __init__(self, api_key: Optional[str] = None, model: str = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set.")
        
        self.client = Groq(api_key=self.api_key)
        # Default fallback to llama-3.1-8b-instant for high-speed, high rate limit tool execution.
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.logger = ReasoningLogManager()

    def get_provider_name(self) -> str:
        return f"Groq ({self.model})"

    def call_with_tools(
        self,
        system_instruction: str,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Executes a call to Groq with system instructions, messages, and function tools.
        """
        # Build prompt payload
        full_messages = [{"role": "system", "content": system_instruction}] + messages
        
        # Format tools if provided
        kwargs = {}
        if tools:
            # Groq expects tools formatted in OpenAI standard: list of {"type": "function", "function": {...}}
            formatted_tools = []
            for t in tools:
                if "type" not in t:
                    formatted_tools.append({
                        "type": "function",
                        "function": t
                    })
                else:
                    formatted_tools.append(t)
            kwargs["tools"] = formatted_tools
            kwargs["tool_choice"] = "auto"

        start_time = time.time()
        
        try:
            # Execute chat completion
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=0.0,  # low temperature for stable agentic behavior
                **kwargs
            )
            
            latency = time.time() - start_time
            
            # Extract content and tool calls
            choice = response.choices[0]
            content = choice.message.content
            tool_calls_raw = getattr(choice.message, "tool_calls", None)
            
            # Parse tool calls to clean dicts
            tool_calls = []
            if tool_calls_raw:
                for tc in tool_calls_raw:
                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments  # JSON string
                    })
            
            # Extract token usage
            usage = response.usage
            tokens_in = usage.prompt_tokens if usage else 0
            tokens_out = usage.completion_tokens if usage else 0
            
            # Log the thought if agent returned text alongside or instead of tool calling
            # If the model uses tool calling, it might output a 'thought' reasoning in content or have a system rule
            if content:
                # Add a thought or reply log step
                self.logger.add_step(
                    session_id=session_id,
                    step_type="thought" if tool_calls else "agent_message",
                    content=content,
                    latency=latency,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    model=self.model
                )
            elif tool_calls:
                # Log tool generation step without content text
                self.logger.add_step(
                    session_id=session_id,
                    step_type="thought",
                    content=f"Agent generated {len(tool_calls)} tool calls: {[tc['name'] for tc in tool_calls]}",
                    latency=latency,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    model=self.model
                )

            return {
                "content": content,
                "tool_calls": tool_calls,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "latency": latency
            }

        except Exception as e:
            latency = time.time() - start_time
            self.logger.add_step(
                session_id=session_id,
                step_type="error",
                content=f"Groq API Error: {str(e)}",
                latency=latency
            )
            raise e
