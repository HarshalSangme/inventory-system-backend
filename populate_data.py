from app import crud, schemas, database, models
from app.auth import get_password_hash
from app.database import SessionLocal
import random

db = SessionLocal()

# Create Users
users = [
    {"username": "manager", "password": "password", "role": "manager"},
    {"username": "sales1", "password": "password", "role": "sales"},
    {"username": "sales2", "password": "password", "role": "sales"},
    {"username": "sales3", "password": "password", "role": "sales"},
]

for u in users:
    try:
        u['password'] = get_password_hash(u['password'])
        user_in = schemas.UserCreate(**u)
        crud.create_user(db, user_in)
        print(f"Created user {u['username']}")
    except Exception as e:
        db.rollback()
        print(f"User {u['username']} might exist")

# Create Partners
partners = [
    {"name": "Tech Solutions Ltd", "type": "customer", "email": "contact@techsol.com", "address": "Mumbai, MH"},
    {"name": "General Store 24", "type": "customer", "email": "info@gs24.com", "address": "Delhi, DL"},
    {"name": "Global Electronics", "type": "vendor", "email": "sales@globelec.com", "address": "Bangalore, KA"},
    {"name": "Local Distributors", "type": "vendor", "email": "dist@local.com", "address": "Pune, MH"},
]

db_partners = []
for p in partners:
    try:
        partner_in = schemas.PartnerCreate(**p)
        db_p = crud.create_partner(db, partner_in)
        db_partners.append(db_p)
        print(f"Created partner {p['name']}")
    except Exception as e:
        db.rollback()
        print(f"Partner {p['name']} might exist")

# Create Products
products = [
    {"name": "Wireless Mouse", "sku": "MS-001", "price": 499.0, "cost_price": 250.0, "stock_quantity": 50, "min_stock_level": 10},
    {"name": "Mechanical Keyboard", "sku": "KB-101", "price": 2499.0, "cost_price": 1800.0, "stock_quantity": 20, "min_stock_level": 5},
    {"name": "HD Monitor", "sku": "MN-200", "price": 8999.0, "cost_price": 7000.0, "stock_quantity": 4, "min_stock_level": 5},
    {"name": "USB-C Cable", "sku": "CB-050", "price": 299.0, "cost_price": 100.0, "stock_quantity": 100, "min_stock_level": 20},
]

for p in products:
    try:
        prod_in = schemas.ProductCreate(**p)
        crud.create_product(db, prod_in)
        print(f"Created product {p['name']}")
    except Exception as e:
        db.rollback()
        print(f"Product {p['name']} might exist")

db.close()
