import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import date, timedelta
from .schema import Base, Customer, Order, OrderItem, Refund

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./refund_agent.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_db(db: Session):
    # Check if database is already seeded
    if db.query(Customer).count() > 0:
        return
    
    today = date.today()
    
    # 1. Alice - Clean Success case
    alice = Customer(name="Alice Vance", email="alice@example.com", tier="VIP")
    db.add(alice)
    db.flush() # get ID
    
    o_alice = Order(
        customer_id=alice.id,
        purchase_date=today - timedelta(days=10), # within 30 days
        status="Delivered",
        payment_method="Credit Card",
        total_amount=150.00
    )
    db.add(o_alice)
    db.flush()
    db.add_all([
        OrderItem(order_id=o_alice.id, product_name="Premium Wireless Headphones", price=120.00, is_final_sale=False),
        OrderItem(order_id=o_alice.id, product_name="USB-C Charging Cable", price=30.00, is_final_sale=False)
    ])

    # 2. Bob - Out of Window case (pleading)
    bob = Customer(name="Bob Smith", email="bob@example.com", tier="Standard")
    db.add(bob)
    db.flush()
    
    o_bob = Order(
        customer_id=bob.id,
        purchase_date=today - timedelta(days=45), # out of window
        status="Delivered",
        payment_method="PayPal",
        total_amount=80.00
    )
    db.add(o_bob)
    db.flush()
    db.add_all([
        OrderItem(order_id=o_bob.id, product_name="Ergonomic Mouse", price=50.00, is_final_sale=False),
        OrderItem(order_id=o_bob.id, product_name="Fabric Mousepad", price=30.00, is_final_sale=False)
    ])

    # 3. Charlie - Final Sale case
    charlie = Customer(name="Charlie Brown", email="charlie@example.com", tier="Standard")
    db.add(charlie)
    db.flush()
    
    o_charlie = Order(
        customer_id=charlie.id,
        purchase_date=today - timedelta(days=5), # within window
        status="Delivered",
        payment_method="Credit Card",
        total_amount=135.00
    )
    db.add(o_charlie)
    db.flush()
    db.add_all([
        OrderItem(order_id=o_charlie.id, product_name="Clearance Denim Jacket", price=95.00, is_final_sale=True), # final sale
        OrderItem(order_id=o_charlie.id, product_name="Basic White Tee", price=40.00, is_final_sale=False)
    ])

    # 4. Diana - High Value case (> $500, requires escalation)
    diana = Customer(name="Diana Prince", email="diana@example.com", tier="VIP")
    db.add(diana)
    db.flush()
    
    o_diana = Order(
        customer_id=diana.id,
        purchase_date=today - timedelta(days=12), # within window
        status="Delivered",
        payment_method="Apple Pay",
        total_amount=1250.00
    )
    db.add(o_diana)
    db.flush()
    db.add_all([
        OrderItem(order_id=o_diana.id, product_name="4K Ultra-Wide Monitor", price=850.00, is_final_sale=False), # high value
        OrderItem(order_id=o_diana.id, product_name="Mechanical Keyboard", price=400.00, is_final_sale=False)
    ])

    # 5. Ethan - Abuse prevention (already has 3 refunds in 2026)
    ethan = Customer(name="Ethan Hunt", email="ethan@example.com", tier="Standard")
    db.add(ethan)
    db.flush()
    
    # Order he wants to return now (eligible otherwise)
    o_ethan_new = Order(
        customer_id=ethan.id,
        purchase_date=today - timedelta(days=8),
        status="Delivered",
        payment_method="Credit Card",
        total_amount=90.00
    )
    db.add(o_ethan_new)
    db.flush()
    db.add(OrderItem(order_id=o_ethan_new.id, product_name="Leather Wallet", price=90.00, is_final_sale=False))
    
    # 3 past orders in 2026 that were already fully returned/refunded
    for i in range(3):
        o_past = Order(
            customer_id=ethan.id,
            purchase_date=today - timedelta(days=60 + i*10),
            status="Returned",
            payment_method="Credit Card",
            total_amount=50.00
        )
        db.add(o_past)
        db.flush()
        db.add(OrderItem(order_id=o_past.id, product_name=f"Return Abuse Item {i+1}", price=50.00, is_final_sale=False))
        
        ref = Refund(
            order_id=o_past.id,
            amount=50.00,
            status="Approved",
            requested_date=today - timedelta(days=55 - i*10),
            reason="Defective"
        )
        db.add(ref)

    # 6. Fiona - Shipped order (not delivered yet, refund denied)
    fiona = Customer(name="Fiona Gallagher", email="fiona@example.com", tier="Standard")
    db.add(fiona)
    db.flush()
    
    o_fiona = Order(
        customer_id=fiona.id,
        purchase_date=today - timedelta(days=2),
        status="Shipped", # Shipped, not delivered
        payment_method="PayPal",
        total_amount=110.00
    )
    db.add(o_fiona)
    db.flush()
    db.add(OrderItem(order_id=o_fiona.id, product_name="Winter Parka Coat", price=110.00, is_final_sale=False))

    # 7. George - VIP with Gold Tier standing and a returned order
    george = Customer(name="George Costanza", email="george@example.com", tier="Gold")
    db.add(george)
    db.flush()
    o_george = Order(
        customer_id=george.id,
        purchase_date=today - timedelta(days=14),
        status="Delivered",
        payment_method="Credit Card",
        total_amount=75.00
    )
    db.add(o_george)
    db.flush()
    db.add(OrderItem(order_id=o_george.id, product_name="Velvet Tracksuit Jacket", price=75.00, is_final_sale=False))

    # 8. Hannah - Standard user, normal orders
    hannah = Customer(name="Hannah Abbott", email="hannah@example.com", tier="Standard")
    db.add(hannah)
    db.flush()
    o_hannah = Order(
        customer_id=hannah.id,
        purchase_date=today - timedelta(days=20),
        status="Delivered",
        payment_method="Credit Card",
        total_amount=45.00
    )
    db.add(o_hannah)
    db.flush()
    db.add(OrderItem(order_id=o_hannah.id, product_name="Essential Herb Gardening Kit", price=45.00, is_final_sale=False))

    # 9. Ian - Gold user with multiple orders, one returned, one delivered, one processing
    ian = Customer(name="Ian Malcolm", email="ian@example.com", tier="Gold")
    db.add(ian)
    db.flush()
    o_ian_1 = Order(
        customer_id=ian.id,
        purchase_date=today - timedelta(days=120),
        status="Returned",
        payment_method="Credit Card",
        total_amount=250.00
    )
    db.add(o_ian_1)
    db.flush()
    db.add(OrderItem(order_id=o_ian_1.id, product_name="Prehistoric Amber Replica", price=250.00, is_final_sale=False))
    db.add(Refund(order_id=o_ian_1.id, amount=250.00, status="Approved", requested_date=today - timedelta(days=115), reason="Damaged in shipping"))
    
    o_ian_2 = Order(
        customer_id=ian.id,
        purchase_date=today - timedelta(days=22),
        status="Delivered",
        payment_method="Credit Card",
        total_amount=60.00
    )
    db.add(o_ian_2)
    db.flush()
    db.add(OrderItem(order_id=o_ian_2.id, product_name="Dinosaur Encyclopedia", price=60.00, is_final_sale=False))
    
    o_ian_3 = Order(
        customer_id=ian.id,
        purchase_date=today - timedelta(days=1),
        status="Processing",
        payment_method="Credit Card",
        total_amount=90.00
    )
    db.add(o_ian_3)
    db.flush()
    db.add(OrderItem(order_id=o_ian_3.id, product_name="Jurassic Park Explorer Toy", price=90.00, is_final_sale=False))

    # 10. Julia - VIP user, high value order that succeeded in past
    julia = Customer(name="Julia Roberts", email="julia@example.com", tier="VIP")
    db.add(julia)
    db.flush()
    o_julia = Order(
        customer_id=julia.id,
        purchase_date=today - timedelta(days=28),
        status="Delivered",
        payment_method="Credit Card",
        total_amount=350.00
    )
    db.add(o_julia)
    db.flush()
    db.add(OrderItem(order_id=o_julia.id, product_name="Silk Evening Gown", price=350.00, is_final_sale=False))

    # 11. Kevin - Standard customer, one order
    kevin = Customer(name="Kevin Malone", email="kevin@example.com", tier="Standard")
    db.add(kevin)
    db.flush()
    o_kevin = Order(
        customer_id=kevin.id,
        purchase_date=today - timedelta(days=19),
        status="Delivered",
        payment_method="PayPal",
        total_amount=85.00
    )
    db.add(o_kevin)
    db.flush()
    db.add(OrderItem(order_id=o_kevin.id, product_name="Commercial Chili Pot (10 Gallon)", price=85.00, is_final_sale=False))

    # 12. Laura - Gold customer, bought items on Final Sale but also normal items in same order
    laura = Customer(name="Laura Croft", email="laura@example.com", tier="Gold")
    db.add(laura)
    db.flush()
    o_laura = Order(
        customer_id=laura.id,
        purchase_date=today - timedelta(days=4),
        status="Delivered",
        payment_method="Credit Card",
        total_amount=200.00
    )
    db.add(o_laura)
    db.flush()
    db.add_all([
        OrderItem(order_id=o_laura.id, product_name="Tomb Raider Boots", price=120.00, is_final_sale=False), # returnable
        OrderItem(order_id=o_laura.id, product_name="Collectible Jade Pendant (Clearance)", price=80.00, is_final_sale=True) # final sale
    ])

    # 13. Mike - VIP customer, has returned 2 orders already (close to limit)
    mike = Customer(name="Mike Wheeler", email="mike@example.com", tier="VIP")
    db.add(mike)
    db.flush()
    for i in range(2):
        o_m = Order(
            customer_id=mike.id,
            purchase_date=today - timedelta(days=80 + i*10),
            status="Returned",
            payment_method="Apple Pay",
            total_amount=40.00
        )
        db.add(o_m)
        db.flush()
        db.add(OrderItem(order_id=o_m.id, product_name=f"Stranger Things Merchandise {i+1}", price=40.00, is_final_sale=False))
        db.add(Refund(order_id=o_m.id, amount=40.00, status="Approved", requested_date=today - timedelta(days=75 - i*10), reason="Sizing Issue"))

    o_mike_active = Order(
        customer_id=mike.id,
        purchase_date=today - timedelta(days=15),
        status="Delivered",
        payment_method="Apple Pay",
        total_amount=60.00
    )
    db.add(o_mike_active)
    db.flush()
    db.add(OrderItem(order_id=o_mike_active.id, product_name="Dungeons & Dragons Starter Kit", price=60.00, is_final_sale=False))

    # 14. Nancy - Standard user, order within window but status is still "Processing" (no refund yet)
    nancy = Customer(name="Nancy Drew", email="nancy@example.com", tier="Standard")
    db.add(nancy)
    db.flush()
    o_nancy = Order(
        customer_id=nancy.id,
        purchase_date=today - timedelta(days=3),
        status="Processing",
        payment_method="Credit Card",
        total_amount=35.00
    )
    db.add(o_nancy)
    db.flush()
    db.add(OrderItem(order_id=o_nancy.id, product_name="Vintage Magnifying Glass", price=35.00, is_final_sale=False))

    # 15. Oscar - Gold user, order has already been fully refunded
    oscar = Customer(name="Oscar Martinez", email="oscar@example.com", tier="Gold")
    db.add(oscar)
    db.flush()
    o_oscar = Order(
        customer_id=oscar.id,
        purchase_date=today - timedelta(days=12),
        status="Returned",
        payment_method="PayPal",
        total_amount=150.00
    )
    db.add(o_oscar)
    db.flush()
    db.add(OrderItem(order_id=o_oscar.id, product_name="Tax Accounting Software Suite", price=150.00, is_final_sale=False))
    db.add(Refund(order_id=o_oscar.id, amount=150.00, status="Approved", requested_date=today - timedelta(days=10), reason="Accidental Purchase"))

    db.commit()

def reset_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    db = SessionLocal()
    try:
        seed_db(db)
    finally:
        db.close()
