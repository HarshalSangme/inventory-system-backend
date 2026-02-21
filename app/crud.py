from sqlalchemy.orm import Session
from . import schemas, models

def update_transaction(db: Session, transaction_id: int, transaction: schemas.TransactionCreate):
    db_transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not db_transaction:
        return None
    # Remove old items
    db.query(models.TransactionItem).filter(models.TransactionItem.transaction_id == transaction_id).delete()
    db.commit()
    # Update transaction fields
    db_transaction.type = transaction.type
    db_transaction.partner_id = transaction.partner_id
    db_transaction.vat_percent = transaction.vat_percent
    db_transaction.sales_person = transaction.sales_person
    # Recalculate total
    subtotal = 0
    total_discount = 0
    for item in transaction.items:
        item_total = item.price * item.quantity
        item_discount = getattr(item, 'discount', 0) or 0
        subtotal += item_total - item_discount
        total_discount += item_discount
        # Selling price validation for sales
        if transaction.type == models.TransactionType.SALE.value:
            product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
            if product and item.price < product.cost_price:
                raise ValueError(f"Selling price ({item.price}) cannot be less than cost price ({product.cost_price}) for product '{product.name}'.")
    vat_percent = transaction.vat_percent or 0
    total = subtotal + (subtotal * vat_percent / 100)
    db_transaction.total_amount = total
    db.commit()
    # Add new items
    for item in transaction.items:
        db_item = models.TransactionItem(
            transaction_id=transaction_id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price,
            discount=getattr(item, 'discount', 0) or 0
        )
        db.add(db_item)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def delete_transaction(db: Session, transaction_id: int):
    db_transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not db_transaction:
        return False
    # Delete items first
    db.query(models.TransactionItem).filter(models.TransactionItem.transaction_id == transaction_id).delete()
    db.delete(db_transaction)
    db.commit()
    return True

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from . import models, schemas
from passlib.context import CryptContext

def update_user(db: Session, user_id: int, user: schemas.UserUpdate):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return None
    if user.username is not None:
        db_user.username = user.username
    if user.password:
        db_user.hashed_password = get_password_hash(user.password)
    if user.role is not None:
        db_user.role = user.role
    db.commit()
    db.refresh(db_user)
    return db_user

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_categories(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Category).offset(skip).limit(limit).all()

