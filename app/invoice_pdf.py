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
    Generate invoice PDF from invoice data
    
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
    
    # ==================== HEADER SECTION ====================
    y = height - MARGIN_TOP
    
    # Load header images
    logo_path = os.path.join(static_dir, 'jot.png')
    shop_name_path = os.path.join(static_dir, 'Shop_Name.jpg')
    shop_address_path = os.path.join(static_dir, 'Shop_Address.jpg')
    
    # Draw logo (larger, positioned at left)
    logo_size = 70
    try:
        if os.path.exists(logo_path):
            c.drawImage(logo_path, MARGIN_LEFT, y - logo_size, width=logo_size, height=logo_size, preserveAspectRatio=True, mask='auto')
    except Exception as e:
        print(f"Could not load logo: {e}")
    
    # Draw shop name image (JOT AUTO PARTS W.L.L + Arabic text) - touching logo
    try:
        if os.path.exists(shop_name_path):
            c.drawImage(shop_name_path, MARGIN_LEFT + logo_size - 5, y - 38, width=200, height=38, preserveAspectRatio=True)
    except Exception as e:
        print(f"Could not load shop name: {e}")
    
    # Draw shop address image (below shop name, smaller)
    try:
        if os.path.exists(shop_address_path):
            c.drawImage(shop_address_path, MARGIN_LEFT + logo_size - 5, y - 62, width=180, height=20, preserveAspectRatio=True)
    except Exception as e:
        print(f"Could not load shop address: {e}")
    
    # ==================== META BOX (Right side - aligned with header top) ====================
    meta_box_width = 190
    meta_box_x = MARGIN_LEFT + CONTENT_WIDTH - meta_box_width  # Align with right edge of content
    meta_box_y = y  # Start at top
    row_height = 16
    label_col_width = 95
    
    # Draw meta box
    meta_data = [
        ('Invoice Date:', format_date(invoice_data.get('date'))),
        ('Invoice No:', edit_data.get('invoice_number', '')),
        ('Payment Terms:', edit_data.get('payment_terms', 'CREDIT')),
        ('Due Date:', format_date(edit_data.get('due_date', ''))),
    ]
    
    for i, (label, value) in enumerate(meta_data):
        row_y = meta_box_y - i * row_height
        
        # Label cell (dark background)
        c.setFillColor(GRAY_DARK)
        c.rect(meta_box_x, row_y - row_height, label_col_width, row_height, fill=1, stroke=1)
        
        # Value cell
        c.setFillColor(WHITE)
        c.rect(meta_box_x + label_col_width, row_y - row_height, meta_box_width - label_col_width, row_height, fill=1, stroke=1)
        
        # Text
        c.setFillColor(WHITE)
        c.setFont('Helvetica-Bold', 8)
        c.drawString(meta_box_x + 4, row_y - row_height + 5, label)
        
        c.setFillColor(BLACK)
        c.setFont('Helvetica', 8)
        c.drawString(meta_box_x + label_col_width + 4, row_y - row_height + 5, str(value))
    
    # ==================== INVOICE TITLE BAR (centered on page, aligned with bottom of meta box) ====================
    title_bar_width = 130
    title_bar_height = 22
    # Center horizontally on page
    title_bar_x = (PAGE_WIDTH - title_bar_width) / 2
    title_bar_y = meta_box_y - 4 * row_height + title_bar_height  # Aligned with bottom of meta box
    
    c.setFillColor(GRAY_DARK)
    c.rect(title_bar_x, title_bar_y - title_bar_height, title_bar_width, title_bar_height, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 12)
    c.drawCentredString(title_bar_x + title_bar_width / 2, title_bar_y - 16, 'INVOICE')
    
    # Underline below title bar
    c.setStrokeColor(BLACK)
    c.setLineWidth(1.5)
    c.line(title_bar_x, title_bar_y - title_bar_height - 2, title_bar_x + title_bar_width, title_bar_y - title_bar_height - 2)
    c.setLineWidth(1)  # Reset line width
    
    # ==================== CUSTOMER BOX ====================
    customer_box_y = meta_box_y - 4 * row_height - 15  # Below meta box
    customer_box_width = 280
    customer_box_height = 55
    
    c.setFillColor(WHITE)
    c.setStrokeColor(BLACK)
    c.roundRect(MARGIN_LEFT, customer_box_y - customer_box_height, customer_box_width, customer_box_height, 5, fill=1, stroke=1)
    
    customer_name = invoice_data.get('partner', {}).get('name', '') or invoice_data.get('customer_name', '')
    customer_address = invoice_data.get('partner', {}).get('address', '') or invoice_data.get('address', '')
    customer_mobile = invoice_data.get('partner', {}).get('phone', '') or invoice_data.get('mobile', '')
    
    c.setFillColor(BLACK)
    c.setFont('Helvetica-Bold', 7)
    c.drawString(MARGIN_LEFT + 8, customer_box_y - 15, 'CUSTOMER NAME #')
    c.drawString(MARGIN_LEFT + 8, customer_box_y - 28, 'ADDRESS #')
    c.drawString(MARGIN_LEFT + 8, customer_box_y - 41, 'MOBILE NO #')
    
    c.setFont('Helvetica', 7)
    c.drawString(MARGIN_LEFT + 95, customer_box_y - 15, str(customer_name))
    
    # Wrap address if needed
    if len(str(customer_address)) > 35:
        c.drawString(MARGIN_LEFT + 95, customer_box_y - 28, str(customer_address)[:35])
        c.drawString(MARGIN_LEFT + 95, customer_box_y - 36, str(customer_address)[35:70])
    else:
        c.drawString(MARGIN_LEFT + 95, customer_box_y - 28, str(customer_address))
    
    c.drawString(MARGIN_LEFT + 95, customer_box_y - 41, str(customer_mobile))
    
    # ==================== TABLE ====================
    table_y = customer_box_y - customer_box_height - 15
    
    # Column headers and widths - scaled to fit CONTENT_WIDTH
    headers = ['SR.NO', 'ITEM CODE', 'ITEM NAME', 'QTY', 'PRICE', 'DISCOUNT', 'AMT', '%', 'VAT', 'NET AMT']
    # Base proportions (will be scaled)
    base_widths = [28, 55, 135, 30, 55, 55, 45, 25, 50, 75]
    total_base = sum(base_widths)
    # Scale to fit content width
    table_width = CONTENT_WIDTH
    col_widths = [w * table_width / total_base for w in base_widths]
    row_height = 16
    
    # Calculate table position
    table_x = MARGIN_LEFT
    
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
    
    # Ensure minimum 12 rows
    min_rows = 12
    while len(item_rows) < min_rows:
        item_rows.append([''] * 10)
    
    # Draw table header
    header_y = table_y
    c.setFillColor(BLACK)
    c.rect(table_x, header_y - row_height, table_width, row_height, fill=1, stroke=1)
    
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 6)
    x = table_x
    for i, header in enumerate(headers):
        c.drawCentredString(x + col_widths[i] / 2, header_y - row_height + 5, header)
        x += col_widths[i]
    
    # Draw header vertical lines
    c.setStrokeColor(WHITE)
    x = table_x
    for i in range(len(col_widths) - 1):
        x += col_widths[i]
        c.line(x, header_y, x, header_y - row_height)
    c.setStrokeColor(BLACK)
    
    # Draw data rows
    data_start_y = header_y - row_height
    totals_start_row = len(item_rows) - 5  # Last 5 rows for totals
    totals_box_width = col_widths[-1] + col_widths[-2]  # Last 2 columns for totals
    totals_x = table_x + table_width - totals_box_width  # X position where totals box starts
    
    # Draw outer table border
    total_table_height = len(item_rows) * row_height
    c.rect(table_x, data_start_y - total_table_height, table_width, total_table_height)
    
    # Draw vertical lines
    x = table_x
    for i in range(len(col_widths) - 1):
        x += col_widths[i]
        # For last columns, only draw up to totals section
        if x >= table_x + table_width - totals_box_width and totals_start_row > 0:
            c.line(x, data_start_y, x, data_start_y - totals_start_row * row_height)
        else:
            c.line(x, data_start_y, x, data_start_y - total_table_height)
    
    # Draw horizontal lines - ONLY in totals section (not between item rows)
    for r in range(1, len(item_rows)):
        line_y = data_start_y - r * row_height
        if r >= totals_start_row:
            # Draw horizontal line ONLY in totals section (right-side totals box)
            c.line(totals_x, line_y, table_x + table_width, line_y)
        # No horizontal lines for item rows - they only have vertical separators
    
    # Vertical line before totals
    c.line(totals_x, data_start_y - totals_start_row * row_height, totals_x, data_start_y - total_table_height)
    
    # Fill in item data
    c.setFillColor(BLACK)
    c.setFont('Helvetica', 6)
    for row_idx, row in enumerate(item_rows):
        if row_idx >= totals_start_row:
            continue  # Skip rows in totals section (will fill totals separately)
        
        row_y = data_start_y - row_idx * row_height
        x = table_x
        for col_idx, cell in enumerate(row):
            if col_idx == 0:  # SR.NO - center
                c.drawCentredString(x + col_widths[col_idx] / 2, row_y - row_height + 5, cell)
            elif col_idx in [1, 2]:  # ITEM CODE, ITEM NAME - left
                text = cell[:20] if len(cell) > 20 else cell
                c.drawString(x + 3, row_y - row_height + 5, text)
            else:  # Others - right
                c.drawRightString(x + col_widths[col_idx] - 3, row_y - row_height + 5, cell)
            x += col_widths[col_idx]
    
    # ==================== TOTALS SECTION (inside table) ====================
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
    
    # Calculate label/value column widths within totals box
    totals_label_width = totals_box_width * 0.55  # 55% for label
    totals_value_x = totals_x + totals_label_width
    
    # Draw vertical line separating label and value in totals
    c.setStrokeColor(BLACK)
    c.line(totals_value_x, data_start_y - totals_start_row * row_height, 
           totals_value_x, data_start_y - (totals_start_row + 4) * row_height)
    
    c.setFont('Helvetica-Bold', 7)
    c.setFillColor(BLACK)
    for i, (label, value) in enumerate(totals_data):
        row_y = data_start_y - (totals_start_row + i) * row_height
        c.drawString(totals_x + 6, row_y - row_height + 5, label)
        c.drawRightString(table_x + table_width - 6, row_y - row_height + 5, value)
    
    # NET AMT BHD row (highlighted)
    net_row_y = data_start_y - (totals_start_row + 4) * row_height
    c.setFillColor(GRAY_DARK)
    c.rect(totals_x, net_row_y - row_height, totals_box_width, row_height, fill=1, stroke=1)
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 7)
    c.drawString(totals_x + 6, net_row_y - row_height + 5, 'NET AMT BHD:')
    c.drawRightString(table_x + table_width - 6, net_row_y - row_height + 5, f'{display_total:.3f}')
    
    # "*Items sold..." text - spans from left edge to totals section
    c.setFillColor(BLACK)
    c.setFont('Helvetica-Oblique', 7)
    items_sold_y = data_start_y - (totals_start_row + 1) * row_height  # Second row of totals area
    c.drawString(table_x + 6, items_sold_y + 5, '*Items sold will not be taken back or returned.')
    
    # ==================== IN WORDS ROW ====================
    in_words_y = data_start_y - total_table_height
    in_words_height = 16
    in_words_label_w = 50
    
    # IN WORDS label cell
    c.setFillColor(GRAY_LIGHT)
    c.rect(table_x, in_words_y - in_words_height, in_words_label_w, in_words_height, fill=1, stroke=1)
    c.setFillColor(BLACK)
    c.setFont('Helvetica-Bold', 5)
    c.drawString(table_x + 4, in_words_y - in_words_height + 5, 'IN WORDS')
    
    # IN WORDS value cell
    c.setFillColor(WHITE)
    c.rect(table_x + in_words_label_w, in_words_y - in_words_height, table_width - in_words_label_w, in_words_height, fill=1, stroke=1)
    c.setFillColor(BLACK)
    c.setFont('Helvetica-Bold', 6)
    amount_words = f'BAHRAIN DINAR {number_to_words(int(total_gross))} ONLY'
    c.drawString(table_x + in_words_label_w + 4, in_words_y - in_words_height + 5, amount_words)
    
    # ==================== BANK DETAILS ====================
    bank_y = in_words_y - in_words_height - 15
    bank_box_width = 180
    bank_box_height = 50
    
    c.setStrokeColor(BLACK)
    c.roundRect(MARGIN_LEFT, bank_y - bank_box_height, bank_box_width, bank_box_height, 4, fill=0, stroke=1)
    
    c.setFont('Helvetica-Bold', 6)
    c.drawString(MARGIN_LEFT + 6, bank_y - 10, 'BANK TRANSFER DETAILS')
    c.drawString(MARGIN_LEFT + 6, bank_y - 20, BANK_DETAILS['name'])
    c.setFont('Helvetica', 6)
    c.drawString(MARGIN_LEFT + 6, bank_y - 30, f"Bank: {BANK_DETAILS['bank']}")
    c.drawString(MARGIN_LEFT + 6, bank_y - 40, f"IBAN: {BANK_DETAILS['iban']}")
    
    # Thank you message
    c.setFont('Helvetica-Bold', 8)
    c.drawString(MARGIN_LEFT, bank_y - bank_box_height - 15, 'Thank You for Your Business!')
    
    # ==================== SIGNATURE ROW ====================
    sig_y = bank_y - bank_box_height - 45
    
    # Date above signature row
    today = datetime.now()
    c.setFont('Helvetica', 7)
    c.drawString(width / 2 + 40, sig_y + 15, today.strftime('%d/%m/%Y'))
    
    c.setFont('Helvetica', 7)
    c.drawString(MARGIN_LEFT, sig_y, 'Authorized Signatory/STAMP')
    
    c.setFont('Helvetica-Bold', 7)
    sales_person = edit_data.get('sales_person', 'Mamun Hussain')
    c.drawString(width / 2 - 60, sig_y, f'Sales Person: {sales_person}')
    c.drawString(width / 2 + 40, sig_y, 'Date')
    c.drawString(width / 2 + 80, sig_y, 'Time')
    c.drawRightString(width - MARGIN_RIGHT, sig_y, 'Receiver Signature')
    
    # ==================== FOOTER ====================
    # Load paths for footer images
    static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
    phone_path = os.path.join(static_dir, 'phone.png')
    whatsapp_path = os.path.join(static_dir, 'whatsapp.png')
    mail_path = os.path.join(static_dir, 'mail.png')
    footer_img_path = os.path.join(static_dir, 'shop_footer_board.jpg')
    
    # Footer dimensions (with left/right margins, no bottom margin)
    footer_bar_height = 26
    orange_line_height = 5
    footer_img_height = 50  # Reduced height for the banner image
    
    # Position from bottom of page (no bottom margin)
    orange_y = 0  # Orange line at very bottom
    footer_bar_y = orange_y + orange_line_height  # Black bar above orange
    footer_img_y = footer_bar_y + footer_bar_height  # Image above black bar
    
    # Draw shop footer image (full width within margins, preserve aspect ratio)
    try:
        if os.path.exists(footer_img_path):
            c.drawImage(footer_img_path, MARGIN_LEFT, footer_img_y, 
                       width=CONTENT_WIDTH, height=footer_img_height, 
                       preserveAspectRatio=True, anchor='s')
    except Exception as e:
        print(f"Could not load footer image: {e}")
    
    # Dark contact bar (with left/right margins)
    c.setFillColor(colors.Color(0.12, 0.12, 0.12))
    c.rect(MARGIN_LEFT, footer_bar_y, CONTENT_WIDTH, footer_bar_height, fill=1, stroke=0)
    
    # Orange accent line at bottom (with left/right margins)
    c.setFillColor(ORANGE)
    c.rect(MARGIN_LEFT, orange_y, CONTENT_WIDTH, orange_line_height, fill=1, stroke=0)
    
    # Icon settings
    icon_size = 18
    icon_y = footer_bar_y + (footer_bar_height - icon_size) / 2
    
    # Phone and WhatsApp icons on left
    try:
        if os.path.exists(phone_path):
            c.drawImage(phone_path, MARGIN_LEFT + 8, icon_y, width=icon_size, height=icon_size, preserveAspectRatio=True, mask='auto')
    except:
        pass
    
    try:
        if os.path.exists(whatsapp_path):
            c.drawImage(whatsapp_path, MARGIN_LEFT + 30, icon_y, width=icon_size, height=icon_size, preserveAspectRatio=True, mask='auto')
    except:
        pass
    
    # Phone number text
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(MARGIN_LEFT + 54, footer_bar_y + 8, '+973 36341106')
    
    # Mail icon on right side
    try:
        if os.path.exists(mail_path):
            c.drawImage(mail_path, MARGIN_LEFT + CONTENT_WIDTH - 175, icon_y, width=icon_size, height=icon_size, preserveAspectRatio=True, mask='auto')
    except:
        pass
    
    # Email text
    c.setFillColor(WHITE)
    c.drawRightString(MARGIN_LEFT + CONTENT_WIDTH - 8, footer_bar_y + 8, 'harjinders717@gmail.com')
    
    # Save the PDF
    c.save()
    buffer.seek(0)
    return buffer
