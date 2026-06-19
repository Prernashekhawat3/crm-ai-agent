import os
import sys
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Ensure the backend directory is in the system path for Vercel imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Load environment variables
load_dotenv()

from app.database.database import init_db, get_db, seed_db, reset_db, SessionLocal
from app.database.schema import Customer, Order, Refund
from app.database.crm_repository import CRMRepository
from app.core.policy_validator import PolicyValidator
from app.services.groq_llm import GroqLLMService
from app.core.agent import RefundAgent
from app.core.logger import ReasoningLogManager

# Initialize Database on Startup
init_db()
db = SessionLocal()
try:
    seed_db(db)
finally:
    db.close()

app = FastAPI(
    title="AI Customer Support Agent API",
    description="Backend API hosting an agent loop for e-commerce refund validation.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared Telemetry Manager (Singleton)
log_manager = ReasoningLogManager()

# Request/Response DTOs
class ChatRequest(BaseModel):
    session_id: str
    messages: List[Dict[str, str]]

class ChatResponse(BaseModel):
    session_id: str
    response: str
    trace: Dict[str, Any]

# Endpoints
@app.post("/api/chat", response_model=ChatResponse)
def chat_with_agent(req: ChatRequest, db=Depends(get_db)):
    """
    POST route to chat with the AI Support Agent. 
    Runs the agent loop, executes tools, and captures trace outputs.
    """
    if not req.session_id:
        raise HTTPException(status_code=400, detail="session_id is required.")
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty.")

    try:
        # Resolve dependencies
        repo = CRMRepository(db)
        policy = PolicyValidator()
        llm = GroqLLMService()
        agent = RefundAgent(llm_service=llm, repository=repo, policy_validator=policy)
        
        # Execute the agent loop
        response_text = agent.run(req.session_id, req.messages)
        
        # Fetch the completed session trace
        trace = log_manager.get_trace(req.session_id)
        trace_data = trace.model_dump() if trace else {}
        
        # Record final assistant response in trace log
        log_manager.add_step(req.session_id, "agent_message", response_text)
        
        # Fetch trace again to ensure final message is included
        trace = log_manager.get_trace(req.session_id)
        trace_data = trace.model_dump() if trace else {}

        return ChatResponse(
            session_id=req.session_id,
            response=response_text,
            trace=trace_data
        )

    except Exception as e:
        # Register failure in the trace logs
        log_manager.add_step(req.session_id, "error", f"System Exception: {str(e)}")
        log_manager.update_status(req.session_id, "Escalated")
        
        raise HTTPException(status_code=500, detail=f"Agent loop error: {str(e)}")

@app.get("/api/admin/logs")
def get_admin_logs():
    """
    Returns list of all session execution traces.
    """
    return [t.model_dump() for t in log_manager.get_all_traces()]

@app.get("/api/admin/logs/{session_id}")
def get_admin_log_by_id(session_id: str):
    """
    Returns specific session execution trace.
    """
    trace = log_manager.get_trace(session_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace with session_id {session_id} not found.")
    return trace.model_dump()

@app.get("/api/admin/metrics")
def get_admin_metrics():
    """
    Returns aggregate performance and cost metrics.
    """
    return log_manager.get_metrics()

@app.get("/api/crm/customers")
def list_crm_customers(db=Depends(get_db)):
    """
    Helper route listing seeded customer profiles.
    Allows easy selection in the frontend sandbox.
    """
    customers = db.query(Customer).all()
    results = []
    for c in customers:
        # Calculate number of orders
        order_count = len(c.orders)
        # Find active orders
        orders = [
            {
                "id": o.id,
                "purchase_date": o.purchase_date,
                "status": o.status,
                "total_amount": o.total_amount,
                "items": [{"id": i.id, "name": i.product_name, "price": i.price, "final_sale": i.is_final_sale} for i in o.items]
            } for o in c.orders
        ]
        
        # Count approved refunds in 2026
        refund_count = (
            db.query(Refund)
            .join(Order)
            .filter(Order.customer_id == c.id)
            .filter(Refund.status == "Approved")
            .count()
        )
        
        results.append({
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "tier": c.tier,
            "refund_count_2026": refund_count,
            "order_count": order_count,
            "orders": orders
        })
    return results

@app.post("/api/crm/reset")
def reset_crm_database():
    """
    POST route to reset and reseed database.
    Clear trace logs to restart demo cleanly.
    """
    try:
        reset_db()
        log_manager.clear()
        return {"success": True, "message": "Database and execution traces have been reset successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset database: {str(e)}")
