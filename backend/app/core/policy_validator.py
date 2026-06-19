import os
from typing import List, Dict, Any
from datetime import date, datetime
from .interfaces import IPolicyValidator
from app.database.schema import OrderDTO

class PolicyValidator(IPolicyValidator):
    """
    Concrete implementation of the policy validator.
    Validates rules against the corporate refund policy.
    """
    def __init__(self, policy_path: str = None):
        if policy_path is None:
            # Default to backend/data/policy.txt relative to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.policy_path = os.path.join(base_dir, "data", "policy.txt")
        else:
            self.policy_path = policy_path

    def get_policy_text(self) -> str:
        try:
            with open(self.policy_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "Refund Policy File not found. Maintain strict default guidelines."

    def evaluate_request(
        self,
        order: OrderDTO,
        item_ids: List[int],
        original_packaging: bool,
        approved_refunds_this_year: int
    ) -> Dict[str, Any]:
        """
        Evaluate a refund request programmatically.
        Returns:
            {
                "eligible": bool,
                "action": str ('APPROVE' | 'DENY' | 'ESCALATE'),
                "reason": str,
                "amount": float
            }
        """
        policy_text = self.get_policy_text()
        
        # 0. Validate order status. If processing or shipped, cannot return yet.
        if order.status == "Processing":
            return {
                "eligible": False,
                "action": "DENY",
                "reason": "Order is still processing. Refunds are only allowed after delivery.",
                "amount": 0.0
            }
        elif order.status == "Shipped":
            return {
                "eligible": False,
                "action": "DENY",
                "reason": "Order is in transit. Refunds are only allowed after the package is delivered and inspected.",
                "amount": 0.0
            }
        elif order.status == "Returned":
            # Check if this order was already refunded
            # Find any approved refund for this order
            approved_refunds = [r for r in order.refunds if r.status == "Approved"]
            if len(approved_refunds) > 0:
                return {
                    "eligible": False,
                    "action": "DENY",
                    "reason": "This order has already been fully refunded.",
                    "amount": 0.0
                }

        # 1. Standard Refund Window (30 Days)
        purchase_date = order.purchase_date
        days_since_purchase = (date.today() - purchase_date).days
        if days_since_purchase > 30:
            return {
                "eligible": False,
                "action": "DENY",
                "reason": f"Request submitted on day {days_since_purchase}, which exceeds the 30-day refund window limit.",
                "amount": 0.0
            }

        # 2. Condition & Packaging Check
        if not original_packaging:
            return {
                "eligible": False,
                "action": "DENY",
                "reason": "Customer does not have original packaging, which is required by Section 2 of the corporate policy.",
                "amount": 0.0
            }

        # 3. Item Eligibility (Final Sale)
        # Find matching items in order and check final sale
        refund_amount = 0.0
        order_item_ids = {item.id: item for item in order.items}
        
        for item_id in item_ids:
            if item_id not in order_item_ids:
                return {
                    "eligible": False,
                    "action": "DENY",
                    "reason": f"Item ID {item_id} is not part of Order {order.id}.",
                    "amount": 0.0
                }
            item = order_item_ids[item_id]
            if item.is_final_sale:
                return {
                    "eligible": False,
                    "action": "DENY",
                    "reason": f"Item '{item.product_name}' (ID {item.id}) is designated as 'Final Sale' and is strictly non-refundable.",
                    "amount": 0.0
                }
            refund_amount += item.price

        # 4. Limit Check: Refund Abuse Frequency (> 3 approved in current calendar year)
        if approved_refunds_this_year >= 3:
            return {
                "eligible": False,
                "action": "ESCALATE",
                "reason": f"Customer has already received {approved_refunds_this_year} refunds in the current calendar year. This exceeds the return frequency limit and requires risk assessment team review.",
                "amount": refund_amount
            }

        # 5. Escalation Limit Check (High Value > $500)
        if refund_amount > 500.00:
            return {
                "eligible": False,
                "action": "ESCALATE",
                "reason": f"Total refundable amount (${refund_amount:.2f}) exceeds the auto-approval limit of $500.00. Requires manual administrator escalation.",
                "amount": refund_amount
            }

        # If it passes all checks, it's eligible
        return {
            "eligible": True,
            "action": "APPROVE",
            "reason": f"All criteria met. Total refund of ${refund_amount:.2f} approved.",
            "amount": refund_amount
        }
