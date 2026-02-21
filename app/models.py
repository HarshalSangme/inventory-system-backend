from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from .database import Base
import enum
from datetime import datetime

class Role(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    SALES = "sales"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default=Role.SALES)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=True)  # Default True for existing users
    admin_approved = Column(Boolean, default=True)  # Default True for existing users


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    sku = Column(String, unique=True, index=True)  # Barcode
    description = Column(String, nullable=True)
    price = Column(Float) # Selling Price
    cost_price = Column(Float) # Purchase Price
    stock_quantity = Column(Integer, default=0)
    min_stock_level = Column(Integer, default=5)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    category = relationship("Category", back_populates="products")
    transaction_items = relationship("TransactionItem", back_populates="product")

class PartnerType(str, enum.Enum):
    CUSTOMER = "customer"
    VENDOR = "vendor"

class Partner(Base):
    __tablename__ = "partners"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String) # PartnerType
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    
    transactions = relationship("Transaction", back_populates="partner")

class TransactionType(str, enum.Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    RETURN = "return"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    type = Column(String) # TransactionType
    partner_id = Column(Integer, ForeignKey("partners.id"))
    total_amount = Column(Float, default=0.0)
    vat_percent = Column(Float, default=0.0)
    sales_person = Column(String, nullable=True)

    partner = relationship("Partner", back_populates="transactions")
    items = relationship("TransactionItem", back_populates="transaction")

class TransactionItem(Base):
    __tablename__ = "transaction_items"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    price = Column(Float) # Price at the moment of transaction
    discount = Column(Float, default=0.0) # Per-item discount amount
    
    transaction = relationship("Transaction", back_populates="items")
    product = relationship("Product", back_populates="transaction_items")
