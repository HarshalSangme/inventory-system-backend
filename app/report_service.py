import pandas as pd
import io
from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime
from typing import Optional

def get_stock_report_df(db: Session, search: Optional[str] = None):
    from .crud import get_products
    products, _ = get_products(db, skip=None, limit=None, search=search)
    
    data = []
    for p in products:
        data.append({
            'Product Name': p.name.upper(),
            'SKU': p.sku,
            'Category': p.category.name.upper() if p.category else '-',
            'Stock Quantity': p.stock_quantity,
            'Unit Cost': p.cost_price,
            'Unit Retail': p.price,
            'Stock Value (Cost)': p.stock_quantity * p.cost_price,
            'Stock Value (Retail)': p.stock_quantity * p.price,
            'Status': 'Low Stock' if p.stock_quantity < p.min_stock_level else 'In Stock'
        })
    return pd.DataFrame(data)

def get_sales_report_df(db: Session, from_date: Optional[str] = None, to_date: Optional[str] = None, search: Optional[str] = None):
    from .crud import get_transactions
    
    query = db.query(models.Transaction).filter(models.Transaction.type == 'sale')
    if from_date:
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            query = query.filter(models.Transaction.date >= from_dt)
        except: pass
    if to_date:
        try:
            to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(models.Transaction.date <= to_dt)
        except: pass
        
    transactions, _ = get_transactions(db, skip=None, limit=None, base_query=query, search=search)
    
    data = []
    idx = 1
    for t in transactions:
        partner_name = t.partner.name if t.partner else 'Unknown'
        for item in t.items:
            gross = item.price * item.quantity
            discount = item.discount or 0.0
            amt_after_disc = gross - discount
            vat_percent = item.vat_percent or 0.0
            vat = amt_after_disc * (vat_percent / 100.0)
            net_amt = amt_after_disc + vat

            data.append({
                'Sr. No.': idx,
                'Date': t.date.strftime("%Y-%m-%d %H:%M"),
                'Customer': partner_name,
                'SKU Code': item.product.sku if item.product else '-',
                'Item Name': item.product.name.upper() if item.product else '-',
                'Gross Amount': round(gross, 3),
                'Discount': round(discount, 3),
                'VAT': round(vat, 3),
                'Net Amount': round(net_amt, 3),
                'Payment Method': t.payment_method or '-',
                'Sales Person': t.sales_person or '-',
                'Status': 'Completed'
            })
            idx += 1
            
    return pd.DataFrame(data)

def get_purchase_report_df(db: Session, from_date: Optional[str] = None, to_date: Optional[str] = None, search: Optional[str] = None):
    from .crud import get_transactions
    
    query = db.query(models.Transaction).filter(models.Transaction.type == 'purchase')
    if from_date:
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            query = query.filter(models.Transaction.date >= from_dt)
        except: pass
    if to_date:
        try:
            to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(models.Transaction.date <= to_dt)
        except: pass
        
    transactions, _ = get_transactions(db, skip=None, limit=None, base_query=query, search=search)
    
    data = []
    for t in transactions:
        partner_name = t.partner.name if t.partner else 'Unknown'
        data.append({
            'Date': t.date.strftime("%Y-%m-%d"),
            'Vendor': partner_name,
            'Total Amount': t.total_amount,
            'VAT %': t.vat_percent or 0,
            'Items Count': len(t.items)
        })
    return pd.DataFrame(data)

def get_financial_report_df(db: Session, from_date: Optional[str] = None, to_date: Optional[str] = None):
    # Fetch all transactions or filtered by date
    query = db.query(models.Transaction)
    if from_date:
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            query = query.filter(models.Transaction.date >= from_dt)
        except: pass
    if to_date:
        try:
            to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(models.Transaction.date <= to_dt)
        except: pass
        
    transactions = query.all()
    sales = [t for t in transactions if t.type == 'sale']
    purchases = [t for t in transactions if t.type == 'purchase']
    
    total_revenue = sum(t.total_amount for t in sales)
    total_cogs = 0
    for t in sales:
        for item in t.items:
            if item.product:
                total_cogs += item.quantity * item.product.cost_price
                
    profit = total_revenue - total_cogs
    margin = (profit / total_revenue * 100) if total_revenue > 0 else 0
    total_inventory_purchase = sum(t.total_amount for t in purchases)
    
    data = [{
        'Total Sales Revenue': total_revenue,
        'Total COGS': total_cogs,
        'Gross Profit': profit,
        'Profit Margin %': margin,
        'Sales Transactions': len(sales),
        'Inventory Purchases': total_inventory_purchase
    }]
    return pd.DataFrame(data)

def export_df_to_excel(df: pd.DataFrame):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Report')
    output.seek(0)
    return output

def export_df_to_csv(df: pd.DataFrame):
    output = io.BytesIO()
    csv_data = df.to_csv(index=False).encode('utf-8')
    output.write(csv_data)
    output.seek(0)
    return output