def create_category(db: Session, category: schemas.CategoryCreate):
    db_category = models.Category(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

def update_category(db: Session, category_id: int, category: schemas.CategoryCreate):
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_category:
        return None
    for key, value in category.dict().items():
        setattr(db_category, key, value)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

def delete_category(db: Session, category_id: int):
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_category:
        return False
    db.delete(db_category)
    db.commit()
    return True
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


from sqlalchemy.orm import joinedload

def get_products(db: Session, skip: int = 0, limit: int = None):
    query = db.query(models.Product).options(
        joinedload(models.Product.category)
    ).offset(skip)
    if limit is not None:
        query = query.limit(limit)
    return query.all()

def create_product(db: Session, product: schemas.ProductCreate):
    # Ensure SKU is unique
    sku = product.sku
    base_sku = sku
    counter = 1
    while db.query(models.Product).filter(models.Product.sku == sku).first():
        sku = f"{base_sku}-{counter}"
        counter += 1
    product_dict = product.dict()
    product_dict["sku"] = sku
    db_product = models.Product(**product_dict)
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

def delete_products_bulk(db: Session, product_ids: List[int]):
    try:
        deleted_count = db.query(models.Product).filter(models.Product.id.in_(product_ids)).delete(synchronize_session=False)
        db.commit()
        return deleted_count
    except Exception as e:
        db.rollback()
        raise e

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

    # Calculate Subtotal (price × qty - discount per item)
    subtotal = 0
    total_discount = 0
    for item in transaction.items:
        item_total = item.price * item.quantity
        item_discount = getattr(item, 'discount', 0) or 0
        subtotal += item_total - item_discount
        total_discount += item_discount
        # Selling price validation for sales
        if transaction.type == models.TransactionType.SALE.value:
            product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
            if product and item.price < product.cost_price:
                raise ValueError(f"Selling price ({item.price}) cannot be less than cost price ({product.cost_price}) for product '{product.name}'.")
    vat_percent = getattr(transaction, 'vat_percent', 0) or 0
    total = subtotal + (subtotal * vat_percent / 100)

    db_transaction = models.Transaction(
        type=transaction.type,
        partner_id=transaction.partner_id,
        total_amount=total,
        vat_percent=vat_percent,
        sales_person=transaction.sales_person
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    for item in transaction.items:
        db_item = models.TransactionItem(
            transaction_id=db_transaction.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price,
            discount=getattr(item, 'discount', 0) or 0
        )
        db.add(db_item)
        
        # Update Stock
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if product:
            if transaction.type == models.TransactionType.PURCHASE.value:
                product.stock_quantity += item.quantity
            elif transaction.type == models.TransactionType.SALE.value:
                if product.stock_quantity < item.quantity:
                    raise ValueError(f"Not enough stock for product {product.name}. Available: {product.stock_quantity}, Requested: {item.quantity}")
                product.stock_quantity -= item.quantity

        
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def get_dashboard_stats(db: Session):
    total_customers = db.query(models.Partner).filter(models.Partner.type == models.PartnerType.CUSTOMER).count()
    total_products = db.query(models.Product).count()
    total_sales = db.query(func.sum(models.Transaction.total_amount)).filter(models.Transaction.type == models.TransactionType.SALE).scalar() or 0
    low_stock = db.query(models.Product).filter(models.Product.stock_quantity < models.Product.min_stock_level).count()

    # Total stock value (cost)
    total_stock_value = db.query(func.sum(models.Product.stock_quantity * models.Product.cost_price)).scalar() or 0

    # Total retail value
    total_retail_value = db.query(func.sum(models.Product.stock_quantity * models.Product.price)).scalar() or 0

    # Top 10 products by current stock
    top_stock_products_query = db.query(
        models.Product.name,
        models.Product.stock_quantity,
        models.Product.min_stock_level
    ).order_by(models.Product.stock_quantity.desc()).limit(10).all()
    top_stock_products = [
        {
            "name": name,
            "stock_quantity": stock_quantity,
            "min_stock_level": min_stock_level
        }
        for name, stock_quantity, min_stock_level in top_stock_products_query
    ]

    # Recent sales
    recent_sales = db.query(models.Transaction).filter(models.Transaction.type == models.TransactionType.SALE).order_by(models.Transaction.date.desc()).limit(5).all()

    # Top selling products (by quantity sold)
    top_products_query = (
        db.query(models.Product.name, func.sum(models.TransactionItem.quantity).label('total_qty'))
        .join(models.TransactionItem, models.Product.id == models.TransactionItem.product_id)
        .join(models.Transaction, models.TransactionItem.transaction_id == models.Transaction.id)
        .filter(models.Transaction.type == models.TransactionType.SALE)
        .group_by(models.Product.name)
        .order_by(func.sum(models.TransactionItem.quantity).desc())
        .limit(5)
        .all()
    )
    top_products = [{"name": name, "value": qty} for name, qty in top_products_query]

    # Top customers by revenue
    top_customers_query = (
        db.query(models.Partner.name, func.sum(models.Transaction.total_amount).label('total_spent'))
        .join(models.Transaction, models.Partner.id == models.Transaction.partner_id)
        .filter(models.Transaction.type == models.TransactionType.SALE)
        .group_by(models.Partner.name)
        .order_by(func.sum(models.Transaction.total_amount).desc())
        .limit(5)
        .all()
    )
    top_customers = [{"name": name, "value": total} for name, total in top_customers_query]

    return {
        "total_customers": total_customers,
        "total_products": total_products,
        "total_sales": total_sales,
        "low_stock_items": low_stock,
        "total_stock_value": total_stock_value,
        "total_retail_value": total_retail_value,
        "top_stock_products": top_stock_products,
        "recent_sales": recent_sales,
        "top_products": top_products,
        "top_customers": top_customers
    }
