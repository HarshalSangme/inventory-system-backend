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

def number_to_words(num):
    """Convert number to words (simplified)"""
    ones = ['', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE',
            'TEN', 'ELEVEN', 'TWELVE', 'THIRTEEN', 'FOURTEEN', 'FIFTEEN', 'SIXTEEN',
            'SEVENTEEN', 'EIGHTEEN', 'NINETEEN']
    tens = ['', '', 'TWENTY', 'THIRTY', 'FORTY', 'FIFTY', 'SIXTY', 'SEVENTY', 'EIGHTY', 'NINETY']
    
    if num < 20:
        return ones[int(num)]
    elif num < 100:
        return tens[int(num) // 10] + (' ' + ones[int(num) % 10] if num % 10 else '')
    elif num < 1000:
        return ones[int(num) // 100] + ' HUNDRED' + (' AND ' + number_to_words(num % 100) if num % 100 else '')
    else:
        return str(int(num))

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
    
    # Static assets directory
    static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
    
    # Prepare items data
    items = invoice_data.get('items', [])
    total_gross = 0
    
    item_rows = []
    for idx, item in enumerate(items):
        price = float(item.get('price', 0) or 0)
        qty = float(item.get('quantity', 0) or 0)
        net = price * qty
        total_gross += net
        
        item_rows.append([
            str(idx + 1),
            str(item.get('product', {}).get('sku', '') or item.get('sku', '-')),
            str(item.get('product', {}).get('name', '') or item.get('name', '')),
            str(int(qty)),
            f'{price:.3f}',
            str(item.get('discount', '') or ''),
            '',
            '',
            str(item.get('vat', '') or ''),
            f'{net:.3f}',
        ])
    
    # Column headers and widths - scaled to fit CONTENT_WIDTH
    headers = ['SR.NO', 'ITEM CODE', 'ITEM NAME', 'QTY', 'PRICE', 'DISCOUNT', 'AMT', '%', 'VAT', 'NET AMT']
    base_widths = [28, 55, 135, 30, 55, 55, 45, 25, 50, 75]
    total_base = sum(base_widths)
    table_width = CONTENT_WIDTH
    col_widths = [w * table_width / total_base for w in base_widths]
    table_x = MARGIN_LEFT
    
    # Row height constant
    row_height = 16
    
    # Calculate pagination
    # Page 1: Has header, meta box, customer box - fewer items fit
    # Subsequent pages: More items fit (no header)
    # Last page needs space for totals (5 rows) + signature + footer (~340pt reserved)
    
    footer_reserved = 340  # Reserve for totals, signature, footer on last page
    items_per_page_1 = 12  # Items on page 1 (with header/customer box)
    items_per_middle_page = 30  # Items on middle pages (no header, no footer)
    
    # Calculate total pages needed
    actual_items = len(item_rows)
    
    if actual_items <= items_per_page_1:
        # Single page - works with existing logic
        total_pages = 1
    else:
        remaining_after_page1 = actual_items - items_per_page_1
        # Last page needs 5 rows for totals section
        items_last_page = items_per_middle_page - 5
        
        if remaining_after_page1 <= items_last_page:
            total_pages = 2
        else:
            remaining_after_last = remaining_after_page1 - items_last_page
            middle_pages = (remaining_after_last + items_per_middle_page - 1) // items_per_middle_page
            total_pages = 2 + middle_pages
    
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
        canvas_obj.rect(table_x, start_y - row_height, table_width, row_height, fill=1, stroke=1)
        
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont('Helvetica-Bold', 6)
        x = table_x
        for i, header in enumerate(headers):
            canvas_obj.drawCentredString(x + col_widths[i] / 2, start_y - row_height + 5, header)
            x += col_widths[i]
        
        # Draw header vertical lines
        canvas_obj.setStrokeColor(WHITE)
        x = table_x
        for i in range(len(col_widths) - 1):
            x += col_widths[i]
            canvas_obj.line(x, start_y, x, start_y - row_height)
        canvas_obj.setStrokeColor(BLACK)
        
        return start_y - row_height  # Return data start y
    
    # Helper function to draw item rows
    def draw_item_rows(canvas_obj, start_y, items_to_draw, show_totals=False):
        data_start_y = start_y
        
        # For last page, add 5 empty rows for totals
        display_rows = items_to_draw.copy()
        if show_totals:
            # Add empty rows to make room for totals section
            min_total_rows = len(display_rows) + 5
            while len(display_rows) < min_total_rows:
                display_rows.append([''] * 10)
        
        # Ensure minimum 12 rows for layout consistency
        while len(display_rows) < 12:
            display_rows.append([''] * 10)
        
        totals_start_row = len(display_rows) - 5 if show_totals else len(display_rows)
        totals_box_width = col_widths[-1] + col_widths[-2]
        totals_x = table_x + table_width - totals_box_width
        
        # Draw outer table border
        total_table_height = len(display_rows) * row_height
        canvas_obj.rect(table_x, data_start_y - total_table_height, table_width, total_table_height)
        
        # Draw vertical lines - stop at totals_start_row for item columns
        x = table_x
        for i in range(len(col_widths) - 1):
            x += col_widths[i]
            if show_totals:
                if x < totals_x:
                    canvas_obj.line(x, data_start_y, x, data_start_y - totals_start_row * row_height)
            else:
                canvas_obj.line(x, data_start_y, x, data_start_y - total_table_height)
        
        if show_totals:
            # Draw horizontal line above "Items sold" text
            items_sold_separator_y = data_start_y - totals_start_row * row_height
            canvas_obj.line(table_x, items_sold_separator_y, totals_x, items_sold_separator_y)
            
            # Draw horizontal lines in totals section
            for r in range(1, len(display_rows)):
                line_y = data_start_y - r * row_height
                if r >= totals_start_row:
                    canvas_obj.line(totals_x, line_y, table_x + table_width, line_y)
            
            # Vertical line before totals
            canvas_obj.line(totals_x, data_start_y - totals_start_row * row_height, totals_x, data_start_y - total_table_height)
        
        # Fill in item data
        canvas_obj.setFillColor(BLACK)
        canvas_obj.setFont('Helvetica', 6)
        for row_idx, row in enumerate(display_rows):
            if show_totals and row_idx >= totals_start_row:
                continue
            
            row_y = data_start_y - row_idx * row_height
            x = table_x
            for col_idx, cell in enumerate(row):
                if col_idx == 0:
                    canvas_obj.drawCentredString(x + col_widths[col_idx] / 2, row_y - row_height + 5, cell)
                elif col_idx in [1, 2]:
                    text = cell[:20] if len(cell) > 20 else cell
                    canvas_obj.drawString(x + 3, row_y - row_height + 5, text)
                else:
                    canvas_obj.drawRightString(x + col_widths[col_idx] - 3, row_y - row_height + 5, cell)
                x += col_widths[col_idx]
        
        return data_start_y - total_table_height, totals_start_row, totals_x, totals_box_width
    
    # Helper function to draw totals section
    def draw_totals_section(canvas_obj, data_start_y, totals_start_row, totals_x, totals_box_width):
        vat_percent = float(invoice_data.get('vat_percent', 0) or 0)
        total_vat = total_gross * (vat_percent / 100)
        final_net = total_gross + total_vat
        display_total = float(invoice_data.get('total_amount', 0) or 0) or final_net
        
        totals_data = [
            ('GROSS AMT', f'{total_gross:.3f}'),
            ('DISCOUNT', str(invoice_data.get('discount', '-') or '-')),
            ('VAT AMT', f'{total_vat:.3f}' if total_vat > 0 else '-'),
            ('Balance C/f', str(invoice_data.get('balance_cf', '1.500') or '1.500')),
        ]
        
        totals_label_width = totals_box_width * 0.55
        totals_value_x = totals_x + totals_label_width
        
        canvas_obj.setStrokeColor(BLACK)
        canvas_obj.line(totals_value_x, data_start_y - totals_start_row * row_height,
                       totals_value_x, data_start_y - (totals_start_row + 5) * row_height)
        
        canvas_obj.setFont('Helvetica-Bold', 7)
        canvas_obj.setFillColor(BLACK)
        for i, (label, value) in enumerate(totals_data):
            row_y = data_start_y - (totals_start_row + i) * row_height
            canvas_obj.drawString(totals_x + 6, row_y - row_height + 5, label)
            canvas_obj.drawRightString(table_x + table_width - 6, row_y - row_height + 5, value)
        
        # NET AMT BHD row (highlighted)
        net_row_y = data_start_y - (totals_start_row + 4) * row_height
        canvas_obj.setFillColor(GRAY_DARK)
        canvas_obj.rect(totals_x, net_row_y - row_height, totals_box_width, row_height, fill=1, stroke=1)
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont('Helvetica-Bold', 7)
        canvas_obj.drawString(totals_x + 6, net_row_y - row_height + 5, 'NET AMT BHD:')
        canvas_obj.drawRightString(table_x + table_width - 6, net_row_y - row_height + 5, f'{display_total:.3f}')
        
        # "*Items sold..." text
        canvas_obj.setFillColor(colors.Color(0.1, 0.3, 0.6))
        canvas_obj.setFont('Helvetica-Oblique', 7)
        items_sold_y = data_start_y - totals_start_row * row_height
        canvas_obj.drawString(table_x + 6, items_sold_y - row_height + 5, '*Items sold will not be taken back or returned.')
        
        return net_row_y - row_height
    
    # Helper function to draw IN WORDS row
    def draw_in_words(canvas_obj, y_pos):
        in_words_height = 16
        in_words_label_w = 50
        
        canvas_obj.setFillColor(GRAY_LIGHT)
        canvas_obj.rect(table_x, y_pos - in_words_height, in_words_label_w, in_words_height, fill=1, stroke=1)
        canvas_obj.setFillColor(BLACK)
        canvas_obj.setFont('Helvetica-Bold', 5)
        canvas_obj.drawString(table_x + 4, y_pos - in_words_height + 5, 'IN WORDS')
        
        canvas_obj.setFillColor(WHITE)
        canvas_obj.rect(table_x + in_words_label_w, y_pos - in_words_height, table_width - in_words_label_w, in_words_height, fill=1, stroke=1)
        canvas_obj.setFillColor(BLACK)
        canvas_obj.setFont('Helvetica-Bold', 6)
        amount_words = f'BAHRAIN DINAR {number_to_words(int(total_gross))} ONLY'
        canvas_obj.drawString(table_x + in_words_label_w + 4, y_pos - in_words_height + 5, amount_words)
    
    # Helper function to draw signature section
    def draw_signature(canvas_obj):
        footer_bar_height = 26
        orange_line_height = 5
        footer_img_height = 125
        footer_top = footer_bar_height + orange_line_height + footer_img_height
        
        sig_line_y = footer_top + 12
        stamp_area_y = sig_line_y + 80
        thank_you_y = stamp_area_y + 20
        bank_box_height = 48
        bank_y = thank_you_y + 20 + bank_box_height
        
        # Bank details box
        bank_box_width = 160
        canvas_obj.setStrokeColor(BLACK)
        canvas_obj.roundRect(MARGIN_LEFT, bank_y - bank_box_height, bank_box_width, bank_box_height, 3, fill=0, stroke=1)
        
        canvas_obj.setFont('Helvetica-Bold', 6)
        canvas_obj.setFillColor(BLACK)
        canvas_obj.drawString(MARGIN_LEFT + 5, bank_y - 10, 'BANK TRANSFER DETAILS')
        canvas_obj.drawString(MARGIN_LEFT + 5, bank_y - 20, BANK_DETAILS['name'])
        canvas_obj.setFont('Helvetica', 6)
        canvas_obj.drawString(MARGIN_LEFT + 5, bank_y - 30, f"Name: {BANK_DETAILS['bank']}")
        canvas_obj.drawString(MARGIN_LEFT + 5, bank_y - 40, f"IBAN {BANK_DETAILS['iban']}")
        
        # Thank you message
        canvas_obj.setFillColor(ORANGE)
        canvas_obj.setFont('Helvetica-Bold', 11)
        canvas_obj.drawString(MARGIN_LEFT, thank_you_y, 'Thank You for Your Business!')
        
        # Date value above signature row
        today = datetime.now()
        canvas_obj.setFillColor(BLACK)
        canvas_obj.setFont('Helvetica', 8)
        sales_person = edit_data.get('sales_person', '') or invoice_data.get('sales_person', '')
        if len(sales_person) > 15:
            sales_person = sales_person[:15] + '...'
        
        middle_x = width / 2 - 60
        canvas_obj.drawString(middle_x + 105, sig_line_y + 15, today.strftime('%d-%m-%Y'))
        
        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.drawString(MARGIN_LEFT, sig_line_y, 'Authorized Signatory/STAMP')
        
        canvas_obj.setFillColor(colors.Color(0.6, 0.1, 0.1))
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.drawString(middle_x, sig_line_y, f'Sales Person #  {sales_person}')
        canvas_obj.drawString(middle_x + 105, sig_line_y, 'Date')
        canvas_obj.drawString(middle_x + 140, sig_line_y, 'Time')
        
        canvas_obj.setFillColor(BLACK)
        canvas_obj.drawRightString(width - MARGIN_RIGHT, sig_line_y, 'Receiver Signature')
    
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
                canvas_obj.drawImage(footer_img_path, 0, footer_img_y,
                                    width=PAGE_WIDTH, height=footer_img_height,
                                    preserveAspectRatio=False)
        except Exception as e:
            print(f"Could not load footer image: {e}")
        
        canvas_obj.setFillColor(colors.Color(0.12, 0.12, 0.12))
        canvas_obj.rect(0, footer_bar_y, PAGE_WIDTH, footer_bar_height, fill=1, stroke=0)
        
        canvas_obj.setFillColor(ORANGE)
        canvas_obj.rect(0, orange_y, PAGE_WIDTH, orange_line_height, fill=1, stroke=0)
        
        icon_center_y = footer_bar_y + footer_bar_height / 2
        text_y = footer_bar_y + 8
        icon_size = 16
        icon_y = icon_center_y - icon_size / 2
        
        phone_icon_path = os.path.join(static_dir, 'phone_white_logo.png')
        whatsapp_icon_path = os.path.join(static_dir, 'whatsapp_logo.png')
        email_icon_path = os.path.join(static_dir, 'email_white_logo.png')
        
        try:
            if os.path.exists(phone_icon_path):
                canvas_obj.drawImage(phone_icon_path, MARGIN_LEFT + 8, icon_y,
                                    width=icon_size, height=icon_size,
                                    preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Could not load phone icon: {e}")
        
        try:
            if os.path.exists(whatsapp_icon_path):
                canvas_obj.drawImage(whatsapp_icon_path, MARGIN_LEFT + 28, icon_y,
                                    width=icon_size, height=icon_size,
                                    preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Could not load whatsapp icon: {e}")
        
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont('Helvetica-Bold', 11)
        canvas_obj.drawString(MARGIN_LEFT + 48, text_y, '+973 36341106')
        
        email_text = 'harjinders717@gmail.com'
        email_text_width = canvas_obj.stringWidth(email_text, 'Helvetica-Bold', 11)
        email_text_x = PAGE_WIDTH - MARGIN_LEFT - email_text_width
        email_icon_x = email_text_x - icon_size - 4
        try:
            if os.path.exists(email_icon_path):
                canvas_obj.drawImage(email_icon_path, email_icon_x, icon_y,
                                    width=icon_size, height=icon_size,
                                    preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Could not load email icon: {e}")
        
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont('Helvetica-Bold', 11)
        canvas_obj.drawString(email_text_x, text_y, email_text)
    
    # Helper function to draw header section (page 1 only)
    def draw_header(canvas_obj):
        y = height - MARGIN_TOP
        
        logo_path = os.path.join(static_dir, 'jot.png')
        shop_name_path = os.path.join(static_dir, 'Shop_Name.jpg')
        shop_address_path = os.path.join(static_dir, 'Shop_Address.jpg')
        
        logo_size = 60
        try:
            if os.path.exists(logo_path):
                canvas_obj.drawImage(logo_path, MARGIN_LEFT, y - logo_size, width=logo_size, height=logo_size, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Could not load logo: {e}")
        
        try:
            if os.path.exists(shop_name_path):
                canvas_obj.drawImage(shop_name_path, MARGIN_LEFT + logo_size - 18, y - 38, width=220, height=38, preserveAspectRatio=True)
        except Exception as e:
            print(f"Could not load shop name: {e}")
        
        try:
            if os.path.exists(shop_address_path):
                canvas_obj.drawImage(shop_address_path, MARGIN_LEFT + logo_size - 18, y - 60, width=200, height=20, preserveAspectRatio=True)
        except Exception as e:
            print(f"Could not load shop address: {e}")
        
        # Meta box
        meta_box_width = 160
        meta_box_x = MARGIN_LEFT + CONTENT_WIDTH - meta_box_width
        meta_box_y = y
        meta_row_height = 14
        label_col_width = 80
        
        meta_data = [
            ('Invoice Date:', format_date(invoice_data.get('date'))),
            ('Invoice No:', edit_data.get('invoice_number', '')),
            ('Payment Terms:', edit_data.get('payment_terms', 'CREDIT')),
            ('Due Date:', format_date(edit_data.get('due_date', ''))),
        ]
        
        for i, (label, value) in enumerate(meta_data):
            row_y = meta_box_y - i * meta_row_height
            
            canvas_obj.setFillColor(GRAY_DARK)
            canvas_obj.rect(meta_box_x, row_y - meta_row_height, label_col_width, meta_row_height, fill=1, stroke=1)
            
            canvas_obj.setFillColor(WHITE)
            canvas_obj.rect(meta_box_x + label_col_width, row_y - meta_row_height, meta_box_width - label_col_width, meta_row_height, fill=1, stroke=1)
            
            canvas_obj.setFillColor(WHITE)
            canvas_obj.setFont('Helvetica-Bold', 7)
            canvas_obj.drawString(meta_box_x + 3, row_y - meta_row_height + 4, label)
            
            canvas_obj.setFillColor(BLACK)
            canvas_obj.setFont('Helvetica', 7)
            canvas_obj.drawString(meta_box_x + label_col_width + 3, row_y - meta_row_height + 4, str(value))
        
        # Invoice title bar
        title_bar_width = 130
        title_bar_height = 22
        title_bar_x = meta_box_x - title_bar_width - 20
        title_bar_y = meta_box_y - 4 * meta_row_height + title_bar_height
        
        canvas_obj.setFillColor(GRAY_DARK)
        canvas_obj.rect(title_bar_x, title_bar_y - title_bar_height, title_bar_width, title_bar_height, fill=1, stroke=0)
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont('Helvetica-Bold', 12)
        canvas_obj.drawCentredString(title_bar_x + title_bar_width / 2, title_bar_y - 16, 'INVOICE')
        
        canvas_obj.setStrokeColor(BLACK)
        canvas_obj.setLineWidth(1.5)
        canvas_obj.line(title_bar_x, title_bar_y - title_bar_height - 2, title_bar_x + title_bar_width, title_bar_y - title_bar_height - 2)
        canvas_obj.setLineWidth(1)
        
        # Customer box
        customer_box_y = meta_box_y - 4 * meta_row_height - 30
        customer_box_width = 220
        
        name_str = str(customer_name)
        address_str = str(customer_address)
        mobile_str = str(customer_mobile)
        
        label_width = 85
        chars_per_line = 28
        
        name_lines = max(1, (len(name_str) + chars_per_line - 1) // chars_per_line)
        address_lines = max(1, (len(address_str) + chars_per_line - 1) // chars_per_line)
        mobile_lines = 1
        
        line_height = 11
        padding = 12
        total_lines = name_lines + address_lines + mobile_lines
        customer_box_height = max(50, total_lines * line_height + padding * 2)
        
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setStrokeColor(BLACK)
        canvas_obj.roundRect(MARGIN_LEFT, customer_box_y - customer_box_height, customer_box_width, customer_box_height, 5, fill=1, stroke=1)
        
        canvas_obj.setFillColor(BLACK)
        canvas_obj.setFont('Helvetica-Bold', 7)
        
        y_pos = customer_box_y - padding
        canvas_obj.drawString(MARGIN_LEFT + 8, y_pos, 'CUSTOMER NAME #')
        
        canvas_obj.setFont('Helvetica', 7)
        for i in range(name_lines):
            start = i * chars_per_line
            end = min(start + chars_per_line, len(name_str))
            canvas_obj.drawString(MARGIN_LEFT + label_width, y_pos - i * line_height, name_str[start:end])
        y_pos -= name_lines * line_height
        
        canvas_obj.setFont('Helvetica-Bold', 7)
        canvas_obj.drawString(MARGIN_LEFT + 8, y_pos, 'ADDRESS #')
        canvas_obj.setFont('Helvetica', 7)
        for i in range(address_lines):
            start = i * chars_per_line
            end = min(start + chars_per_line, len(address_str))
            canvas_obj.drawString(MARGIN_LEFT + label_width, y_pos - i * line_height, address_str[start:end])
        y_pos -= address_lines * line_height
        
        canvas_obj.setFont('Helvetica-Bold', 7)
        canvas_obj.drawString(MARGIN_LEFT + 8, y_pos, 'MOBILE NO #')
        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.drawString(MARGIN_LEFT + label_width, y_pos, mobile_str)
        
        return customer_box_y - customer_box_height - 15
    
    # ==================== RENDER PAGES ====================
    
    current_item_idx = 0
    
    for page_num in range(1, total_pages + 1):
        is_first_page = (page_num == 1)
        is_last_page = (page_num == total_pages)
        
        # Determine items for this page
        if is_first_page:
            items_this_page = items_per_page_1
        elif is_last_page:
            items_this_page = len(item_rows) - current_item_idx
        else:
            items_this_page = items_per_middle_page
        
        # Get items for current page
        page_items = item_rows[current_item_idx:current_item_idx + items_this_page]
        current_item_idx += len(page_items)
        
        # Draw page number
        draw_page_number(c, page_num, total_pages)
        
        if is_first_page:
            # Page 1: Draw header + table
            table_y = draw_header(c)
            data_start_y = draw_table_header(c, table_y)
            table_end_y, totals_start_row, totals_x, totals_box_width = draw_item_rows(
                c, data_start_y, page_items, show_totals=is_last_page
            )
        else:
            # Other pages: Table starts near top
            table_y = height - MARGIN_TOP - 20
            data_start_y = draw_table_header(c, table_y)
            table_end_y, totals_start_row, totals_x, totals_box_width = draw_item_rows(
                c, data_start_y, page_items, show_totals=is_last_page
            )
        
        if is_last_page:
            # Draw totals section
            draw_totals_section(c, data_start_y, totals_start_row, totals_x, totals_box_width)
            # Draw IN WORDS row
            draw_in_words(c, table_end_y)
            # Draw signature section
            draw_signature(c)
            # Draw footer
            draw_footer(c)
        
        if page_num < total_pages:
            c.showPage()
    
    # Save the PDF
    c.save()
    buffer.seek(0)
    return buffer