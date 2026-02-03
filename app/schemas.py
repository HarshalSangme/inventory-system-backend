from typing import List, Optional
from pydantic import BaseModel
from .models import Role, PartnerType, TransactionType
from datetime import datetime

class UserBase(BaseModel):
    username: str
    role: str = Role.SALES

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ProductBase(BaseModel):
    name: str
    sku: str
    description: Optional[str] = None
    price: float
    cost_price: float
    min_stock_level: int = 5

class ProductCreate(ProductBase):
    stock_quantity: int = 0

class Product(ProductBase):
    id: int
    stock_quantity: int
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

class TransactionCreate(BaseModel):
    partner_id: int
    type: str # TransactionType
    items: List[TransactionItemBase]

class Transaction(BaseModel):
    id: int
    date: datetime
    type: str
    partner_id: int
    total_amount: float
    items: List[TransactionItemBase] = []
    class Config:
        from_attributes = True
