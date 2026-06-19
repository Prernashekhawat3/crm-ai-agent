import pytest
from datetime import date, timedelta
from app.core.policy_validator import PolicyValidator
from app.database.schema import OrderDTO, OrderItemDTO

@pytest.fixture
def policy_validator():
    return PolicyValidator()

def test_refund_window_expired(policy_validator):
    # Purchase date was 45 days ago -> out of window
    order = OrderDTO(
        id=101,
        customer_id=1,
        purchase_date=date.today() - timedelta(days=45),
        status="Delivered",
        payment_method="Credit Card",
        total_amount=100.0,
        items=[
            OrderItemDTO(id=1, product_name="Regular Shoes", price=100.0, is_final_sale=False)
        ],
        refunds=[]
    )
    result = policy_validator.evaluate_request(
        order=order,
        item_ids=[1],
        original_packaging=True,
        approved_refunds_this_year=0
    )
    assert result["eligible"] is False
    assert result["action"] == "DENY"
    assert "exceeds the 30-day refund window" in result["reason"]

def test_refund_final_sale_denied(policy_validator):
    # Order within 10 days, but item is final sale
    order = OrderDTO(
        id=102,
        customer_id=1,
        purchase_date=date.today() - timedelta(days=10),
        status="Delivered",
        payment_method="Credit Card",
        total_amount=150.0,
        items=[
            OrderItemDTO(id=2, product_name="Clearance Shirt", price=50.0, is_final_sale=True),
            OrderItemDTO(id=3, product_name="Normal Pants", price=100.0, is_final_sale=False)
        ],
        refunds=[]
    )
    # Try refunding final sale item
    result = policy_validator.evaluate_request(
        order=order,
        item_ids=[2],
        original_packaging=True,
        approved_refunds_this_year=0
    )
    assert result["eligible"] is False
    assert result["action"] == "DENY"
    assert "is designated as 'Final Sale'" in result["reason"]

def test_refund_no_packaging_denied(policy_validator):
    # Valid order, but customer lost the original packaging
    order = OrderDTO(
        id=103,
        customer_id=1,
        purchase_date=date.today() - timedelta(days=5),
        status="Delivered",
        payment_method="Credit Card",
        total_amount=60.0,
        items=[
            OrderItemDTO(id=4, product_name="Socks", price=60.0, is_final_sale=False)
        ],
        refunds=[]
    )
    result = policy_validator.evaluate_request(
        order=order,
        item_ids=[4],
        original_packaging=False,
        approved_refunds_this_year=0
    )
    assert result["eligible"] is False
    assert result["action"] == "DENY"
    assert "does not have original packaging" in result["reason"]

def test_refund_high_value_escalation(policy_validator):
    # Refund total is > $500 -> must escalate
    order = OrderDTO(
        id=104,
        customer_id=1,
        purchase_date=date.today() - timedelta(days=5),
        status="Delivered",
        payment_method="Credit Card",
        total_amount=600.0,
        items=[
            OrderItemDTO(id=5, product_name="Expensive Watch", price=600.0, is_final_sale=False)
        ],
        refunds=[]
    )
    result = policy_validator.evaluate_request(
        order=order,
        item_ids=[5],
        original_packaging=True,
        approved_refunds_this_year=0
    )
    assert result["eligible"] is False
    assert result["action"] == "ESCALATE"
    assert "exceeds the auto-approval limit of $500.00" in result["reason"]

def test_refund_frequency_limit_escalation(policy_validator):
    # Customer already has 3 approved refunds in 2026 -> must escalate
    order = OrderDTO(
        id=105,
        customer_id=1,
        purchase_date=date.today() - timedelta(days=5),
        status="Delivered",
        payment_method="Credit Card",
        total_amount=50.0,
        items=[
            OrderItemDTO(id=6, product_name="Plush Toy", price=50.0, is_final_sale=False)
        ],
        refunds=[]
    )
    result = policy_validator.evaluate_request(
        order=order,
        item_ids=[6],
        original_packaging=True,
        approved_refunds_this_year=3
    )
    assert result["eligible"] is False
    assert result["action"] == "ESCALATE"
    assert "exceeds the return frequency limit" in result["reason"]

def test_refund_processing_or_shipped_denied(policy_validator):
    # Order status is Shipped -> cannot refund yet
    order = OrderDTO(
        id=106,
        customer_id=1,
        purchase_date=date.today() - timedelta(days=2),
        status="Shipped",
        payment_method="PayPal",
        total_amount=100.0,
        items=[
            OrderItemDTO(id=7, product_name="Book Shelf", price=100.0, is_final_sale=False)
        ],
        refunds=[]
    )
    result = policy_validator.evaluate_request(
        order=order,
        item_ids=[7],
        original_packaging=True,
        approved_refunds_this_year=0
    )
    assert result["eligible"] is False
    assert result["action"] == "DENY"
    assert "Order is in transit" in result["reason"]

def test_refund_success(policy_validator):
    # All criteria met
    order = OrderDTO(
        id=107,
        customer_id=1,
        purchase_date=date.today() - timedelta(days=12),
        status="Delivered",
        payment_method="Apple Pay",
        total_amount=120.0,
        items=[
            OrderItemDTO(id=8, product_name="Desk Lamp", price=120.0, is_final_sale=False)
        ],
        refunds=[]
    )
    result = policy_validator.evaluate_request(
        order=order,
        item_ids=[8],
        original_packaging=True,
        approved_refunds_this_year=1
    )
    assert result["eligible"] is True
    assert result["action"] == "APPROVE"
    assert result["amount"] == 120.0
    assert "All criteria met" in result["reason"]
