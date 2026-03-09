"""
Invoice PDF Generator using ReportLab
Generates professional invoices matching the JOT Auto Parts W.L.L template
"""
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import os

# Page dimensions
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_LEFT = 10 * mm
MARGIN_RIGHT = 10 * mm
MARGIN_TOP = 12 * mm
MARGIN_BOTTOM = 12 * mm
CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT

# Colors
BLACK = colors.black
WHITE = colors.white
GRAY_DARK = colors.Color(0.37, 0.37, 0.37)
GRAY_LIGHT = colors.Color(0.94, 0.94, 0.94)
ORANGE = colors.Color(0.85, 0.42, 0)

# Bank details
BANK_DETAILS = {
    'name': 'JOT AUTO PARTS W.L.L',
    'bank': 'Bahrain Islamic Bank (BisB)',
    'iban': 'BH49BISB00010002015324',
}

# Styles for wrapped table content
CELL_STYLE = ParagraphStyle(
    'CellStyle',
    fontName='Helvetica',
    fontSize=6.5,
    leading=8,
    alignment=TA_LEFT,
)

SKU_STYLE = ParagraphStyle(
    'SKUStyle',
    fontName='Helvetica',
    fontSize=6,
    leading=7,
    alignment=TA_LEFT,
)

def get_wrapped_height(text, width, style):
    """Calculate height of wrapped text given a width and style"""
    if not text:
        return 0
    p = Paragraph(str(text), style)
    _, h = p.wrap(width, 1000) # Using 1000 as a very large max height
    return h

