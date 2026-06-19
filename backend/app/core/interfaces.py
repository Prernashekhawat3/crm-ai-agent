from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import date
from app.database.schema import CustomerDTO, OrderDTO, RefundDTO

class ILLMService(ABC):
    """
    Interface for interacting with the LLM API provider (e.g., Groq, OpenAI).
    Ensures OCP: can add other models or APIs without changing the agent loop.
    """
    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abstractmethod
    def call_with_tools(
        self,
        system_instruction: str,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Executes an LLM request with custom system instructions, historical messages, 
        and available function tools. Returns a structured dict containing:
        - content: Optional text response
        - tool_calls: List of requested tool invocations
        - tokens_in, tokens_out: Usage metrics
        - latency: Call duration
        """
        pass


class ICRMRepository(ABC):
    """
    Interface for CRM data access.
    Ensures separation of database operations from agent logic.
    """
    @abstractmethod
    def get_customer_by_email(self, email: str) -> Optional[CustomerDTO]:
        pass

    @abstractmethod
    def get_customer_by_id(self, customer_id: int) -> Optional[CustomerDTO]:
        pass

    @abstractmethod
    def list_orders_by_customer_id(self, customer_id: int) -> List[OrderDTO]:
        pass

    @abstractmethod
    def get_order_by_id(self, order_id: int) -> Optional[OrderDTO]:
        pass

    @abstractmethod
    def count_approved_refunds_in_year(self, customer_id: int, year: int) -> int:
        pass

    @abstractmethod
    def create_refund(self, order_id: int, amount: float, status: str, reason: str) -> RefundDTO:
        pass

    @abstractmethod
    def update_order_status(self, order_id: int, status: str) -> None:
        pass


class IPolicyValidator(ABC):
    """
    Interface for validating refund requests against corporate refund policies.
    """
    @abstractmethod
    def get_policy_text(self) -> str:
        """
        Returns the raw corporate refund policy text.
        """
        pass

    @abstractmethod
    def evaluate_request(
        self,
        order: OrderDTO,
        item_ids: List[int],
        original_packaging: bool,
        approved_refunds_this_year: int
    ) -> Dict[str, Any]:
        """
        Validates refund criteria programmatically and returns:
        - eligible: bool
        - action: str ('APPROVE', 'DENY', 'ESCALATE')
        - reason: str
        - total_refundable_amount: float
        """
        pass
