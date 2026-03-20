"""Report generation service - PDF, Excel, CSV export."""
import io
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import func

from models import db, Sale, SalesItem, Product, Customer, InventoryLog
from flask import current_app


def get_sales_report(start_date, end_date):
    """Get sales data for date range, including items bought per transaction."""
    sales = Sale.query.filter(
        Sale.created_at >= datetime.combine(start_date, datetime.min.time()),
        Sale.created_at <= datetime.combine(end_date, datetime.max.time())
    ).order_by(Sale.created_at).all()
    
    rows = []
    for s in sales:
        items_str = ', '.join(f"{item.product.name} x{item.quantity}" for item in s.items)
        rows.append({
            'receipt': s.receipt_number,
            'date': s.created_at.strftime('%Y-%m-%d %H:%M'),
            'customer': s.customer_name or (s.customer.name if s.customer else '-'),
            'products': items_str or '-',  # 'items' conflicts with dict.items() in Jinja2
            'subtotal': float(s.subtotal),
            'discount': float(s.discount_amount),
            'total': float(s.total_amount),
            'status': s.payment_status
        })
    return rows


def get_inventory_movement_report(start_date, end_date):
    """Get inventory movement for date range."""
    logs = InventoryLog.query.filter(
        InventoryLog.created_at >= datetime.combine(start_date, datetime.min.time()),
        InventoryLog.created_at <= datetime.combine(end_date, datetime.max.time())
    ).order_by(InventoryLog.created_at).all()
    
    rows = []
    for log in logs:
        rows.append({
            'date': log.created_at.strftime('%Y-%m-%d %H:%M'),
            'product': log.product.name,
            'type': log.type,
            'quantity': log.quantity,
            'previous': log.previous_qty,
            'new': log.new_qty,
            'notes': log.notes or ''
        })
    return rows


def get_best_selling(start_date, end_date, limit=20):
    """Get best-selling products."""
    items = db.session.query(
        Product.name,
        func.sum(SalesItem.quantity).label('total_qty'),
        func.sum(SalesItem.total).label('total_sales')
    ).join(SalesItem).join(Sale).filter(
        Sale.created_at >= datetime.combine(start_date, datetime.min.time()),
        Sale.created_at <= datetime.combine(end_date, datetime.max.time())
    ).group_by(Product.id).order_by(func.sum(SalesItem.quantity).desc()).limit(limit).all()
    
    return [{'name': n, 'quantity': q, 'sales': float(s)} for n, q, s in items]


def get_profit_report(start_date, end_date):
    """
    Get profit report: actual cost (COGS) vs revenue, total profit.
    Revenue = sum of sales (selling price * qty)
    Cost = sum of cost_price * qty at time of sale
    Profit = Revenue - Cost
    """
    sales = Sale.query.filter(
        Sale.created_at >= datetime.combine(start_date, datetime.min.time()),
        Sale.created_at <= datetime.combine(end_date, datetime.max.time())
    ).all()
    
    total_revenue = 0
    total_cost = 0
    for s in sales:
        for item in s.items:
            total_revenue += float(item.total)
            cost = getattr(item, 'cost_price', 0) or 0
            total_cost += float(cost) * item.quantity
    
    total_profit = total_revenue - total_cost
    return {
        'revenue': total_revenue,
        'cost': total_cost,
        'profit': total_profit,
        'margin_pct': (total_profit / total_revenue * 100) if total_revenue else 0
    }


def export_csv(data, headers=None):
    """Export data to CSV string."""
    import csv
    if not data or not headers:
        return ''
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in data:
        writer.writerow([row.get(h, '') for h in headers])
    return output.getvalue()


def export_excel(data, headers, sheet_title='Report'):
    """Export data to Excel. data=list of dicts, headers=list of (key, display_name)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title[:31]
    
    header_keys = [h[0] if isinstance(h, (list, tuple)) else h for h in headers]
    header_labels = [h[1] if isinstance(h, (list, tuple)) and len(h) > 1 else h for h in headers]
    ws.append(header_labels)
    for h in range(1, len(header_labels) + 1):
        ws.cell(1, h).font = Font(bold=True)
    
    for row in data:
        ws.append([row.get(k, '') for k in header_keys])
    
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def export_pdf(data, headers, title='Report'):
    """Export data to PDF. data=list of dicts, headers=list of keys."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
    elements.append(Spacer(1, 20))
    
    header_labels = [h[1] if isinstance(h, (list, tuple)) and len(h) > 1 else str(h) for h in headers]
    header_keys = [h[0] if isinstance(h, (list, tuple)) else h for h in headers]
    table_data = [header_labels]
    for row in data:
        table_data.append([str(row.get(k, '')) for k in header_keys])
    
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
    ]))
    elements.append(table)
    doc.build(elements)
    return buffer.getvalue()
