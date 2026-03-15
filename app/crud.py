from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, extract, String, cast
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
    # Remove global VAT
    db_transaction.sales_person = transaction.sales_person
    db_transaction.payment_method = transaction.payment_method or "Cash"
    # Recalculate total
    subtotal = 0
    total_discount = 0
    total_vat = 0
    for item in transaction.items:
        item_total = item.price * item.quantity
        item_discount = getattr(item, 'discount', 0) or 0
        item_vat_percent = getattr(item, 'vat_percent', 0) or 0
        item_amt_after_disc = item_total - item_discount
        item_vat = item_amt_after_disc * (item_vat_percent / 100)
        subtotal += item_amt_after_disc
        total_discount += item_discount
        total_vat += item_vat
        # Selling price validation for sales
        # Old selling price logic removed
    total = subtotal + total_vat
    db_transaction.total_amount = total
    db.commit()
    # Add new items
    for item in transaction.items:
        db_item = models.TransactionItem(
            transaction_id=transaction_id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price,
            discount=getattr(item, 'discount', 0) or 0,
            vat_percent=getattr(item, 'vat_percent', 0) or 0
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
    total = db.query(models.Category).count()
    items = db.query(models.Category).offset(skip).limit(limit).all()
    return items, total

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
from sqlalchemy import or_

def get_products(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = None,
    name: Optional[str] = None,
    sku: Optional[str] = None,
    category_id: Optional[int] = None
):
    query = db.query(models.Product).options(
        joinedload(models.Product.category)
    )
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                models.Product.name.ilike(search_pattern),
                models.Product.sku.ilike(search_pattern),
                models.Product.description.ilike(search_pattern)
            )
        )
    if name:
        query = query.filter(models.Product.name.ilike(f"%{name}%"))
    if sku:
        query = query.filter(models.Product.sku.ilike(f"%{sku}%"))
    if category_id:
        query = query.filter(models.Product.category_id == category_id)

    total = query.count()
    if skip is not None:
        query = query.offset(skip)
    if limit is not None:
        query = query.limit(limit)
    return query.all(), total

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

def get_partners(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    partner_type: Optional[str] = None,
    search: Optional[str] = None,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None
):
    query = db.query(models.Partner)
    if partner_type:
        query = query.filter(models.Partner.type == partner_type)
        
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                models.Partner.name.ilike(search_pattern),
                models.Partner.email.ilike(search_pattern),
                models.Partner.phone.ilike(search_pattern),
                models.Partner.address.ilike(search_pattern)
            )
        )
    if name:
        query = query.filter(models.Partner.name.ilike(f"%{name}%"))
    if email:
        query = query.filter(models.Partner.email.ilike(f"%{email}%"))
    if phone:
        query = query.filter(models.Partner.phone.ilike(f"%{phone}%"))
    if address:
        query = query.filter(models.Partner.address.ilike(f"%{address}%"))
        
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return items, total

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

def get_transactions(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    base_query=None,
    search: Optional[str] = None
):
    # Eager load items, partner, and product details
    from sqlalchemy.orm import joinedload
    query = base_query if base_query is not None else db.query(models.Transaction)
    
    if search:
        # Search by transaction ID, partner name, SKU, or PRODUCT NAME
        search_pattern = f"%{search}%"
        query = query.outerjoin(models.Partner)\
                     .outerjoin(models.Transaction.items)\
                     .outerjoin(models.TransactionItem.product).filter(
            or_(
                cast(models.Transaction.id, String).ilike(search_pattern),
                models.Partner.name.ilike(search_pattern),
                models.Product.name.ilike(search_pattern),
                models.Product.sku.ilike(search_pattern)
            )
        ).distinct()
        
    total = query.count()
    # Apply ordering before pagination
    query = query.order_by(models.Transaction.date.desc())
    # Eager load items and their products, and partner
    query = query.options(
        joinedload(models.Transaction.items).joinedload(models.TransactionItem.product),
        joinedload(models.Transaction.partner)
    )
    transactions = query.offset(skip).limit(limit).all()
    # Force loading of product for each item (workaround for lazy loading issues)
    for tx in transactions:
        for item in tx.items:
            _ = item.product  # Access to force load
    return transactions, total

def create_ledger_entry(db: Session, partner_id: int, amount: float, type: str, transaction_id: Optional[int] = None, payment_id: Optional[int] = None, description: Optional[str] = None):
    db_entry = models.LedgerEntry(
        partner_id=partner_id,
        transaction_id=transaction_id,
        payment_id=payment_id,
        amount=amount,
        type=type,
        description=description
    )
    db.add(db_entry)
    return db_entry

