"""Reports and export routes."""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, send_file, jsonify
from flask_login import login_required
import io

from services.report_service import (
    get_sales_report,
    get_inventory_movement_report,
    get_best_selling,
    get_profit_report,
    export_csv,
    export_excel,
    export_pdf
)

reports_bp = Blueprint('reports', __name__)


def get_date_range():
    """Get start/end date from request or default to this month."""
    today = datetime.now().date()
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    start = datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else today.replace(day=1)
    end = datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else today
    return start, end


@reports_bp.route('/')
@login_required
def index():
    """Reports home."""
    start, end = get_date_range()
    sales_data = get_sales_report(start, end)
    return render_template('reports/index.html', sales_data=sales_data, start=start, end=end)


@reports_bp.route('/sales')
@login_required
def sales():
    """Sales report."""
    start, end = get_date_range()
    sales_data = get_sales_report(start, end)
    total = sum(r['total'] for r in sales_data)
    return render_template('reports/sales.html', sales_data=sales_data, start=start, end=end, total=total)


@reports_bp.route('/inventory')
@login_required
def inventory():
    """Inventory movement report."""
    start, end = get_date_range()
    movement_data = get_inventory_movement_report(start, end)
    return render_template('reports/inventory.html', movement_data=movement_data, start=start, end=end)


@reports_bp.route('/profit')
@login_required
def profit():
    """Profit and margin report: cost vs revenue, total profit."""
    start, end = get_date_range()
    profit_data = get_profit_report(start, end)
    best = get_best_selling(start, end, limit=20)
    return render_template('reports/profit.html', best_selling=best,
                          start=start, end=end, **profit_data)


SALES_HEADERS = ['receipt', 'date', 'customer', 'products', 'subtotal', 'discount', 'total', 'status']
INVENTORY_HEADERS = ['date', 'product', 'type', 'quantity', 'previous', 'new', 'notes']


@reports_bp.route('/export/sales/csv')
@login_required
def export_sales_csv():
    """Export sales to CSV."""
    start, end = get_date_range()
    data = get_sales_report(start, end)
    csv_content = export_csv(data, SALES_HEADERS)
    buffer = io.BytesIO(csv_content.encode('utf-8'))
    return send_file(buffer, mimetype='text/csv', as_attachment=True,
                     download_name=f'sales_report_{start}_{end}.csv')


@reports_bp.route('/export/sales/excel')
@login_required
def export_sales_excel():
    """Export sales to Excel."""
    start, end = get_date_range()
    data = get_sales_report(start, end)
    xlsx = export_excel(data, SALES_HEADERS, 'Sales Report')
    return send_file(io.BytesIO(xlsx),
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=f'sales_report_{start}_{end}.xlsx')


@reports_bp.route('/export/sales/pdf')
@login_required
def export_sales_pdf():
    """Export sales to PDF."""
    start, end = get_date_range()
    data = get_sales_report(start, end)
    pdf = export_pdf(data, SALES_HEADERS, title=f'Sales Report ({start} to {end})')
    return send_file(io.BytesIO(pdf), mimetype='application/pdf', as_attachment=True,
                     download_name=f'sales_report_{start}_{end}.pdf')


@reports_bp.route('/export/inventory/csv')
@login_required
def export_inventory_csv():
    """Export inventory movement to CSV."""
    start, end = get_date_range()
    data = get_inventory_movement_report(start, end)
    csv_content = export_csv(data, INVENTORY_HEADERS)
    buffer = io.BytesIO(csv_content.encode('utf-8'))
    return send_file(buffer, mimetype='text/csv', as_attachment=True,
                     download_name=f'inventory_report_{start}_{end}.csv')


@reports_bp.route('/export/inventory/excel')
@login_required
def export_inventory_excel():
    """Export inventory movement to Excel."""
    start, end = get_date_range()
    data = get_inventory_movement_report(start, end)
    xlsx = export_excel(data, INVENTORY_HEADERS, 'Inventory Movement')
    return send_file(io.BytesIO(xlsx),
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=f'inventory_report_{start}_{end}.xlsx')


@reports_bp.route('/export/inventory/pdf')
@login_required
def export_inventory_pdf():
    """Export inventory movement to PDF."""
    start, end = get_date_range()
    data = get_inventory_movement_report(start, end)
    pdf = export_pdf(data, INVENTORY_HEADERS, title=f'Inventory Movement Report ({start} to {end})')
    return send_file(io.BytesIO(pdf), mimetype='application/pdf', as_attachment=True,
                     download_name=f'inventory_report_{start}_{end}.pdf')


@reports_bp.route('/export/profit/csv')
@login_required
def export_profit_csv():
    """Export profit report to CSV."""
    start, end = get_date_range()
    data = get_profit_report(start, end)
    rows = [{'revenue': data['revenue'], 'cost': data['cost'], 'profit': data['profit'], 'margin_pct': data['margin_pct']}]
    csv_content = export_csv(rows, ['revenue', 'cost', 'profit', 'margin_pct'])
    buffer = io.BytesIO(csv_content.encode('utf-8'))
    return send_file(buffer, mimetype='text/csv', as_attachment=True,
                     download_name=f'profit_report_{start}_{end}.csv')


@reports_bp.route('/export/profit/excel')
@login_required
def export_profit_excel():
    """Export profit report to Excel."""
    start, end = get_date_range()
    data = get_profit_report(start, end)
    rows = [{'revenue': data['revenue'], 'cost': data['cost'], 'profit': data['profit'], 'margin_pct': data['margin_pct']}]
    xlsx = export_excel(rows, [('revenue','Revenue'), ('cost','Cost'), ('profit','Profit'), ('margin_pct','Margin %')], 'Profit Report')
    return send_file(io.BytesIO(xlsx),
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=f'profit_report_{start}_{end}.xlsx')


@reports_bp.route('/export/profit/pdf')
@login_required
def export_profit_pdf():
    """Export profit report to PDF."""
    start, end = get_date_range()
    data = get_profit_report(start, end)
    rows = [{'revenue': data['revenue'], 'cost': data['cost'], 'profit': data['profit'], 'margin_pct': data['margin_pct']}]
    pdf = export_pdf(rows, [('revenue','Revenue'), ('cost','Cost'), ('profit','Profit'), ('margin_pct','Margin %')],
                    title=f'Profit Report ({start} to {end})')
    return send_file(io.BytesIO(pdf), mimetype='application/pdf', as_attachment=True,
                     download_name=f'profit_report_{start}_{end}.pdf')
