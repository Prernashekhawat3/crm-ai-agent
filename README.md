# AI Customer Support Refund Agent 
A fully functional web application featuring an AI Customer Support Agent named **Sarah** who evaluates and processes or denies e-commerce refund requests. The application enforces a strict corporate refund policy using an agent loop powered by **Groq Llama 3** (via `llama-3.1-8b-instant`) and displays real-time telemetry/reasoning logs in an admin dashboard.

---

## System Architecture

This project is built using a clean, decoupled architecture:

```
                  ┌────────────────────────────────────────┐
                  │          Vite + React Frontend         │
                  │  (Sandbox Selector, Chat, Admin logs)  │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼ [HTTP REST API]
                  ┌────────────────────────────────────────┐
                  │         FastAPI Router & Controller    │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │            Refund Agent Loop           │
                  │      (Stateful orchestration loop)     │
                  └───────────────────┬────────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│   ILLMService    │         │  ICRMRepository  │         │ IPolicyValidator │
│  (Abstractions)  │         │  (Abstractions)  │         │  (Abstractions)  │
└────────┬─────────┘         └────────┬─────────┘         └────────┬─────────┘
         │                            │                            │
         ▼                            ▼                            ▼
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│   GroqLLMService │         │  CRMRepository   │         │ PolicyValidator  │
│  (Concrete Groq) │         │ (SQLAlchemy + DB)│         │(policy.txt rules)│
└──────────────────┘         └────────┬─────────┘         └──────────────────┘
                                      │
                                      ▼
                             ┌──────────────────┐
                             │  SQLite database │
                             │  (refund_agent)  │
                             └──────────────────┘
```

---

## Data Layer: The 15 Seeded Customers (Edge Cases)

The database seeds 15 specific customer accounts designed to test the limits of the corporate Refund Policy (`backend/data/policy.txt`):

1. **Alice Vance (`alice@example.com`)** (VIP): Eligible Refund. Purchased item 10 days ago (within 30-day window) and possesses original packaging.
2. **Bob Smith (`bob@example.com`)** (Standard): Out of Window. Bought 45 days ago. He will plead/argue, but the policy mandates a hard denial.
3. **Charlie Brown (`charlie@example.com`)** (Standard): Final Sale. Order contains a clearance item marked as strictly non-refundable.
4. **Diana Prince (`diana@example.com`)** (VIP): High Value. Refund request is for an $850 monitor. Exceeds the auto-approval threshold of $500, prompting escalation to a human admin.
5. **Ethan Hunt (`ethan@example.com`)** (Standard): Return Limit Abuse. Customer has already had 3 refunds processed in 2026. Auto-escalated to Risk Assessment.
6. **Fiona Gallagher (`fiona@example.com`)** (Standard): In Transit. Order status is "Shipped", meaning it cannot be refunded yet.
7. **Nancy Drew (`nancy@example.com`)** (Nancy): Processing. Order has not left the warehouse yet, meaning returns are ineligible.
8. **Oscar Martinez (`oscar@example.com`)** (Gold): Already Refunded. Order status is "Returned" and already has an approved refund on file.
9. **Laura Croft (`laura@example.com`)** (Gold): Mixed. Order contains one eligible item and one clearance (final sale) item.

---

## Setup & Running Guide

### 1. Requirements
* Python 3.13+
* Node.js v18+
* Docker (Optional, only needed if running PostgreSQL instead of SQLite)

### 2. Configuration
1. Open [backend/.env](file:///Users/noe/Documents/crm-ai-agent/backend/.env) and verify your **`GROQ_API_KEY`** is set correctly.
2. Choose your database:
   * **SQLite (Default)**: Keep `DATABASE_URL=sqlite:///./refund_agent.db` active in your `.env` file.
   * **PostgreSQL (Docker)**: Comment out the SQLite URL and uncomment:
     `DATABASE_URL=postgresql://postgres:postgrespassword@localhost:5432/refund_agent`

### 3. Install & Start
Launch your terminal in the root directory `/Users/noe/Documents/crm-ai-agent` and run:
```bash
# Install the launch script dependencies
npm install

# Start the DB (if using Docker), Backend API, and Frontend concurrently in one command
npm run dev
```

Open your browser and navigate to **`http://localhost:5173`** to interact with the agent.

---

## Developer Trace Logs (Reasoning)

The admin panel allows real-time tracing of the agent loop. A typical trace showcases:
1. **User Message**: Captures the exact input.
2. **Thought**: The internal chain of thought reasoning by the LLM.
3. **Tool Call**: The exact function requested (e.g. `get_customer_profile` with arguments).
4. **Tool Response**: The raw data output returned by the system database.
5. **Agent Response**: The final formulated message explaining the policy decision.
6. **Metrics**: Real-time evaluation of API latency, input/output tokens used, and the direct cost estimate (calculated based on standard Groq token rates).
