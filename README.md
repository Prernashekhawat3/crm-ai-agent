# AI Customer Support Refund Agent - Clean Architecture

A fully functional, senior-level web application featuring an AI Customer Support Agent named **Sarah** who evaluates and processes or denies e-commerce refund requests. The application enforces a strict corporate refund policy using an agent loop powered by **Groq Llama 3** (via `llama-3.3-70b-versatile` or OpenAI compatibility) and displays real-time telemetry/reasoning logs in an admin dashboard.

---

## System Architecture

This project is built using a clean, decoupled architecture enforcing **SOLID principles**:

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

### SOLID Principles Applied
1. **Single Responsibility Principle (SRP)**:
   * `CRMRepository` handles only database read/write actions.
   * `PolicyValidator` handles only rule evaluations from the corporate policy text.
   * `GroqLLMService` handles only connection, token counting, and API calling.
   * `ReasoningLogManager` handles only stateful execution traces.
2. **Open/Closed Principle (OCP)**: 
   * The agent loop (`RefundAgent`) does not contain direct database queries or API provider calls. To add a new LLM provider (e.g. Anthropic, Gemini), simply implement the `ILLMService` interface. To switch the database engine (e.g. SQLite to PostgreSQL), replace the `ICRMRepository` implementation.
3. **Liskov Substitution Principle (LSP)**:
   * Interface structures (`interfaces.py`) are strictly typed to guarantee that any subclass (like `GroqLLMService` or `OpenAILLMService`) can be substituted cleanly without breaking the orchestrator.
4. **Interface Segregation Principle (ISP)**:
   * Interfaces are broken down into narrow, domain-specific modules (`ILLMService`, `ICRMRepository`, `IPolicyValidator`) so consumers only depend on the methods they actively use.
5. **Dependency Inversion Principle (DIP)**:
   * The core agent orchestration loop depends only on abstract interfaces rather than concrete libraries or schemas. Dependencies are injected via the constructor of `RefundAgent`.

---

## Data Layer: The 15 Seeded Customers (Edge Cases)

The SQLite database seeds 15 specific customer accounts designed to test the limits of the corporate Refund Policy (`backend/data/policy.txt`):

1. **Alice Vance (`alice@example.com`)** (VIP): Eligible Refund. Purchased item 10 days ago (within 30-day window) and possesses original packaging.
2. **Bob Smith (`bob@example.com`)** (Standard): Out of Window. Bought 45 days ago. He will plead/argue, but the policy mandates a hard denial.
3. **Charlie Brown (`charlie@example.com`)** (Standard): Final Sale. Order contains a clearance item marked as strictly non-refundable.
4. **Diana Prince (`diana@example.com`)** (VIP): High Value. Refund request is for an $850 monitor. Exceeds the auto-approval threshold of $500, prompting escalation to a human admin.
5. **Ethan Hunt (`ethan@example.com`)** (Standard): Return Limit Abuse. Customer has already had 3 refunds processed in 2026. Auto-escalated to Risk Assessment.
6. **Fiona Gallagher (`fiona@example.com`)** (Standard): In Transit. Order status is "Shipped", meaning it cannot be refunded yet.
7. **Nancy Drew (`nancy@example.com`)** (Standard): Processing. Order has not left the warehouse yet, meaning returns are ineligible.
8. **Oscar Martinez (`oscar@example.com`)** (Gold): Already Refunded. Order status is "Returned" and already has an approved refund on file.
9. **Laura Croft (`laura@example.com`)** (Gold): Mixed. Order contains one eligible item and one clearance (final sale) item.

---

## Setup & Running Guide

### 1. Requirements
* Python 3.13+
* Node.js v18+

### 2. Backend Setup
1. Open a terminal and navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment (if not already done):
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Verify the `.env` file has the correct `GROQ_API_KEY`.
5. Start the FastAPI server:
   ```bash
   PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload --port 8000
   ```

### 3. Frontend Setup
1. Open a second terminal and navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Start the Vite React development server:
   ```bash
   npm run dev
   ```
4. Open your browser and navigate to the local URL (usually `http://localhost:5173`).

---

## Developer Trace Logs (Reasoning)

The admin panel allows real-time tracing of the agent loop. A typical trace showcases:
1. **User Message**: Captures the exact input.
2. **Thought**: The internal chain of thought reasoning by the LLM.
3. **Tool Call**: The exact function requested (e.g. `get_customer_profile` with arguments).
4. **Tool Response**: The raw data output returned by the system database.
5. **Agent Response**: The final formulated message explaining the policy decision.
6. **Metrics**: Real-time evaluation of API latency, input/output tokens used, and the direct cost estimate (calculated based on standard Groq token rates).
