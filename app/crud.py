from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    # bcrypt only supports passwords up to 72 bytes
    password = password[:72]
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    # Always hash the password for new users
    hashed_password = get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_products(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Product).offset(skip).limit(limit).all()

def create_product(db: Session, product: schemas.ProductCreate):
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, product_id: int, product: schemas.ProductCreate):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        return None
    for key, value in product.dict().items():
        setattr(db_product, key, value)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def delete_product(db: Session, product_id: int):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        return False
    db.delete(db_product)
    db.commit()
    return True

def get_partners(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Partner).offset(skip).limit(limit).all()

def create_partner(db: Session, partner: schemas.PartnerCreate):
    db_partner = models.Partner(**partner.dict())
    db.add(db_partner)
    db.commit()
    db.refresh(db_partner)
    return db_partner

def update_partner(db: Session, partner_id: int, partner: schemas.PartnerCreate):
    db_partner = db.query(models.Partner).filter(models.Partner.id == partner_id).first()
    if not db_partner:
        return None
    for key, value in partner.dict().items():
        setattr(db_partner, key, value)
    db.add(db_partner)
    db.commit()
    db.refresh(db_partner)
    return db_partner

def delete_partner(db: Session, partner_id: int):
    db_partner = db.query(models.Partner).filter(models.Partner.id == partner_id).first()
    if not db_partner:
        return False
    db.delete(db_partner)
    db.commit()
    return True

def get_transactions(db: Session, skip: int = 0, limit: int = 100):
    # Eager load items and partner
    return db.query(models.Transaction).offset(skip).limit(limit).all()

def create_transaction(db: Session, transaction: schemas.TransactionCreate):

    # Calculate Subtotal
    subtotal = 0
    for item in transaction.items:
        subtotal += item.price * item.quantity
    vat_percent = getattr(transaction, 'vat_percent', 0) or 0
    total = subtotal + (subtotal * vat_percent / 100)

    db_transaction = models.Transaction(
        type=transaction.type,
        partner_id=transaction.partner_id,
        total_amount=total,
        vat_percent=vat_percent
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    for item in transaction.items:
        db_item = models.TransactionItem(
            transaction_id=db_transaction.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price
        )
        db.add(db_item)
        
        # Update Stock
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if product:
            if transaction.type == models.TransactionType.PURCHASE.value:
                product.stock_quantity += item.quantity
            elif transaction.type == models.TransactionType.SALE.value:
                if product.stock_quantity < item.quantity:
                    raise Exception(f"Not enough stock for product {product.name}")
                product.stock_quantity -= item.quantity
        
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def get_dashboard_stats(db: Session):
    total_customers = db.query(models.Partner).filter(models.Partner.type == models.PartnerType.CUSTOMER).count()
    total_products = db.query(models.Product).count()
    total_sales = db.query(func.sum(models.Transaction.total_amount)).filter(models.Transaction.type == models.TransactionType.SALE).scalar() or 0
    low_stock = db.query(models.Product).filter(models.Product.stock_quantity < models.Product.min_stock_level).count()
    
    # Recent sales
    recent_sales = db.query(models.Transaction).filter(models.Transaction.type == models.TransactionType.SALE).order_by(models.Transaction.date.desc()).limit(5).all()

    # Top selling products (simplified: count of times sold, really should be sum of quantity)
    # This query sums quantity per product for sales
    top_products_query = db.query(models.Product.name, func.sum(models.TransactionItem.quantity).label('total_qty'))\
        .join(models.TransactionItem, models.Product.id == models.TransactionItem.product_id)\
        .join(models.Transaction, models.TransactionItem.transaction_id == models.Transaction.id)\
        .filter(models.Transaction.type == models.TransactionType.SALE)\
        .group_by(models.Product.name)\
        .order_by(func.sum(models.TransactionItem.quantity).desc())\
        .limit(5).all()
    
    top_products = [{"name": name, "value": qty} for name, qty in top_products_query]

    # Top customers by revenue
    top_customers_query = db.query(models.Partner.name, func.sum(models.Transaction.total_amount).label('total_spent'))\
        .join(models.Transaction, models.Partner.id == models.Transaction.partner_id)\
        .filter(models.Transaction.type == models.TransactionType.SALE)\
        .group_by(models.Partner.name)\
        .order_by(func.sum(models.Transaction.total_amount).desc())\
        .limit(5).all()

    top_customers = [{"name": name, "value": total} for name, total in top_customers_query]

    return {
        "total_customers": total_customers,
        "total_products": total_products,
        "total_sales": total_sales,
        "low_stock_items": low_stock,
        "recent_sales": recent_sales,
        "top_products": top_products,
        "top_customers": top_customers
    }
