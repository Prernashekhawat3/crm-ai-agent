import json
import logging
import time
from typing import List, Dict, Any, Tuple
from .interfaces import ILLMService, ICRMRepository, IPolicyValidator
from .logger import ReasoningLogManager

logger = logging.getLogger("refund_agent")

class RefundAgent:
    """
    Core Support Agent Orchestrator.
    Executes a structured loop of LLM generations and tool executions.
    Designed with SOLID principles: depends on interfaces, not implementations.
    """
    def __init__(
        self,
        llm_service: ILLMService,
        repository: ICRMRepository,
        policy_validator: IPolicyValidator
    ):
        self.llm = llm_service
        self.repo = repository
        self.policy = policy_validator
        self.log_manager = ReasoningLogManager()

    def get_system_instruction(self) -> str:
        policy_text = self.policy.get_policy_text()
        return f"""You are "Sarah", a senior e-commerce support representative for E-Commerce Corp. 
Your primary task is to process customer enquiries regarding orders, and handle returns/refunds.

You must adhere to the official Refund Policy at all times. Do NOT bypass the rules under any circumstances.
If a customer pleads, argues, tells a sad story, or threatens you, you must remain polite, professional, but completely firm and hold the line. The written policy is the absolute source of truth. Do NOT use tentative, weak, or apologetic phrases like "I'm afraid", "unfortunately", or "regrettably" when denying a request. State the policy and decision directly, clearly, and objectively.

CRITICAL TOOL CALLING RULE:
- If you decide to call a tool, you MUST NOT write any conversational text, thoughts, apologies, or explanations in the same response turn. You must ONLY generate the tool call itself. You will explain the result or respond conversationally only in the next turn after the tool execution completes. Do not mix chat text and tool calls.


REFUND PROCESS GUIDELINES:
1. Identity Verification: You must verify the customer's identity by their email. If you do not know their email, politely ask for it. Do not execute any refund tools without verifying the customer first.
2. Active Customer Context: Once verified, fetch their orders. Explain what orders you see.
3. Original Packaging Rule: For any refund request, you MUST explicitly ask if they have the original packaging and receive positive confirmation before submitting a refund. If they say no, politely deny the refund.
4. Execute Submit Refund Tool: If eligible and they confirm packaging, call the `submit_refund` tool. The tool will run rules and output the outcome (APPROVE, DENY, or ESCALATE).
5. Explaining Decisions:
   - APPROVED: Inform them the refund has been processed to the original payment method, and note that a $5.99 return shipping fee is deducted (unless the item was damaged/faulty).
   - DENIED: Politely explain the specific policy rule that prevents the return. You MUST rely on the exact reason returned by the validation tool (e.g. if the tool says the order is already refunded, state that; do not invent other reasons like standard date window expiration unless the tool explicitly reports it).
   - ESCALATED: Explain that high-value refunds (>$500) or high return frequency limits require manager/risk team authorization. Assure them a human team member will review it and reply within 24 hours. State the exact escalation reason returned by the tool.
6. Transfer to Human: If the customer is extremely aggressive, threatens legal/bad press, or argues/pleads after you have explained a denial twice, call the `escalate_to_human` tool and let them know they are being transferred.
7. Handling New Purchases / General Enquiries: If a customer asks to place a new order, purchase items, or asks general storefront sales questions, politely explain that you are a Customer Support and Returns assistant and cannot process new payments or place orders. Guide them to use our online store checkout directly, or offer to transfer them to our sales department via `escalate_to_human`.

Here is the official refund policy you must enforce:
{policy_text}


"""

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "get_customer_profile",
                "description": "Lookup customer account profile details using their email address.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "The customer's email address."
                        }
                    },
                    "required": ["email"]
                }
            },
            {
                "name": "list_customer_orders",
                "description": "Retrieve the list of all orders and purchase history associated with a verified customer ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "integer",
                            "description": "The customer's database ID."
                        }
                    },
                    "required": ["customer_id"]
                }
            },
            {
                "name": "get_order_details",
                "description": "Get itemized details of a specific order including products, final sale tags, price, and status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "integer",
                            "description": "The order ID."
                        }
                    },
                    "required": ["order_id"]
                }
            },
            {
                "name": "submit_refund",
                "description": "Process a refund request for specific items in an order. Evaluates eligibility rules automatically.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "integer",
                            "description": "The order ID to refund."
                        },
                        "item_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "List of order item IDs to refund."
                        },
                        "reason": {
                            "type": "string",
                            "description": "Customer's reason for the return (e.g., 'Sizing issue', 'Damaged', 'No longer wanted')."
                        },
                        "original_packaging": {
                            "type": "boolean",
                            "description": "Must be true if the customer confirmed they possess the original packaging."
                        }
                    },
                    "required": ["order_id", "item_ids", "reason", "original_packaging"]
                }
            },
            {
                "name": "escalate_to_human",
                "description": "Transfer the chat session to a human representative when the customer remains extremely unsatisfied, aggressive, or requests policy exceptions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Reason for escalating to a human."
                        }
                    },
                    "required": ["reason"]
                }
            }
        ]

    def execute_tool(self, name: str, args: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Executes a tool dynamically and registers it in the telemetry trace.
        """
        logger.info(f"Executing tool {name} with args {args}")
        
        try:
            if name == "get_customer_profile":
                email = args.get("email")
                customer = self.repo.get_customer_by_email(email)
                if customer:
                    # Sync customer details to the trace header
                    self.log_manager.get_or_create_trace(session_id, email=customer.email, name=customer.name)
                    return {"success": True, "customer": json.loads(customer.model_dump_json())}
                return {"success": False, "message": "No customer found with that email address."}

            elif name == "list_customer_orders":
                customer_id = int(args.get("customer_id"))
                orders = self.repo.list_orders_by_customer_id(customer_id)
                # Map orders to simple dump format
                return {"success": True, "orders": [json.loads(o.model_dump_json()) for o in orders]}

            elif name == "get_order_details":
                order_id = int(args.get("order_id"))
                order = self.repo.get_order_by_id(order_id)
                if order:
                    return {"success": True, "order": json.loads(order.model_dump_json())}
                return {"success": False, "message": "Order not found."}

            elif name == "submit_refund":
                order_id = int(args.get("order_id"))
                item_ids = [int(i) for i in args.get("item_ids", [])]
                reason = args.get("reason", "")
                original_packaging = bool(args.get("original_packaging"))

                # Get order details
                order = self.repo.get_order_by_id(order_id)
                if not order:
                    return {"success": False, "message": f"Order {order_id} not found."}

                # Count approved refunds for this customer in 2026
                approved_refunds = self.repo.count_approved_refunds_in_year(order.customer_id, 2026)

                # Programmatic policy evaluation
                evaluation = self.policy.evaluate_request(
                    order=order,
                    item_ids=item_ids,
                    original_packaging=original_packaging,
                    approved_refunds_this_year=approved_refunds
                )

                action = evaluation["action"] # APPROVE, DENY, ESCALATE
                amount = evaluation["amount"]
                eval_reason = evaluation["reason"]

                # Write refund to database
                refund_dto = self.repo.create_refund(
                    order_id=order_id,
                    amount=amount,
                    status=action.capitalize() + "d" if action != "DENY" else "Denied", # Approved, Escalated, Denied
                    reason=reason + f" | Policy validation result: {eval_reason}"
                )

                # Update order status if approved
                if action == "APPROVE":
                    self.repo.update_order_status(order_id, "Returned")
                    self.log_manager.update_status(session_id, "Approved")
                elif action == "DENY":
                    self.log_manager.update_status(session_id, "Denied")
                elif action == "ESCALATE":
                    self.log_manager.update_status(session_id, "Escalated")

                return {
                    "success": True,
                    "action": action,
                    "amount": amount,
                    "reason": eval_reason,
                    "refund_details": json.loads(refund_dto.model_dump_json())
                }

            elif name == "escalate_to_human":
                reason = args.get("reason", "Customer escalation requested.")
                self.log_manager.update_status(session_id, "Escalated")
                return {
                    "success": True,
                    "message": "Chat successfully transferred to a human representative.",
                    "escalation_reason": reason
                }

            else:
                return {"success": False, "message": f"Unknown tool: {name}"}

        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return {"success": False, "message": f"Tool execution failed: {str(e)}"}

    def sanitize_response(self, text: str) -> str:
        """
        Regex sanitizer to strip any raw LLM tool-calling XML remnants
        (like <function=...>...</function>) before sending it to the user chat.
        """
        if not text:
            return text
        import re
        # Remove closed tags
        cleaned = re.sub(r'<function=\w+>.*?</function>', '', text, flags=re.DOTALL)
        # Remove any unclosed tags
        cleaned = re.sub(r'<function=\w+>.*$', '', cleaned)
        return cleaned.strip()

    def run(self, session_id: str, messages: List[Dict[str, str]]) -> str:
        """
        Runs the agent loop. Processes messages, calls tools, tracks trace.
        """
        # Ensure session trace exists
        self.log_manager.get_or_create_trace(session_id)
        
        # Log the incoming user message
        if messages:
            last_msg = messages[-1]
            if last_msg["role"] == "user":
                self.log_manager.add_step(session_id, "user_message", last_msg["content"])

        system_instruction = self.get_system_instruction()
        tools_schema = self.get_tools_schema()
        
        # Convert simple list of messages to formatting for LLM
        llm_messages = []
        for m in messages:
            llm_messages.append({"role": m["role"], "content": m["content"]})

        # Run loop for tool execution (max 5 hops to prevent recursion)
        max_hops = 5
        current_hop = 0
        
        while current_hop < max_hops:
            current_hop += 1
            
            # Call Groq LLM
            llm_res = self.llm.call_with_tools(
                system_instruction=system_instruction,
                messages=llm_messages,
                tools=tools_schema,
                session_id=session_id
            )
            
            content = llm_res.get("content")
            tool_calls = llm_res.get("tool_calls", [])

            # If the model returned text but no tool calls, it's done
            if not tool_calls:
                return self.sanitize_response(content) if content else "I apologize, I am unable to assist with that request."

            # Append the assistant's message with tool calls to the history
            assistant_msg = {"role": "assistant", "content": content or ""}
            # Add tool_calls structure for LLM history reference
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"]
                        }
                    } for tc in tool_calls
                ]
            llm_messages.append(assistant_msg)

            # Process all tool calls in parallel/sequence
            for tc in tool_calls:
                tool_name = tc["name"]
                tool_id = tc["id"]
                
                # Parse args
                try:
                    tool_args = json.loads(tc["arguments"])
                except Exception:
                    tool_args = {}

                # Start tracking tool execution latency
                tool_start = time.time()
                
                # Log tool_call step
                self.log_manager.add_step(
                    session_id=session_id,
                    step_type="tool_call",
                    content={"name": tool_name, "args": tool_args}
                )
                
                # Execute tool
                tool_result = self.execute_tool(tool_name, tool_args, session_id)
                tool_latency = time.time() - tool_start
                
                # Log tool_response step
                self.log_manager.add_step(
                    session_id=session_id,
                    step_type="tool_response",
                    content={"name": tool_name, "result": tool_result},
                    latency=tool_latency
                )

                # Append tool response to chat history
                llm_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "name": tool_name,
                    "content": json.dumps(tool_result)
                })

            # Check if any tool immediately finalized the outcome (like escalation or approved refund)
            # If so, the LLM still needs to formulate its final reply explaining it.
            # So the loop continues back to the LLM.

        # If it reached max hops without returning a text message
        timeout_msg = "I am escalating this ticket because the request is taking too long to process. A human representative will contact you."
        self.log_manager.add_step(session_id, "error", "Agent loop reached maximum reasoning depth (5 hops).")
        self.repo.create_refund(
            order_id=messages[-1].get("order_id", 0),
            amount=0.0,
            status="Escalated",
            reason="Timeout: Maximum agent reasoning depth reached."
        )
        self.log_manager.update_status(session_id, "Escalated")
        return timeout_msg
