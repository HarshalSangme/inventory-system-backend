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
    email = Column(String, nullable=True)
    hashed_password = Column(String)
    role = Column(String, default=Role.SALES)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=True)  # Default True for existing users
    admin_approved = Column(Boolean, default=True)  # Default True for existing users
    email_verification_token = Column(String, nullable=True)
    email_verification_token_expiry = Column(DateTime, nullable=True)


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    margin_percent = Column(Float, default=40.0)  # Default margin percent for recommended selling price
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
    image_url = Column(String, nullable=True)
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

class PaymentStatus(str, enum.Enum):
    PAID = "paid"
    PARTIAL = "partial"
    UNPAID = "unpaid"

class PaymentChannel(str, enum.Enum):
    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"
    OTHER = "other"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    type = Column(String) # TransactionType
    partner_id = Column(Integer, ForeignKey("partners.id"))
    total_amount = Column(Float, default=0.0)
    vat_percent = Column(Float, default=0.0)
    sales_person = Column(String, nullable=True)
    payment_method = Column(String, default="Cash")
    amount_paid = Column(Float, default=0.0)
    payment_status = Column(String, default=PaymentStatus.UNPAID.value)
    vendor_invoice_no = Column(String, nullable=True)  # Vendor's own invoice number for purchases

    partner = relationship("Partner", back_populates="transactions")
    items = relationship("TransactionItem", back_populates="transaction")
    payments = relationship("Payment", back_populates="transaction")
    ledger_entries = relationship("LedgerEntry", back_populates="transaction")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    partner_id = Column(Integer, ForeignKey("partners.id"))
    amount = Column(Float)
    date = Column(DateTime, default=datetime.utcnow)
    payment_method = Column(String, default="Cash") # Legacy
    channel = Column(String, default=PaymentChannel.CASH.value)
    reference_id = Column(String, nullable=True) # Transaction ID from UPI/Card
    notes = Column(String, nullable=True)

    transaction = relationship("Transaction", back_populates="payments")
    partner = relationship("Partner")
    ledger_entries = relationship("LedgerEntry", back_populates="payment")

class LedgerEntryType(str, enum.Enum):
    DEBIT = "debit"   # Increases money owed TO the partner (e.g., Purchase Invoice) or decreases money owed BY them
    CREDIT = "credit" # Increases money owed BY the partner (e.g., Sale Invoice) or decreases money owed TO them

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"))
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    amount = Column(Float)
    type = Column(String) # LedgerEntryType
    date = Column(DateTime, default=datetime.utcnow)
    description = Column(String, nullable=True)

    partner = relationship("Partner")
    transaction = relationship("Transaction", back_populates="ledger_entries")
    payment = relationship("Payment", back_populates="ledger_entries")

class TransactionItem(Base):
    __tablename__ = "transaction_items"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    price = Column(Float) # Price at the moment of transaction
    discount = Column(Float, default=0.0) # Per-item discount amount
    vat_percent = Column(Float, default=0.0) # Per-item VAT percent

    transaction = relationship("Transaction", back_populates="items")
    product = relationship("Product", back_populates="transaction_items")
