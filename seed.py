import os
import sys
from datetime import datetime, timedelta
import random

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app import models, crud, schemas

import uuid

def seed_data():
    db = SessionLocal()
    run_id = str(uuid.uuid4())[:4]
    try:
        # Create tables if they don't exist
        models.Base.metadata.create_all(bind=engine)
        
        print("Creating dummy partners...")
        partners = []
        for i in range(1, 6):
            partner = models.Partner(
                name=f"Test Customer {i} ({run_id})",
                phone=f"123-456-{run_id}{i}",
                email=f"customer{i}_{run_id}@test.com",
                type=models.PartnerType.CUSTOMER.value,
                address=f"{i} Test St, Test City"
            )
            db.add(partner)
            partners.append(partner)
        
        for i in range(1, 3):
            vendor = models.Partner(
                name=f"Test Vendor {i} ({run_id})",
                phone=f"987-654-{run_id}{i}",
                email=f"vendor{i}_{run_id}@test.com",
                type=models.PartnerType.VENDOR.value,
                address=f"{i} Vendor Blvd, Test City"
            )
            db.add(vendor)
            partners.append(vendor)
            
        db.commit()
        
        print("Creating dummy products...")
        products = []
        for i in range(1, 11):
            product = models.Product(
                name=f"Test Product {i} ({run_id})",
                sku=f"SKU-{run_id}-{i}",
                category_id=None,
                cost_price=random.uniform(5.0, 20.0),
                price=random.uniform(25.0, 100.0),
                stock_quantity=random.randint(10, 100),
                min_stock_level=10
            )
            db.add(product)
            products.append(product)
            
        db.commit()
        
        print("Creating dummy transactions...")
        # Create Sales
        customers = [p for p in partners if p.type == models.PartnerType.CUSTOMER.value]
        
        for _ in range(15):
            customer = random.choice(customers)
            product1 = random.choice(products)
            product2 = random.choice(products)
            
            # Create through actual CRUD to trigger ledger entries
            items = [
                schemas.TransactionItemBase(product_id=product1.id, quantity=random.randint(1, 5), price=product1.price, discount=0, vat_percent=10),
                schemas.TransactionItemBase(product_id=product2.id, quantity=random.randint(1, 3), price=product2.price, discount=0, vat_percent=10),
            ]
            
            tx_create = schemas.TransactionCreate(
                type=models.TransactionType.SALE.value,
                partner_id=customer.id,
                sales_person="Admin User",
                payment_method="Cash",
                payment_channel="cash",
                amount_paid=0.0, # Make it unpaid initially
                items=items
            )
            
            db_tx = crud.create_transaction(db, tx_create)
            
            # Randomly pay some of them
            if random.choice([True, False]):
                payment_amt = db_tx.total_amount if random.choice([True, False]) else db_tx.total_amount / 2
                crud.record_payment(db, schemas.PaymentCreate(
                    transaction_id=db_tx.id,
                    partner_id=customer.id,
                    amount=payment_amt,
                    payment_method="Cash",
                    channel="cash",
                    notes="Dummy test payment"
                ))
                
        print("Dummy data seeded successfully!")
        
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
