
from typing import List, Optional
from pydantic import BaseModel
from .models import Role, PartnerType, TransactionType
from datetime import datetime

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    role: str = Role.SALES
    email_verified: bool = True
    admin_approved: bool = True

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    email: Optional[str] = None
    email_verified: bool = True
    admin_approved: bool = True
    email_verification_token: Optional[str] = None
    email_verification_token_expiry: Optional[datetime] = None
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None


class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int
    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    sku: str
    description: Optional[str] = None
    price: float
    cost_price: float
    min_stock_level: int = 5
    category_id: Optional[int] = None


class ProductCreate(ProductBase):
    stock_quantity: int = 0


class Product(ProductBase):
    id: int
    stock_quantity: int
    category: Optional[Category] = None
    class Config:
        from_attributes = True

class PartnerBase(BaseModel):
    name: str
    type: str # PartnerType
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class PartnerCreate(PartnerBase):
    pass

class Partner(PartnerBase):
    id: int
    class Config:
        from_attributes = True

class TransactionItemBase(BaseModel):
    product_id: int
    quantity: int
    price: float
    discount: float = 0  # Per-item discount amount
    vat_percent: float = 0  # Per-item VAT percent

class TransactionCreate(BaseModel):
    partner_id: int
    type: str # TransactionType
    items: List[TransactionItemBase]
    sales_person: Optional[str] = None
    payment_method: Optional[str] = "Cash"

class TransactionItemOut(TransactionItemBase):
    id: int
    product: Product
    class Config:
        from_attributes = True

class Transaction(BaseModel):
    id: int
    date: datetime
    type: str
    partner_id: int
    total_amount: float
    sales_person: Optional[str] = None
    payment_method: Optional[str] = "Cash"
    partner: Optional[Partner] = None
    items: List[TransactionItemOut] = []
    class Config:
        from_attributes = True
