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
            
    # Add a Total row at the bottom
    if data:
        total_gross = sum(row['Gross Amount'] for row in data)
        total_discount = sum(row['Discount'] for row in data)
        total_vat = sum(row['VAT'] for row in data)
        total_net = sum(row['Net Amount'] for row in data)
        
        data.append({
            'Sr. No.': '',
            'Date': '',
            'Customer': '',
            'SKU Code': '',
            'Item Name': 'TOTAL',
            'Gross Amount': round(total_gross, 3),
            'Discount': round(total_discount, 3),
            'VAT': round(total_vat, 3),
            'Net Amount': round(total_net, 3),
            'Payment Method': '',
            'Sales Person': '',
            'Status': ''
        })
            
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

def get_category_profit_data(db: Session, from_date: Optional[str] = None, to_date: Optional[str] = None, search: Optional[str] = None):
    from sqlalchemy import func
    from datetime import datetime
    
    # 1. Sales revenue and COGS grouped by category
    sales_query = db.query(
        models.Category.name.label('category_name'),
        func.sum((models.TransactionItem.quantity * models.TransactionItem.price) - models.TransactionItem.discount).label('sales_revenue'),
        func.sum(models.TransactionItem.quantity * models.Product.cost_price).label('cogs')
    ).select_from(models.TransactionItem)\
     .join(models.Transaction)\
     .join(models.Product)\
     .outerjoin(models.Category)\
     .filter(models.Transaction.type == 'sale')

    if from_date:
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            sales_query = sales_query.filter(models.Transaction.date >= from_dt)
        except: pass
    if to_date:
        try:
            to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            sales_query = sales_query.filter(models.Transaction.date <= to_dt)
        except: pass
        
    sales_query = sales_query.group_by(models.Category.name)
    sales_data = sales_query.all()
    
    # 2. Total stock in hand grouped by category
    stock_query = db.query(
        models.Category.name.label('category_name'),
        func.sum(models.Product.stock_quantity * models.Product.cost_price).label('stock_value')
    ).select_from(models.Product)\
     .outerjoin(models.Category)\
     .group_by(models.Category.name)
     
    stock_data = stock_query.all()
    
    # Merge data cleanly
    merged_data = {}
    
    for row in stock_data:
        cat_name = row.category_name or 'Uncategorized'
        merged_data[cat_name] = {
            'Category': cat_name,
            'Sales Revenue': 0.0,
            'Total COGS': 0.0,
            'Gross Profit': 0.0,
            'Profit Margin %': 0.0,
            'Total STOCK IN HAND': float(row.stock_value or 0.0)
        }
        
    for row in sales_data:
        cat_name = row.category_name or 'Uncategorized'
        if cat_name not in merged_data:
            merged_data[cat_name] = {
                'Category': cat_name,
                'Sales Revenue': 0.0,
                'Total COGS': 0.0,
                'Gross Profit': 0.0,
                'Profit Margin %': 0.0,
                'Total STOCK IN HAND': 0.0
            }
            
        revenue = float(row.sales_revenue or 0.0)
        cogs = float(row.cogs or 0.0)
        profit = revenue - cogs
        margin = (profit / revenue * 100) if revenue > 0 else 0.0
        
        merged_data[cat_name]['Sales Revenue'] = round(revenue, 3)
        merged_data[cat_name]['Total COGS'] = round(cogs, 3)
        merged_data[cat_name]['Gross Profit'] = round(profit, 3)
        merged_data[cat_name]['Profit Margin %'] = round(margin, 2)
        
    result_list = list(merged_data.values())
    
    if search:
        search_lower = search.lower()
        result_list = [r for r in result_list if search_lower in r['Category'].lower()]
        
    result_list.sort(key=lambda x: x['Sales Revenue'], reverse=True)
    return result_list

def get_financial_report_df(db: Session, from_date: Optional[str] = None, to_date: Optional[str] = None):
    # Retrieve the new optimized category data
    result_list = get_category_profit_data(db, from_date, to_date)
    
    # Add Grand Totals to the export
    if result_list:
        total_revenue = sum(r['Sales Revenue'] for r in result_list)
        total_cogs = sum(r['Total COGS'] for r in result_list)
        total_profit = sum(r['Gross Profit'] for r in result_list)
        total_stock = sum(r['Total STOCK IN HAND'] for r in result_list)
        total_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0.0
        
        result_list.append({
            'Category': 'GRAND TOTAL',
            'Sales Revenue': round(total_revenue, 3),
            'Total COGS': round(total_cogs, 3),
            'Gross Profit': round(total_profit, 3),
            'Profit Margin %': round(total_margin, 2),
            'Total STOCK IN HAND': round(total_stock, 3)
        })
        
    # Return matched directly to client's requested DataFrame columns
    export_data = []
    for r in result_list:
        export_data.append({
            'SALES REVENUE - CATEGORY WISE ( WITH TOTAL AMT )': r['Category'],
            'Total Sales Revenue': r['Sales Revenue'],
            'COGS CATEGORY WISE (WITH TOTAL AMT)': r['Category'],
            'Total COGS': r['Total COGS'],
            'Gross Profit': r['Gross Profit'],
            'Profit Margin %': r['Profit Margin %'],
            'STOCK CATEGORY WISE (WITH TOTAL AMT)': r['Category'],
            'Total STOCK IN HAND': r['Total STOCK IN HAND']
        })
        
    return pd.DataFrame(export_data)

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