def create_transaction(db: Session, transaction: schemas.TransactionCreate):

    # Calculate Subtotal (price × qty - discount per item)
    subtotal = 0
    total_discount = 0
    total_vat = 0
    for item in transaction.items:
        item_total = item.price * item.quantity
        item_discount = getattr(item, 'discount', 0) or 0
        item_vat_percent = getattr(item, 'vat_percent', 0) or 0
        item_amt_after_disc = item_total - item_discount
        item_vat = item_amt_after_disc * (item_vat_percent / 100)
        subtotal += item_amt_after_disc
        total_discount += item_discount
        total_vat += item_vat
        # Selling price validation for sales
        # Old selling price logic removed
    total = subtotal + total_vat

    db_transaction = models.Transaction(
        type=transaction.type,
        partner_id=transaction.partner_id,
        total_amount=total,
        sales_person=transaction.sales_person,
        payment_method=transaction.payment_method or "Cash"
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
            discount=getattr(item, 'discount', 0) or 0,
            vat_percent=getattr(item, 'vat_percent', 0) or 0
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
        
    # Handle initial payment
    amount_paid = getattr(transaction, 'amount_paid', 0.0) or 0.0
    db_transaction.amount_paid = amount_paid
    if amount_paid >= db_transaction.total_amount:
        db_transaction.payment_status = models.PaymentStatus.PAID.value
    elif amount_paid > 0:
        db_transaction.payment_status = models.PaymentStatus.PARTIAL.value
    else:
        db_transaction.payment_status = models.PaymentStatus.UNPAID.value
        
    if amount_paid > 0:
        db_payment = models.Payment(
            transaction_id=db_transaction.id,
            partner_id=db_transaction.partner_id,
            amount=amount_paid,
            payment_method=db_transaction.payment_method, # Legacy
            channel=transaction.payment_channel or models.PaymentChannel.CASH.value,
            reference_id=transaction.payment_reference
        )
        db.add(db_payment)
        db.flush() # Get payment ID

    # --- Ledger Bookkeeping ---
    # 1. Record the full invoice amount
    if db_transaction.type == models.TransactionType.SALE.value:
        create_ledger_entry(db, db_transaction.partner_id, db_transaction.total_amount, models.LedgerEntryType.DEBIT.value, transaction_id=db_transaction.id, description=f"Sale Invoice #{db_transaction.id}")
        # 2. Record the payment if any
        if amount_paid > 0:
            create_ledger_entry(db, db_transaction.partner_id, amount_paid, models.LedgerEntryType.CREDIT.value, transaction_id=db_transaction.id, payment_id=db_payment.id, description=f"Payment Received for Sale #{db_transaction.id}")
    elif db_transaction.type == models.TransactionType.PURCHASE.value:
        create_ledger_entry(db, db_transaction.partner_id, db_transaction.total_amount, models.LedgerEntryType.CREDIT.value, transaction_id=db_transaction.id, description=f"Purchase Invoice #{db_transaction.id}")
        # 2. Record the payment if any
        if amount_paid > 0:
            create_ledger_entry(db, db_transaction.partner_id, amount_paid, models.LedgerEntryType.DEBIT.value, transaction_id=db_transaction.id, payment_id=db_payment.id, description=f"Payment Sent for Purchase #{db_transaction.id}")
        
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
def record_payment(db: Session, payment: schemas.PaymentCreate):
    db_payment = models.Payment(**payment.dict())
    db.add(db_payment)
    
    # Update transaction
    transaction = db.query(models.Transaction).filter(models.Transaction.id == payment.transaction_id).first()
    if transaction:
        transaction.amount_paid += payment.amount
        if transaction.amount_paid >= transaction.total_amount:
            transaction.payment_status = models.PaymentStatus.PAID.value
        elif transaction.amount_paid > 0:
            transaction.payment_status = models.PaymentStatus.PARTIAL.value
        else:
            transaction.payment_status = models.PaymentStatus.UNPAID.value
            
        # --- Ledger Bookkeeping ---
        description = payment.notes or f"Payment for {transaction.type} #{transaction.id}"
        if transaction.type == models.TransactionType.SALE.value:
            create_ledger_entry(db, transaction.partner_id, payment.amount, models.LedgerEntryType.CREDIT.value, transaction_id=transaction.id, payment_id=db_payment.id, description=description)
        else:
            create_ledger_entry(db, transaction.partner_id, payment.amount, models.LedgerEntryType.DEBIT.value, transaction_id=transaction.id, payment_id=db_payment.id, description=description)

    db.commit()
    db.refresh(db_payment)
    return db_payment

def reset_transaction_payment(db: Session, transaction_id: int):
    """Reset all payments for a transaction — deletes Payment records,
    their related LedgerEntry records, and resets the transaction to unpaid."""
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id
    ).first()
    if not transaction:
        return None

    # 1. Delete ledger entries linked to payments for this transaction
    db.query(models.LedgerEntry).filter(
        models.LedgerEntry.transaction_id == transaction_id,
        models.LedgerEntry.payment_id != None  # noqa: E711 — only payment-related entries
    ).delete(synchronize_session='fetch')

    # 2. Delete all payment records for this transaction
    db.query(models.Payment).filter(
        models.Payment.transaction_id == transaction_id
    ).delete(synchronize_session='fetch')

    # 3. Reset the transaction itself
    transaction.amount_paid = 0.0
    transaction.payment_status = models.PaymentStatus.UNPAID.value

    db.commit()
    db.refresh(transaction)
    return transaction

