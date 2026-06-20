import React, { useState, useEffect, useRef } from "react";
import {
  MessageSquare,
  ShieldCheck,
  User,
  RefreshCw,
  Send,
  FileText,
  HelpCircle,
  Terminal,
  Clock,
  Coins,
  TrendingUp,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronRight,
  Database
} from "lucide-react";

const API_BASE = import.meta.env.DEV
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : "";

// Quick label mapping to help user choose test cases
const SCENARIO_LABELS = {
  "alice@example.com": "Eligible Refund (VIP)",
  "bob@example.com": "Out of Window (>45 days)",
  "charlie@example.com": "Final Sale Item",
  "diana@example.com": "High Value (>$500)",
  "ethan@example.com": "Return Limit Exceeded",
  "fiona@example.com": "Status: Shipped Only",
  "nancy@example.com": "Status: Processing",
  "oscar@example.com": "Already Refunded",
  "laura@example.com": "Mixed (Normal + Final Sale)",
  "mike@example.com": "Close to Limit (2 past)"
};

function App() {
  const [customers, setCustomers] = useState([]);
  const [activeCustomer, setActiveCustomer] = useState(null);
  const [messages, setMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [isLoadingAgent, setIsLoadingAgent] = useState(false);

  // Admin Telemetry States
  const [adminSessions, setAdminSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [metrics, setMetrics] = useState({
    total_sessions: 0,
    approved_count: 0,
    denied_count: 0,
    escalated_count: 0,
    total_tokens: 0,
    total_cost: 0.0,
    avg_latency: 0.0
  });

  const [activeTab, setActiveTab] = useState("logs"); // "logs" | "policy"
  const chatEndRef = useRef(null);

  // Initial Data Fetch
  useEffect(() => {
    fetchCRMData();
    fetchAdminTelemetry();
  }, []);

  // Scroll to bottom of chat when messages change
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoadingAgent]);

  // Poll telemetry in real-time while agent is reasoning
  useEffect(() => {
    let intervalId = null;
    if (isLoadingAgent) {
      // Immediate fetch when starting
      fetchAdminTelemetry();
      intervalId = setInterval(() => {
        fetchAdminTelemetry();
      }, 500);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isLoadingAgent]);

  const fetchCRMData = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/crm/customers`);
      const data = await res.json();
      setCustomers(data);
      if (data.length > 0 && !activeCustomer) {
        selectCustomer(data[0]);
      }
    } catch (err) {
      console.error("Error fetching CRM customers:", err);
    }
  };

  const fetchAdminTelemetry = async () => {
    try {
      const resLogs = await fetch(`${API_BASE}/api/admin/logs`);
      const dataLogs = await resLogs.json();
      setAdminSessions(dataLogs);

      const resMetrics = await fetch(`${API_BASE}/api/admin/metrics`);
      const dataMetrics = await resMetrics.json();
      setMetrics(dataMetrics);

      // Auto-select the active session if it exists in the logs
      const activeTrace = dataLogs.find(s => s.session_id === sessionId);
      if (activeTrace) {
        setSelectedSession(activeTrace);
      } else if (sessionId) {
        // If there is an active session but no trace is recorded yet, do not show fallback logs
        setSelectedSession(null);
      } else if (dataLogs.length > 0 && !selectedSession) {
        setSelectedSession(dataLogs[0]);
      } else if (selectedSession) {
        const updated = dataLogs.find(s => s.session_id === selectedSession.session_id);
        if (updated) setSelectedSession(updated);
      }
    } catch (err) {
      console.error("Error fetching telemetry:", err);
    }
  };

  const selectCustomer = (customer) => {
    setActiveCustomer(customer);
    const newSessionId = `session_${customer.id}_${Date.now().toString().slice(-4)}`;
    setSessionId(newSessionId);
    setSelectedSession(null); // Clear previous trace logs when customer changes
    setMessages([
      {
        role: "assistant",
        content: `Hi, I am Sarah from E-Commerce Corp Customer Service. How can I help you today?`
      }
    ]);
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || isLoadingAgent) return;

    const userMsg = chatInput.trim();
    setChatInput("");

    // Add user message locally
    const newMessages = [...messages, { role: "user", content: userMsg }];
    setMessages(newMessages);
    setIsLoadingAgent(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          messages: newMessages
        })
      });

      const data = await res.json();
      if (res.ok) {
        setMessages([...newMessages, { role: "assistant", content: data.response }]);
      } else {
        setMessages([...newMessages, { role: "assistant", content: `Error: ${data.detail}` }]);
      }
    } catch (err) {
      setMessages([...newMessages, { role: "assistant", content: "Connection to the support server failed." }]);
    } finally {
      setIsLoadingAgent(false);
      // Fetch latest logs to refresh dashboard
      await fetchAdminTelemetry();
    }
  };

  const handleResetDatabase = async () => {
    if (!window.confirm("Are you sure you want to reset the CRM database and trace logs?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/crm/reset`, { method: "POST" });
      const data = await res.json();
      alert(data.message);

      // Clear local states
      setActiveCustomer(null);
      setSelectedSession(null);
      setMessages([]);

      await fetchCRMData();
      await fetchAdminTelemetry();
    } catch (err) {
      console.error("Error resetting DB:", err);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "Approved": return <CheckCircle className="status-Approved" style={{ width: 14, height: 14 }} />;
      case "Denied": return <XCircle className="status-Denied" style={{ width: 14, height: 14 }} />;
      case "Escalated": return <AlertTriangle className="status-Escalated" style={{ width: 14, height: 14 }} />;
      default: return <Clock className="status-Active" style={{ width: 14, height: 14 }} />;
    }
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div className="app-container">
      {/* HEADER */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo">
            <ShieldCheck />
          </div>
          <div className="brand-title">
            <h1>E-Commerce Refund Policy Agent</h1>
            <div className="brand-subtitle">AI Customer Support Refund Agent</div>
          </div>
        </div>
        <div className="header-actions">
          <button className="btn btn-secondary btn-sm" onClick={handleResetDatabase}>
            <Database style={{ width: 14, height: 14 }} />
            Reset Database & Logs
          </button>
        </div>
      </header>

      {/* DASHBOARD GRID */}
      <div className="dashboard-grid">

        {/* PANEL 1: CUSTOMER LIST SIDEBAR */}
        <section className="panel">
          <div className="panel-header">
            <h2 className="panel-title">
              <User />
              Sandbox Customers
            </h2>
            <span className="badge" style={{ fontSize: "0.65rem", background: "rgba(255,255,255,0.05)", padding: "0.2rem 0.5rem", borderRadius: "10px" }}>
              {customers.length} Accounts
            </span>
          </div>
          <div className="panel-content" style={{ gap: "0.75rem" }}>
            <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>
              Select a synthetic customer profile below to load their purchase details and simulate their chat session.
            </p>
            <div className="customer-list">
              {customers.map((c) => {
                const label = SCENARIO_LABELS[c.email] || "Normal Profile";
                const isActive = activeCustomer && activeCustomer.id === c.id;
                return (
                  <div
                    key={c.id}
                    className={`customer-card ${isActive ? "active" : ""}`}
                    onClick={() => selectCustomer(c)}
                  >
                    <div className="customer-header">
                      <span className="customer-name">{c.name}</span>
                      <span className={`tier-badge tier-${c.tier}`}>{c.tier}</span>
                    </div>
                    <div className="customer-email">{c.email}</div>

                    {/* Scenario badge */}
                    <div style={{
                      fontSize: "0.65rem",
                      color: label.includes("Eligible") ? "var(--success)" : label.includes("Status") ? "var(--info)" : "var(--warning)",
                      fontWeight: "600",
                      marginTop: "0.25rem",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.25rem"
                    }}>
                      <ChevronRight style={{ width: 10, height: 10 }} />
                      {label}
                    </div>

                    <div className="customer-stats">
                      <span>Orders: {c.order_count}</span>
                      <span>2026 Refunds: {c.refund_count_2026}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* PANEL 2: CUSTOMER CHAT SIMULATOR */}
        <section className="panel" style={{ flex: 1.2 }}>
          <div className="panel-header" style={{ background: "rgba(139, 92, 246, 0.03)" }}>
            <h2 className="panel-title">
              <MessageSquare />
              Sarah Support Agent Simulator
            </h2>
            {activeCustomer && (
              <span className="trace-status-badge status-Active" style={{ fontSize: "0.65rem" }}>
                Session: {sessionId.toUpperCase()}
              </span>
            )}
          </div>

          <div className="panel-content">
            {activeCustomer ? (
              <>
                {/* Customer context header widget */}
                <div style={{
                  background: "rgba(30, 41, 59, 0.3)",
                  border: "1px solid var(--border-color)",
                  borderRadius: "var(--radius-md)",
                  padding: "0.75rem",
                  marginBottom: "1rem",
                  fontSize: "0.75rem"
                }}>
                  <div style={{ fontWeight: "600", color: "#fff", marginBottom: "0.25rem" }}>Customer Context Loaded</div>
                  <div style={{ color: "var(--text-secondary)" }}>
                    <strong>Name:</strong> {activeCustomer.name} | <strong>Email:</strong> {activeCustomer.email} | <strong>Session ID:</strong> {sessionId}
                  </div>
                  <div style={{ marginTop: "0.5rem", borderTop: "1px solid rgba(255,255,255,0.05)", paddingTop: "0.5rem" }}>
                    <div style={{ fontWeight: "600", color: "#fff", marginBottom: "0.25rem" }}>Purchase History:</div>
                    <ul style={{ paddingLeft: "1rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                      {activeCustomer.orders.map(o => (
                        <li key={o.id}>
                          Order #{o.id} ({o.purchase_date}) - <strong>{o.status}</strong> | Total: ${o.total_amount.toFixed(2)}
                          <ul style={{ paddingLeft: "1rem", color: "var(--text-muted)", listStyleType: "circle" }}>
                            {o.items.map(item => (
                              <li key={item.id}>
                                {item.name} - ${item.price.toFixed(2)} {item.final_sale && <span style={{ color: "var(--danger)", fontWeight: "600" }}>(Final Sale)</span>}
                              </li>
                            ))}
                          </ul>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Hint helper */}
                  <div style={{
                    marginTop: "0.5rem",
                    padding: "0.4rem",
                    background: "rgba(139, 92, 246, 0.08)",
                    borderRadius: "4px",
                    borderLeft: "2px solid var(--primary)",
                    color: "var(--text-primary)"
                  }}>
                    💡 <strong>Quick Start:</strong> Tell Sarah: <em>"Hi, I am {activeCustomer.name}. I would like to request a refund for order #{activeCustomer.orders[0]?.id}."</em>
                  </div>
                </div>

                {/* Messages Body */}
                <div className="chat-messages">
                  {messages.map((m, i) => (
                    <div key={i} className={`message-bubble message-${m.role}`}>
                      {m.content}
                    </div>
                  ))}
                  {isLoadingAgent && (
                    <div className="typing-indicator">
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                {/* Send Input */}
                <form className="chat-input-area" onSubmit={handleSendMessage}>
                  <input
                    type="text"
                    className="chat-input"
                    placeholder="Type a message to pleading support agent Sarah..."
                    value={chatInput}
                    disabled={isLoadingAgent}
                    onChange={(e) => setChatInput(e.target.value)}
                  />
                  <button type="submit" className="btn" disabled={isLoadingAgent || !chatInput.trim()}>
                    <Send style={{ width: 14, height: 14 }} />
                  </button>
                </form>
              </>
            ) : (
              <div className="chat-welcome">
                <MessageSquare />
                <h3>No Sandbox Session</h3>
                <p>Select a customer profile from the left sidebar to initialize the AI Support Agent conversation simulator.</p>
              </div>
            )}
          </div>
        </section>

        {/* PANEL 3: ADMIN INSTRUMENTATION & LOGS */}
        <section className="panel" style={{ flex: 1.3 }}>
          <div className="panel-header">
            <h2 className="panel-title">
              <Terminal />
              Agent Trace Telemetry
            </h2>
            <div className="tab-nav">
              <button
                className={`tab-btn ${activeTab === "logs" ? "active" : ""}`}
                onClick={() => setActiveTab("logs")}
              >
                Traces
              </button>
              <button
                className={`tab-btn ${activeTab === "policy" ? "active" : ""}`}
                onClick={() => setActiveTab("policy")}
              >
                Refund Policy
              </button>
            </div>
          </div>

          <div className="panel-content">
            {activeTab === "logs" ? (
              <>
                {/* METRICS HEADER CARDS */}
                <div className="metrics-grid">
                  <div className="metric-card">
                    <div className="metric-title">Total Tests</div>
                    <div className="metric-value">{metrics.total_sessions}</div>
                    <div className="metric-subtitle">Evaluations</div>
                  </div>
                  <div className="metric-card" style={{ borderColor: "rgba(16, 185, 129, 0.2)" }}>
                    <div className="metric-title" style={{ color: "var(--success)" }}>Approved</div>
                    <div className="metric-value">{metrics.approved_count}</div>
                    <div className="metric-subtitle">Auto-Approved</div>
                  </div>
                  <div className="metric-card" style={{ borderColor: "rgba(245, 158, 11, 0.2)" }}>
                    <div className="metric-title" style={{ color: "var(--warning)" }}>Escalations</div>
                    <div className="metric-value">{metrics.escalated_count}</div>
                    <div className="metric-subtitle">Transfer Rate</div>
                  </div>
                  <div className="metric-card">
                    <div className="metric-title">Agent Cost</div>
                    <div className="metric-value">${metrics.total_cost.toFixed(5)}</div>
                    <div className="metric-subtitle">{metrics.total_tokens} Tokens</div>
                  </div>
                </div>

                {/* SESSIONS SPLIT */}
                <div style={{ display: "grid", gridTemplateRows: "180px 1fr", gap: "1rem", flex: 1, minHeight: 0 }}>

                  {/* SESSION LIST */}
                  <div style={{ overflowY: "auto", borderBottom: "1px solid var(--border-color)", paddingBottom: "0.75rem" }}>
                    <div style={{ fontSize: "0.7rem", fontWeight: "600", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "0.5rem" }}>
                      Trace Sessions
                    </div>
                    {adminSessions.length > 0 ? (
                      <div className="trace-sessions-list">
                        {adminSessions.map((s) => {
                          const isSelected = selectedSession && selectedSession.session_id === s.session_id;
                          return (
                            <div
                              key={s.session_id}
                              className={`trace-session-item ${isSelected ? "selected" : ""}`}
                              onClick={() => setSelectedSession(s)}
                            >
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <span style={{ fontSize: "0.75rem", fontWeight: "600", color: "#fff" }}>
                                  {s.customer_name || "Unknown Customer"}
                                </span>
                                <span className={`trace-status-badge status-${s.status}`} style={{ display: "flex", alignItems: "center", gap: "0.2rem" }}>
                                  {getStatusIcon(s.status)}
                                  {s.status}
                                </span>
                              </div>
                              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.65rem", color: "var(--text-muted)", marginTop: "0.15rem" }}>
                                <span>{s.session_id}</span>
                                <span>{formatTime(s.start_time)}</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", padding: "1rem 0", textAlign: "center" }}>
                        No session traces recorded yet. Start chatting to trigger logs.
                      </div>
                    )}
                  </div>

                  {/* CHOSEN SESSION STEPS DETAIL */}
                  <div style={{ display: "flex", flexDirection: "column", minHeight: 0, height: "100%" }}>
                    {selectedSession ? (
                      <>
                        <div style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          fontSize: "0.7rem",
                          fontWeight: "600",
                          textTransform: "uppercase",
                          color: "var(--text-muted)",
                          marginBottom: "0.5rem"
                        }}>
                          <span>Step Logs: {selectedSession.session_id}</span>
                          <span style={{ textTransform: "none", color: "var(--primary)", fontWeight: "500", display: "flex", gap: "0.75rem" }}>
                            <span><Clock style={{ width: 10, height: 10, verticalAlign: "middle", marginRight: 2 }} /> Latency: {selectedSession.total_latency.toFixed(2)}s</span>
                            <span><Coins style={{ width: 10, height: 10, verticalAlign: "middle", marginRight: 2 }} /> Cost: ${selectedSession.total_cost.toFixed(5)}</span>
                          </span>
                        </div>

                        <div className="trace-steps-container" style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
                          {selectedSession.steps.map((step, idx) => (
                            <div key={idx} className="step-card">
                              <div className={`step-header step-header-${step.step_type}`}>
                                <span>{step.step_type.replace("_", " ")}</span>
                                <div style={{ display: "flex", gap: "0.5rem", fontSize: "0.6rem" }}>
                                  {step.latency && <span>{step.latency.toFixed(2)}s</span>}
                                  {step.cost > 0 && <span>${step.cost.toFixed(5)}</span>}
                                </div>
                              </div>
                              <div className="step-body">
                                {typeof step.content === "object" ? (
                                  <pre className="step-body-code">
                                    {JSON.stringify(step.content, null, 2)}
                                  </pre>
                                ) : (
                                  step.content
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </>
                    ) : (
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", padding: "2rem 0", textAlign: "center" }}>
                        Select a trace session above to view its internal reasoning steps and tool execution.
                      </div>
                    )}
                  </div>

                </div>
              </>
            ) : (
              <div style={{ overflowY: "auto", fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: "1.5" }}>
                <div style={{ fontWeight: "700", color: "#fff", marginBottom: "0.5rem" }}>Corporate Refund Policy Guidelines</div>
                <div style={{ background: "rgba(0,0,0,0.2)", border: "1px solid var(--border-color)", borderRadius: "var(--radius-md)", padding: "1rem", fontFamily: "monospace", fontSize: "0.75rem" }}>
                  <pre style={{ whiteSpace: "pre-wrap" }}>
                    {`1. RETURN WINDOW:
   - Must be within exactly 30 days of purchase.
   - Deny refund if day >= 31.

2. ITEM ELIGIBILITY:
   - "Final Sale" items are STRICTLY non-refundable.
   - Packaging: Must possess original packaging.
     (Sarah MUST verify this first).

3. EXPORT / ESCALATION CONTROLS:
   - Value Limit: Requests > $500 require human admin.
   - Freq Limit: Max 3 approved refunds/year per user.
   - Aggression: Transfer to human after 2 explains of a denial.`}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </section>

      </div>
    </div>
  );
}

export default App;
