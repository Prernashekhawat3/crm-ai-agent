import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class StepLog(BaseModel):
    step_type: str  # "user_message", "thought", "tool_call", "tool_response", "agent_message", "error"
    content: Any
    timestamp: float
    latency: Optional[float] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost: Optional[float] = None

class SessionTrace(BaseModel):
    session_id: str
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    status: str = "Active"  # "Active", "Approved", "Denied", "Escalated"
    start_time: float
    end_time: Optional[float] = None
    steps: List[StepLog] = []
    total_latency: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost: float = 0.0

class ReasoningLogManager:
    """
    Stateful memory manager for agent execution traces.
    Acts as the telemetry engine for the admin dashboard.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ReasoningLogManager, cls).__new__(cls, *args, **kwargs)
            cls._instance.traces = {}
            cls._instance.chat_histories = {}
        return cls._instance

    def get_or_create_trace(self, session_id: str, email: str = None, name: str = None) -> SessionTrace:
        if session_id not in self.traces:
            self.traces[session_id] = SessionTrace(
                session_id=session_id,
                customer_email=email,
                customer_name=name,
                start_time=time.time()
            )
        else:
            if email and not self.traces[session_id].customer_email:
                self.traces[session_id].customer_email = email
            if name and not self.traces[session_id].customer_name:
                self.traces[session_id].customer_name = name
        return self.traces[session_id]

    def add_step(self, session_id: str, step_type: str, content: Any, latency: float = None, 
                 tokens_in: int = 0, tokens_out: int = 0, model: str = None) -> None:
        trace = self.get_or_create_trace(session_id)
        
        # Calculate cost based on Groq standard rates
        # Llama 3 70B: Input = $0.59 / M tokens, Output = $0.79 / M tokens
        cost_in = (tokens_in / 1_000_000.0) * 0.59
        cost_out = (tokens_out / 1_000_000.0) * 0.79
        step_cost = cost_in + cost_out

        step = StepLog(
            step_type=step_type,
            content=content,
            timestamp=time.time(),
            latency=latency,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=step_cost
        )
        trace.steps.append(step)
        
        # Update session aggregates
        trace.total_tokens_in += tokens_in
        trace.total_tokens_out += tokens_out
        trace.total_cost += step_cost
        if latency:
            trace.total_latency += latency

    def update_status(self, session_id: str, status: str) -> None:
        trace = self.get_or_create_trace(session_id)
        trace.status = status
        if status in ["Approved", "Denied", "Escalated"]:
            trace.end_time = time.time()
            trace.total_latency = trace.end_time - trace.start_time

    def get_all_traces(self) -> List[SessionTrace]:
        # Sort traces by start time descending
        return sorted(self.traces.values(), key=lambda t: t.start_time, reverse=True)

    def get_trace(self, session_id: str) -> Optional[SessionTrace]:
        return self.traces.get(session_id)

    def get_metrics(self) -> Dict[str, Any]:
        all_traces = list(self.traces.values())
        total_sessions = len(all_traces)
        approved = sum(1 for t in all_traces if t.status == "Approved")
        denied = sum(1 for t in all_traces if t.status == "Denied")
        escalated = sum(1 for t in all_traces if t.status == "Escalated")
        
        total_tokens = sum(t.total_tokens_in + t.total_tokens_out for t in all_traces)
        total_cost = sum(t.total_cost for t in all_traces)
        
        completed_latencies = [t.total_latency for t in all_traces if t.end_time is not None]
        avg_latency = sum(completed_latencies) / len(completed_latencies) if completed_latencies else 0.0

        return {
            "total_sessions": total_sessions,
            "approved_count": approved,
            "denied_count": denied,
            "escalated_count": escalated,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "avg_latency": avg_latency
        }

    def clear(self) -> None:
        self.traces.clear()
        self.chat_histories.clear()
