from sqlalchemy import Column, Integer, String, Float, Boolean, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declarative_base
from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Optional

Base = declarative_base()

# ==========================================
# SQLAlchemy Models
# ==========================================

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    tier = Column(String, default="Standard")  # VIP, Gold, Standard
    created_at = Column(DateTime, default=datetime.utcnow)
    
    orders = relationship("Order", back_populates="customer")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    purchase_date = Column(Date, nullable=False)
    status = Column(String, nullable=False)  # Delivered, Shipped, Processing, Returned
    payment_method = Column(String, nullable=False)
    total_amount = Column(Float, nullable=False)
    
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")
    refunds = relationship("Refund", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    is_final_sale = Column(Boolean, default=False)
    
    order = relationship("Order", back_populates="items")

class Refund(Base):
    __tablename__ = "refunds"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False)  # Approved, Escalated, Denied
    requested_date = Column(Date, nullable=False)
    reason = Column(String, nullable=True)
    
    order = relationship("Order", back_populates="refunds")

# ==========================================
# Pydantic Schemas (DIP Data Transfer Objects)
# ==========================================

class CustomerDTO(BaseModel):
    id: int
    name: str
    email: str
    tier: str
    created_at: datetime

    class Config:
        from_attributes = True

class OrderItemDTO(BaseModel):
    id: int
    product_name: str
    price: float
    is_final_sale: bool

    class Config:
        from_attributes = True

class RefundDTO(BaseModel):
    id: int
    order_id: int
    amount: float
    status: str
    requested_date: date
    reason: Optional[str] = None

    class Config:
        from_attributes = True

class OrderDTO(BaseModel):
    id: int
    customer_id: int
    purchase_date: date
    status: str
    payment_method: str
    total_amount: float
    items: List[OrderItemDTO] = []
    refunds: List[RefundDTO] = []

    class Config:
        from_attributes = True