def get_accounts_summary(db: Session):
    from sqlalchemy import func

    # Receivables = sum of (total_amount - amount_paid) for all SALE transactions
    # This is always accurate regardless of ledger entry state
    total_receivables = db.query(
        func.coalesce(
            func.sum(models.Transaction.total_amount - models.Transaction.amount_paid), 0
        )
    ).filter(
        models.Transaction.type == models.TransactionType.SALE.value,
        models.Transaction.payment_status.in_([
            models.PaymentStatus.UNPAID.value,
            models.PaymentStatus.PARTIAL.value
        ])
    ).scalar() or 0.0

    # Payables = sum of (total_amount - amount_paid) for all PURCHASE transactions
    total_payables = db.query(
        func.coalesce(
            func.sum(models.Transaction.total_amount - models.Transaction.amount_paid), 0
        )
    ).filter(
        models.Transaction.type == models.TransactionType.PURCHASE.value,
        models.Transaction.payment_status.in_([
            models.PaymentStatus.UNPAID.value,
            models.PaymentStatus.PARTIAL.value
        ])
    ).scalar() or 0.0

    return {
        "total_receivables": total_receivables,
        "total_payables": total_payables
    }

def get_partner_balance_at_date(db: Session, partner_id: int, target_date):
    """Calculate how much a partner owes (positive) or is owed (negative) before a given date.
    Computed from the transactions table directly so it works even for
    old transactions that have no ledger entries."""
    from sqlalchemy import func

    # Sum of unpaid amounts for SALES to this partner before target_date
    receivable = db.query(
        func.coalesce(
            func.sum(models.Transaction.total_amount - models.Transaction.amount_paid), 0
        )
    ).filter(
        models.Transaction.partner_id == partner_id,
        models.Transaction.type == models.TransactionType.SALE.value,
        models.Transaction.date < target_date
    ).scalar() or 0.0

    # Sum of unpaid amounts for PURCHASES from this partner before target_date
    payable = db.query(
        func.coalesce(
            func.sum(models.Transaction.total_amount - models.Transaction.amount_paid), 0
        )
    ).filter(
        models.Transaction.partner_id == partner_id,
        models.Transaction.type == models.TransactionType.PURCHASE.value,
        models.Transaction.date < target_date
    ).scalar() or 0.0

    # Positive = partner owes us (receivable), negative = we owe partner (payable)
    return float(receivable) - float(payable)

def get_partner_statement(db: Session, partner_id: int):
    # Fetch all ledger entries for a partner, ordered by date
    # Secondary sort: type DESC puts 'debit' before 'credit' (invoice before payment)
    # Tertiary sort: id ASC for consistent ordering of same-date, same-type entries
    entries = db.query(models.LedgerEntry).filter(
        models.LedgerEntry.partner_id == partner_id
    ).order_by(
        models.LedgerEntry.date.asc(),
        models.LedgerEntry.type.desc(),
        models.LedgerEntry.id.asc()
    ).all()
    
    # Calculate running balance
    statement = []
    running_balance = 0.0
    for entry in entries:
        if entry.type == models.LedgerEntryType.DEBIT.value:
            running_balance += entry.amount
        else:
            running_balance -= entry.amount
        
        statement.append({
            "id": entry.id,
            "date": entry.date,
            "type": entry.type,
            "amount": entry.amount,
            "balance": running_balance,
            "description": entry.description,
            "transaction_id": entry.transaction_id,
            "payment_id": entry.payment_id
        })
    
    return statement[::-1] # Return most recent first
