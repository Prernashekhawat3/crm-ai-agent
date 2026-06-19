from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from ..core.interfaces import ICRMRepository
from .schema import CustomerDTO, OrderDTO, RefundDTO
from .schema import Customer, Order, OrderItem, Refund

class CRMRepository(ICRMRepository):
    """
    SQLAlchemy database implementation of the ICRMRepository.
    Decoupled database transactions from the agent core loop.
    """
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_customer_by_email(self, email: str) -> Optional[CustomerDTO]:
        customer = self.db.query(Customer).filter(Customer.email == email.strip().lower()).first()
        if not customer:
            return None
        return CustomerDTO.model_validate(customer)

    def get_customer_by_id(self, customer_id: int) -> Optional[CustomerDTO]:
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return None
        return CustomerDTO.model_validate(customer)

    def list_orders_by_customer_id(self, customer_id: int) -> List[OrderDTO]:
        orders = self.db.query(Order).filter(Order.customer_id == customer_id).all()
        return [OrderDTO.model_validate(o) for o in orders]

    def get_order_by_id(self, order_id: int) -> Optional[OrderDTO]:
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return None
        return OrderDTO.model_validate(order)

    def count_approved_refunds_in_year(self, customer_id: int, year: int) -> int:
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        # Count refunds whose status is 'Approved' and belong to this customer
        count = (
            self.db.query(Refund)
            .join(Order)
            .filter(Order.customer_id == customer_id)
            .filter(Refund.status == "Approved")
            .filter(Refund.requested_date >= start_date)
            .filter(Refund.requested_date <= end_date)
            .count()
        )
        return count

    def create_refund(self, order_id: int, amount: float, status: str, reason: str) -> RefundDTO:
        refund = Refund(
            order_id=order_id,
            amount=amount,
            status=status, # Approved, Escalated, Denied
            requested_date=date.today(),
            reason=reason
        )
        self.db.add(refund)
        self.db.commit()
        self.db.refresh(refund)
        return RefundDTO.model_validate(refund)

    def update_order_status(self, order_id: int, status: str) -> None:
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.status = status
            self.db.commit()