def number_to_words(num):
    """Convert number to words handling Bahraini Dinar (3 decimal places)"""
    def convert_int_to_words(n):
        ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
                'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
                'Seventeen', 'Eighteen', 'Nineteen']
        tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
        
        if n == 0:
            return ""
        
        if n < 20:
            return ones[int(n)]
        elif n < 100:
            return tens[int(n) // 10] + ('-' + ones[int(n) % 10] if n % 10 else '')
        elif n < 1000:
            return ones[int(n) // 100] + ' Hundred' + (' and ' + convert_int_to_words(n % 100) if n % 100 else '')
        elif n < 1000000:
            return convert_int_to_words(n // 1000) + ' Thousand' + (' ' + convert_int_to_words(n % 1000) if n % 1000 else '')
        else:
            return str(int(n))

    # Split into Dinar and Fils
    total_fils = int(round(num * 1000))
    bd = total_fils // 1000
    fils = total_fils % 1000
    
    bd_words = convert_int_to_words(bd) if bd > 0 else "Zero"
    fils_words = convert_int_to_words(fils) if fils > 0 else "Zero"
    
    # Format: Baharaini Dinar [WORDS] and Fils [WORDS] only
    result = f"BAHRAINI DINAR {bd_words} AND FILS {fils_words} ONLY"
        
    return result.upper()

def format_date(date_str):
    """Format date string to DD-MM-YYYY"""
    if not date_str:
        return ''
    try:
        if isinstance(date_str, str):
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            dt = date_str
        return dt.strftime('%d-%m-%Y')
    except:
        return str(date_str)

def generate_invoice_pdf(invoice_data: dict, edit_data: dict) -> BytesIO:
    """
    Generate invoice PDF from invoice data (supports multi-page)
    
    Args:
        invoice_data: Transaction data with items, customer info, etc.
        edit_data: Editable fields (invoice_number, payment_terms, due_date, sales_person)
    
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    
    # Create the PDF document
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Set Metadata Title
    doc_title = f"Invoice {edit_data.get('invoice_number', 'Untitled')}"
    c.setTitle(doc_title)
    
    # Static assets directory
    static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
    
    # Prepare items data
    items = invoice_data.get('items', [])
    total_gross = 0
    
    item_rows = []
    vat_percent_global = float(invoice_data.get('vat_percent', 0) or 0)
    total_gross = 0  # sum of price*qty (before discount)
    total_discount_all = 0  # sum of all per-item discounts
    total_amt_after_disc = 0  # sum of (price*qty - discount)
    total_vat_all = 0  # sum of per-item VAT
    total_net_all = 0  # sum of per-item net amounts
    
    for idx, item in enumerate(items):
        price = float(item.get('price', 0) or 0)
        qty = float(item.get('quantity', 0) or 0)
        item_discount = float(item.get('discount', 0) or 0)
        gross = price * qty
        amt_after_disc = gross - item_discount
        item_vat = amt_after_disc * (vat_percent_global / 100) if vat_percent_global > 0 else 0
        net = amt_after_disc + item_vat
        
        total_gross += gross
        total_discount_all += item_discount
        total_amt_after_disc += amt_after_disc
        total_vat_all += item_vat
        total_net_all += net
        
        item_rows.append([
            str(idx + 1),
            str(item.get('product', {}).get('sku', '') or item.get('sku', '-')),
            str(item.get('product', {}).get('name', '') or item.get('name', '')),
            str(int(qty)),
            f'{price:.3f}',
            f'{item_discount:.3f}' if item_discount > 0 else '-',
            f'{amt_after_disc:.3f}',
            f'{vat_percent_global:.1f}' if vat_percent_global > 0 else '-',
            f'{item_vat:.3f}' if item_vat > 0 else '-',
            f'{net:.3f}',
        ])
    
    # Column headers and table layout
    headers = ['SR.NO', 'ITEM CODE', 'ITEM NAME', 'QTY', 'PRICE', 'DISCOUNT', 'AMT', '%', 'VAT', 'NET AMT']
    # Reduced NET AMT width, increased ITEM NAME
    base_widths = [30, 58, 155, 32, 60, 60, 55, 28, 55, 50]
    total_base = sum(base_widths)
    table_width = CONTENT_WIDTH
    col_widths = [w * table_width / total_base for w in base_widths]
    table_x = MARGIN_LEFT
    
    # Base row height
    MIN_ROW_HEIGHT = 16
    
    item_rows = []
    item_heights = []
    vat_percent_global = float(invoice_data.get('vat_percent', 0) or 0)
    total_gross = 0  # sum of price*qty (before discount)
    total_discount_all = 0  # sum of all per-item discounts
    total_amt_after_disc = 0  # sum of (price*qty - discount)
    total_vat_all = 0  # sum of per-item VAT
    total_net_all = 0  # sum of per-item net amounts
    
    for idx, item in enumerate(items):
        price = float(item.get('price', 0) or 0)
        qty = float(item.get('quantity', 0) or 0)
        item_discount = float(item.get('discount', 0) or 0)
        gross = price * qty
        amt_after_disc = gross - item_discount
        item_vat = amt_after_disc * (vat_percent_global / 100) if vat_percent_global > 0 else 0
        net = amt_after_disc + item_vat
        
        total_gross += gross
        total_discount_all += item_discount
        total_amt_after_disc += amt_after_disc
        total_vat_all += item_vat
        total_net_all += net
        
        sku = str(item.get('product', {}).get('sku', '') or item.get('sku', '-'))
        name = str(item.get('product', {}).get('name', '') or item.get('name', ''))
        
        # Calculate dynamic height for this row based on SKU and Name wrapping
        # Padding: 4pt top + 4pt bottom = 8pt
        sku_h = get_wrapped_height(sku, col_widths[1] - 6, SKU_STYLE) + 8
        name_h = get_wrapped_height(name, col_widths[2] - 6, CELL_STYLE) + 8
        row_h = max(MIN_ROW_HEIGHT, sku_h, name_h)
        item_heights.append(row_h)
        
        item_rows.append([
            str(idx + 1),
            sku,
            name,
            str(int(qty)),
            f'{price:.3f}',
            f'{item_discount:.3f}' if item_discount > 0 else '-',
            f'{amt_after_disc:.3f}',
            f'{vat_percent_global:.1f}' if vat_percent_global > 0 else '-',
            f'{item_vat:.3f}' if item_vat > 0 else '-',
            f'{net:.3f}',
        ])
    
    # ==================== LAYOUT CALCULATIONS ====================
    # Fixed positions from page bottom:
    # - Footer (image + bars): 0-116pt
    # - Signature labels: 131pt
    # - Stamp area: 131-211pt (80pt clear)  
    # - Thank You line: 95pt (Below signatures)
    # - Bank box: Moved to totals section (dynamic)
    
    fixed_bottom_section = 350  # Increased to fit 8-row totals box
    header_height = 140  
    table_header_height = MIN_ROW_HEIGHT
    
    # Calculate items that fit per page type
    page_height = height - MARGIN_TOP  # We draw footer at absolute 0
    
    # Page 1: Has header
    available_page_1 = page_height - header_height - table_header_height - fixed_bottom_section
    
    # Other pages: No header, just table continuing
    available_page_other = page_height - 20 - table_header_height - fixed_bottom_section  # 20pt margin at top
    
    # Calculate page distribution based on actual heights
    items_per_page = []
    current_page_items = 0
    current_page_height = 0
    
    is_first_page = True
    available_height = available_page_1
    
    for h in item_heights:
        if current_page_height + h > available_height:
            # Page is full
            if current_page_items == 0:
                # Force at least one item? (Shouldn't happen if available_height > MIN_ROW_HEIGHT)
                items_per_page.append(1)
                current_page_items = 0
                current_page_height = 0
            else:
                items_per_page.append(current_page_items)
                current_page_items = 1
                current_page_height = h
            
            is_first_page = False
            available_height = available_page_other
        else:
            current_page_items += 1
            current_page_height += h
            
    if current_page_items > 0:
        items_per_page.append(current_page_items)
    
    # If no items, ensure at least one page
    if not items_per_page:
        items_per_page = [0]
    
    total_pages = len(items_per_page)
    
    # Prepare customer info
    customer_name = invoice_data.get('partner', {}).get('name', '') or invoice_data.get('customer_name', '')
    customer_address = invoice_data.get('partner', {}).get('address', '') or invoice_data.get('address', '')
    customer_mobile = invoice_data.get('partner', {}).get('phone', '') or invoice_data.get('mobile', '')
    
    # Helper function to draw page number
    def draw_page_number(canvas_obj, page_num, total):
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.setFillColor(BLACK)
        canvas_obj.drawRightString(width - MARGIN_RIGHT, height - 10, f'Page {page_num} of {total}')
    
    # Helper function to draw table header
    def draw_table_header(canvas_obj, start_y):
        canvas_obj.setFillColor(GRAY_DARK)
        canvas_obj.rect(table_x, start_y - MIN_ROW_HEIGHT, table_width, MIN_ROW_HEIGHT, fill=1, stroke=1)
        
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont('Helvetica-Bold', 6)
        x = table_x
        for i, header in enumerate(headers):
            canvas_obj.drawCentredString(x + col_widths[i] / 2, start_y - MIN_ROW_HEIGHT + 5, header)
            x += col_widths[i]
        
        # Draw header vertical lines
        canvas_obj.setStrokeColor(WHITE)
        x = table_x
        for i in range(len(col_widths) - 1):
            x += col_widths[i]
            canvas_obj.line(x, start_y, x, start_y - MIN_ROW_HEIGHT)
        canvas_obj.setStrokeColor(BLACK)
        
        return start_y - MIN_ROW_HEIGHT  # Return data start y
    
    # Helper function to draw item rows
    def draw_item_rows(canvas_obj, start_y, items_to_draw, item_heights_to_draw, show_totals=False):
        data_start_y = start_y
        
        # Build display rows
        display_rows = items_to_draw.copy()
        display_heights = item_heights_to_draw.copy()
        actual_item_count = len(display_rows)
        
        if show_totals:
            # Add 8 rows for totals section
            for _ in range(8):
                display_rows.append([''] * 10)
                display_heights.append(MIN_ROW_HEIGHT)
        
        totals_start_row = actual_item_count if show_totals else len(display_rows)
        totals_box_width = col_widths[-1] + col_widths[-2]
        totals_x = table_x + table_width - totals_box_width
        
        # Draw outer table border
        total_table_height = sum(display_heights)
        canvas_obj.rect(table_x, data_start_y - total_table_height, table_width, total_table_height)
        
        # Calculate heights of actual content (items + totals if present)
        real_item_count = len(items_to_draw)
        item_section_height = sum(item_heights_to_draw)
        content_bottom_y = data_start_y - item_section_height
        
        x = table_x
        for i in range(len(col_widths) - 1):
            x += col_widths[i]
            
            # Draw line for the item section
            canvas_obj.line(x, data_start_y, x, content_bottom_y)
            
            if show_totals:
                # If we have totals, we might need lines in the totals section at the bottom?
                totals_top_y = data_start_y - item_section_height
                totals_bottom_y = data_start_y - total_table_height
                
                # Check if this column is part of the totals section
                if x >= totals_x:
                     canvas_obj.line(x, totals_top_y, x, totals_bottom_y)

        if show_totals:
            # Draw horizontal line above "Items sold" text
            items_sold_separator_y = data_start_y - item_section_height
            canvas_obj.line(table_x, items_sold_separator_y, table_x + table_width, items_sold_separator_y)
            
            # Draw horizontal lines in totals section
            current_y = data_start_y
            for r in range(len(display_rows)):
                h = display_heights[r]
                current_y -= h
                if r >= totals_start_row:
                    canvas_obj.line(totals_x, current_y, table_x + table_width, current_y)
            
            # Vertical line before totals (left side of totals box)
            canvas_obj.line(totals_x, data_start_y - item_section_height, totals_x, data_start_y - total_table_height)
        else:
             # If not showing totals (intermediate page), we might want a bottom line for the content?
             # Or just leave it open if it continues? 
             # Usually strictly closed box. 
             # If the user wants NO vertical lines in empty space, maybe they still want the box outline?
             # total_table_height covers the full height including padding.
             pass
        
        # Fill in item data
        canvas_obj.setFillColor(BLACK)
        current_y = data_start_y
        for row_idx, row in enumerate(display_rows):
            if show_totals and row_idx >= totals_start_row:
                continue
            
            h = display_heights[row_idx]
            row_y = current_y
            current_y -= h
            
            x = table_x
            for col_idx, cell in enumerate(row):
                if col_idx == 0:
                    canvas_obj.drawCentredString(x + col_widths[col_idx] / 2, current_y + (h - 6) / 2, cell)
                elif col_idx == 1: # SKU
                    p = Paragraph(cell, SKU_STYLE)
                    p.wrapOn(canvas_obj, col_widths[col_idx] - 6, h)
                    p.drawOn(canvas_obj, x + 3, current_y + 4)
                elif col_idx == 2: # ITEM NAME
                    p = Paragraph(cell, CELL_STYLE)
                    p.wrapOn(canvas_obj, col_widths[col_idx] - 6, h)
                    p.drawOn(canvas_obj, x + 3, current_y + 4)
                elif col_idx in [3, 4, 5, 6, 7, 8, 9]:
                    canvas_obj.setFont('Helvetica', 6)
                    canvas_obj.drawRightString(x + col_widths[col_idx] - 3, current_y + (h - 6) / 2, cell)
                x += col_widths[col_idx]
        
        return data_start_y - total_table_height, totals_start_row, totals_x, totals_box_width, sum(display_heights[:totals_start_row])
    
    # Helper function to draw totals section
    def draw_totals_section(canvas_obj, data_start_y, totals_start_row, totals_x, totals_box_width, items_height):
        previous_balance = float(invoice_data.get('previous_balance', 0) or 0)
        amount_paid = float(invoice_data.get('amount_paid', 0) or 0)
        total_due = total_net_all + previous_balance
        remaining_balance = total_due - amount_paid

        totals_label_width = totals_box_width * 0.55
        totals_value_x = totals_x + col_widths[-2]
        
        canvas_obj.setStrokeColor(BLACK)
        canvas_obj.line(totals_value_x, data_start_y - items_height,
                       totals_value_x, data_start_y - items_height - 8 * MIN_ROW_HEIGHT)
        
        totals_data_top = [
            ('GROSS AMT', f'{total_gross:.3f}'),
            ('DISCOUNT', f'{total_discount_all:.3f}' if total_discount_all > 0 else '-'),
            ('VAT AMT', f'{total_vat_all:.3f}' if total_vat_all > 0 else '-'),
        ]
        
        canvas_obj.setFont('Helvetica-Bold', 7)
        canvas_obj.setFillColor(BLACK)
        for i, (label, value) in enumerate(totals_data_top):
            row_y = data_start_y - items_height - i * MIN_ROW_HEIGHT
            canvas_obj.drawString(totals_x + 6, row_y - MIN_ROW_HEIGHT + 5, label)
            canvas_obj.drawRightString(table_x + table_width - 6, row_y - MIN_ROW_HEIGHT + 5, value)
        
        # NET AMT BHD row (highlighted)
        net_row_y = data_start_y - items_height - 3 * MIN_ROW_HEIGHT
        canvas_obj.setFillColor(GRAY_DARK)
        canvas_obj.rect(totals_x, net_row_y - MIN_ROW_HEIGHT, totals_box_width, MIN_ROW_HEIGHT, fill=1, stroke=1)
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont('Helvetica-Bold', 7)
        canvas_obj.drawString(totals_x + 6, net_row_y - MIN_ROW_HEIGHT + 5, 'NET AMT BHD:')
        canvas_obj.drawRightString(table_x + table_width - 6, net_row_y - MIN_ROW_HEIGHT + 5, f'{total_net_all:.3f}')
        
        totals_data_bottom = [
            ('PREV BAL', f'{previous_balance:.3f}'),
            ('TOTAL DUE', f'{total_due:.3f}'),
            ('PAID', f'{amount_paid:.3f}'),
        ]
        
        canvas_obj.setFillColor(BLACK)
        for i, (label, value) in enumerate(totals_data_bottom):
            row_y = data_start_y - items_height - (i + 4) * MIN_ROW_HEIGHT
            canvas_obj.drawString(totals_x + 6, row_y - MIN_ROW_HEIGHT + 5, label)
            canvas_obj.drawRightString(table_x + table_width - 6, row_y - MIN_ROW_HEIGHT + 5, value)

        # REMAINING BALANCE row (highlighted)
        rem_row_y = data_start_y - items_height - 7 * MIN_ROW_HEIGHT
        canvas_obj.setFillColor(GRAY_DARK)
        canvas_obj.rect(totals_x, rem_row_y - MIN_ROW_HEIGHT, totals_box_width, MIN_ROW_HEIGHT, fill=1, stroke=1)
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont('Helvetica-Bold', 7)
        canvas_obj.drawString(totals_x + 6, rem_row_y - MIN_ROW_HEIGHT + 5, 'BAL DUE:')
        canvas_obj.drawRightString(table_x + table_width - 6, rem_row_y - MIN_ROW_HEIGHT + 5, f'{remaining_balance:.3f}')

        # "*Items sold..." text
        items_sold_y = data_start_y - items_height - 8 * MIN_ROW_HEIGHT
        canvas_obj.setFillColor(colors.Color(0.1, 0.3, 0.6))
        canvas_obj.setFont('Helvetica-Oblique', 7)
        canvas_obj.drawString(table_x + 6, items_sold_y - MIN_ROW_HEIGHT + 5, '*Items sold will not be taken back or returned.')
        
        # === BANK DETAILS BOX ===
        bank_box_width = 140
        bank_box_height = 50
        bank_y = (rem_row_y - MIN_ROW_HEIGHT) + 15 + bank_box_height
        bank_x = totals_x - bank_box_width - 10
        
        canvas_obj.setStrokeColor(BLACK)
        if bank_x < table_x: bank_x = table_x + 10 # Fallback
        
        canvas_obj.roundRect(bank_x, bank_y - bank_box_height, bank_box_width, bank_box_height, 3, fill=0, stroke=1)
        
        canvas_obj.setFont('Helvetica-Bold', 6)
        canvas_obj.setFillColor(BLACK)
        canvas_obj.drawString(bank_x + 5, bank_y - 11, 'BANK TRANSFER DETAILS')
        canvas_obj.drawString(bank_x + 5, bank_y - 20, BANK_DETAILS['name'])
        canvas_obj.setFont('Helvetica', 6)
        canvas_obj.drawString(bank_x + 5, bank_y - 30, f"Name: {BANK_DETAILS['bank']}")
        canvas_obj.drawString(bank_x + 5, bank_y - 40, f"IBAN: {BANK_DETAILS['iban']}")
        
        return rem_row_y - MIN_ROW_HEIGHT
    
    # Helper function to draw IN WORDS row
    def draw_in_words(canvas_obj, y_pos):
        in_words_height = 16
        in_words_label_w = 50
        
        # Draw IN WORDS label and value
        canvas_obj.setFillColor(GRAY_LIGHT)
        canvas_obj.rect(table_x, y_pos - in_words_height, in_words_label_w, in_words_height, fill=1, stroke=1)
        canvas_obj.setFillColor(BLACK)
        canvas_obj.setFont('Helvetica-Bold', 6)
        canvas_obj.drawString(table_x + 4, y_pos - in_words_height + 5, 'IN WORDS')
        
        canvas_obj.setFillColor(WHITE)
        canvas_obj.rect(table_x + in_words_label_w, y_pos - in_words_height, table_width - in_words_label_w, in_words_height, fill=1, stroke=1)
        canvas_obj.setFillColor(BLACK)
        canvas_obj.setFont('Helvetica-Bold', 6)
        amount_words = number_to_words(total_net_all)
        # The user wants specific casing, number_to_words already returns it
        canvas_obj.drawString(table_x + in_words_label_w + 3, y_pos - in_words_height + 5, amount_words)
    
    # Helper function to draw signature section
    def draw_signature(canvas_obj, table_end_y):
        footer_top = 116
        sig_line_y = footer_top + 30 # Moved up slightly
        
        today = datetime.now()
        canvas_obj.setFillColor(BLACK)
        
        sales_person = edit_data.get('sales_person', '') or invoice_data.get('sales_person', '')
        if len(sales_person) > 15:
            sales_person = sales_person[:15] + '...'
            
        # Center points for 3 sections
        x1 = MARGIN_LEFT + (CONTENT_WIDTH / 6)
        x2 = MARGIN_LEFT + (CONTENT_WIDTH / 2)
        x3 = MARGIN_LEFT + (5 * CONTENT_WIDTH / 6)
        
        # Signature Labels (Centered in their sections)
        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.drawCentredString(x1, sig_line_y, 'Authorized Signatory/STAMP')
        
        canvas_obj.setFillColor(colors.Color(0.6, 0.1, 0.1))
        canvas_obj.setFont('Helvetica', 8)
        # Sales Person Info in Center
        canvas_obj.drawCentredString(x2, sig_line_y + 20, f'{sales_person}')
        canvas_obj.drawCentredString(x2, sig_line_y + 10, f'{today.strftime("%d-%m-%Y")}    {today.strftime("%I:%M %p")}')
        canvas_obj.setFillColor(BLACK)
        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.drawCentredString(x2, sig_line_y, 'Sales Person Name')
        
        # Receiver Signature
        canvas_obj.drawCentredString(x3, sig_line_y, 'Receiver Signature')
        
        # "Thank You for Your Business!" - Below signatures, above footer
        thank_you_text = 'Thank You for Your Business!'
        canvas_obj.setFillColor(ORANGE)
        canvas_obj.setFont('Helvetica-Bold', 11)
        canvas_obj.drawCentredString(PAGE_WIDTH / 2, 125, thank_you_text)
    
    # Helper function to draw footer
    def draw_footer(canvas_obj):
        footer_img_path = os.path.join(static_dir, 'shop_footer_board.jpg')
        
        footer_bar_height = 26
        orange_line_height = 5
        footer_img_height = 85
        
        orange_y = 0
        footer_bar_y = orange_y + orange_line_height
        footer_img_y = footer_bar_y + footer_bar_height
        
        try:
            if os.path.exists(footer_img_path):
                # Keep only the footer image at the bottom, remove bars and text
                canvas_obj.drawImage(footer_img_path, 0, 0,
                                    width=PAGE_WIDTH, height=footer_img_height,
                                    preserveAspectRatio=False)
        except Exception as e:
            print(f"Could not load footer image: {e}")
    
    # Helper function to draw header section (page 1 only)
    def draw_header(canvas_obj):
        # Start higher up (8mm from top) to utilize space better
        top_offset = 8 * mm
        header_img_height = 85 
        header_img_path = os.path.join(static_dir, 'Invoice_Header.png')
        
        try:
            if os.path.exists(header_img_path):
                # Use MARGIN_LEFT and CONTENT_WIDTH to align perfectly with the boxes below
                canvas_obj.drawImage(header_img_path, MARGIN_LEFT, height - top_offset - header_img_height, 
                                   width=CONTENT_WIDTH, height=header_img_height, 
                                   preserveAspectRatio=False)
        except Exception as e:
            print(f"Could not load header image: {e}")
            
        # Start the data row (Customer, INVOCIE, Meta) exactly 12pt below the image
        y = height - top_offset - header_img_height - 12
        
        # Customer Details (Left side) - compact width, height grows with content
        customer_box_width = 160
        customer_box_x = MARGIN_LEFT
        
        # Meta Table (Right side) - flush to right edge, wider with no gap
        meta_box_width = 170
        meta_box_x = MARGIN_LEFT + CONTENT_WIDTH - meta_box_width
        
        # INVOICE banner (perfectly centered on the page)
        title_bar_width = 110
        title_bar_x = (width - title_bar_width) / 2
        
        meta_row_height = 11
        title_bar_height = 20
        
        # Calculate Customer Box internal lines first to determine height
        name_str = str(customer_name)
        address_str = str(customer_address)
        mobile_str = str(customer_mobile)
        
        label_width = 75
        chars_per_line = 24
        
        name_lines = max(1, (len(name_str) + chars_per_line - 1) // chars_per_line)
        address_lines = max(1, (len(address_str) + chars_per_line - 1) // chars_per_line)
        mobile_lines = 1
        
        line_height = 10
        padding = 8
        total_lines = name_lines + address_lines + mobile_lines
        customer_box_height = max(45, total_lines * line_height + padding * 2)
        
        # Draw everything starting at top y
        row_top_y = y
        
        # 1. Draw Customer Box (Left)
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setStrokeColor(BLACK)
        canvas_obj.roundRect(customer_box_x, row_top_y - customer_box_height, customer_box_width, customer_box_height, 4, fill=1, stroke=1)
        
        canvas_obj.setFillColor(BLACK)
        canvas_obj.setFont('Helvetica-Bold', 6)
        y_pos = row_top_y - padding
        canvas_obj.drawString(customer_box_x + 6, y_pos, 'CUSTOMER NAME #')
        
        canvas_obj.setFont('Helvetica', 6)
        for i in range(name_lines):
            start = i * chars_per_line
            end = min(start + chars_per_line, len(name_str))
            canvas_obj.drawString(customer_box_x + label_width, y_pos - i * line_height, name_str[start:end])
        y_pos -= name_lines * line_height
        
        canvas_obj.setFont('Helvetica-Bold', 6)
        canvas_obj.drawString(customer_box_x + 6, y_pos, 'ADDRESS #')
        canvas_obj.setFont('Helvetica', 6)
        for i in range(address_lines):
            start = i * chars_per_line
            end = min(start + chars_per_line, len(address_str))
            canvas_obj.drawString(customer_box_x + label_width, y_pos - i * line_height, address_str[start:end])
        y_pos -= address_lines * line_height
        
        canvas_obj.setFont('Helvetica-Bold', 6)
        canvas_obj.drawString(customer_box_x + 6, y_pos, 'MOBILE NO #')
        canvas_obj.setFont('Helvetica', 6)
        canvas_obj.drawString(customer_box_x + label_width, y_pos, mobile_str)
        
        # 2. Draw INVOICE banner (Center)
        # Center vertically relative to the customer box if possible, or just top-aligned
        banner_y = row_top_y - (customer_box_height / 2) + (title_bar_height / 2) - 5
        
        # Determine header text based on VAT
        vat_percent = float(invoice_data.get('vat_percent', 0) or 0)
        header_text = 'TAX INVOICE' if vat_percent > 0 else 'INVOICE'
        canvas_obj.setFillColor(GRAY_DARK)
        canvas_obj.rect(title_bar_x, banner_y - title_bar_height, title_bar_width, title_bar_height, fill=1, stroke=0)
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont('Helvetica-Bold', 11)
        canvas_obj.drawCentredString(title_bar_x + title_bar_width / 2, banner_y - 14, header_text)
        
        canvas_obj.setStrokeColor(BLACK)
        canvas_obj.setLineWidth(1.2)
        canvas_obj.line(title_bar_x, banner_y - title_bar_height - 2, title_bar_x + title_bar_width, banner_y - title_bar_height - 2)
        canvas_obj.setLineWidth(1)
        
        # 3. Draw Meta Box (Right)
        meta_data = [
            ('Invoice Date:', format_date(invoice_data.get('date'))),
            ('Invoice No:', edit_data.get('invoice_number', '')),
            ('Payment Terms:', edit_data.get('payment_terms', 'CREDIT')),
            ('Due Date:', format_date(edit_data.get('due_date', ''))),
        ]
        
        meta_label_w = 70
        for i, (label, value) in enumerate(meta_data):
            row_y = row_top_y - i * meta_row_height
            
            canvas_obj.setFillColor(GRAY_DARK)
            canvas_obj.rect(meta_box_x, row_y - meta_row_height, meta_label_w, meta_row_height, fill=1, stroke=1)
            
            canvas_obj.setFillColor(WHITE)
            canvas_obj.rect(meta_box_x + meta_label_w, row_y - meta_row_height, meta_box_width - meta_label_w, meta_row_height, fill=1, stroke=1)
            
            canvas_obj.setFillColor(WHITE)
            canvas_obj.setFont('Helvetica-Bold', 6)
            canvas_obj.drawString(meta_box_x + 3, row_y - meta_row_height + 3, label)
            
            canvas_obj.setFillColor(BLACK)
            canvas_obj.setFont('Helvetica', 6)
            canvas_obj.drawString(meta_box_x + meta_label_w + 3, row_y - meta_row_height + 3, str(value))
        
        # Return the y position for the table, with increased gap (30pt) for clarity
        return row_top_y - max(customer_box_height, 4 * meta_row_height) - 30
    
    # ==================== RENDER PAGES ====================
    
    current_item_idx = 0
    
    for page_num in range(1, total_pages + 1):
        is_first_page = (page_num == 1)
        is_last_page = (page_num == total_pages)
        
        # Get items for this page from pre-calculated distribution
        items_this_page = items_per_page[page_num - 1]
        page_items = item_rows[current_item_idx:current_item_idx + items_this_page]
        page_heights = item_heights[current_item_idx:current_item_idx + items_this_page]
        
        # Draw page number
        draw_page_number(c, page_num, total_pages)
        
        if is_first_page:
            # Page 1: Draw header + table
            table_y = draw_header(c)
            data_start_y = draw_table_header(c, table_y)
            page_heights = item_heights[current_item_idx:current_item_idx + items_this_page]
            table_end_y, totals_start_row, totals_x, totals_box_width, items_height = draw_item_rows(
                c, data_start_y, page_items, page_heights, show_totals=is_last_page
            )
        else:
            # Other pages: Table starts near top
            table_y = height - MARGIN_TOP - 20
            data_start_y = draw_table_header(c, table_y)
            page_heights = item_heights[current_item_idx:current_item_idx + items_this_page]
            table_end_y, totals_start_row, totals_x, totals_box_width, items_height = draw_item_rows(
                c, data_start_y, page_items, page_heights, show_totals=is_last_page
            )
        
        # Update index AFTER getting page_heights
        current_item_idx += len(page_items)
        
        if is_last_page:
            # Draw totals section
            draw_totals_section(c, data_start_y, totals_start_row, totals_x, totals_box_width, items_height)
            # Draw IN WORDS row
            draw_in_words(c, table_end_y)
            # Draw signature section (position relative to table end)
            draw_signature(c, table_end_y - 16)  # 16 = IN WORDS row height
            # Draw footer
            draw_footer(c)
        
        if page_num < total_pages:
            c.showPage()
    
    # Save the PDF
    c.save()
    buffer.seek(0)
    return buffer