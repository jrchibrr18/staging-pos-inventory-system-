"""Dashboard and monitoring routes."""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from sqlalchemy import func

from models import Sale, SalesItem, Product, Customer
from services.pos_service import get_daily_summary
from services.inventory_service import get_low_stock_products, get_expiring_products

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    """Dashboard home with KPIs and charts."""
    summary = get_daily_summary()
    low_stock = get_low_stock_products()
    expiring = get_expiring_products(14)
    
    # Monthly revenue
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly = Sale.query.filter(Sale.created_at >= month_start).all()
    monthly_total = sum(float(s.total_amount) for s in monthly)
    
    # Best sellers (last 30 days)
    days_ago = datetime.now() - timedelta(days=30)
    top_items = (
        Sale.query.join(SalesItem).join(Product)
        .filter(Sale.created_at >= days_ago)
        .with_entities(Product.name, func.sum(SalesItem.quantity).label('qty'), func.sum(SalesItem.total).label('sales'))
        .group_by(Product.id)
        .order_by(func.sum(SalesItem.quantity).desc())
        .limit(10)
        .all()
    )
    
    return render_template('dashboard/index.html',
                          summary=summary,
                          monthly_total=monthly_total,
                          low_stock=low_stock,
                          expiring=expiring,
                          top_items=top_items)


@dashboard_bp.route('/api/kpis')
@login_required
def api_kpis():
    """REST API: Real-time KPIs."""
    today = datetime.now().date()
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    daily_sales = Sale.query.filter(func.date(Sale.created_at) == today).all()
    daily_total = sum(float(s.total_amount) for s in daily_sales)
    
    monthly_sales = Sale.query.filter(Sale.created_at >= month_start).all()
    monthly_total = sum(float(s.total_amount) for s in monthly_sales)
    
    low_stock_count = Product.query.filter(Product.quantity <= Product.min_stock).count()
    
    return jsonify({
        'daily_sales': daily_total,
        'daily_transactions': len(daily_sales),
        'monthly_revenue': monthly_total,
        'low_stock_alerts': low_stock_count
    })


@dashboard_bp.route('/api/sales-trend')
@login_required
def api_sales_trend():
    """REST API: Sales trend for charts (last 7 days)."""
    labels = []
    data = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).date()
        sales = Sale.query.filter(func.date(Sale.created_at) == d).all()
        total = sum(float(s.total_amount) for s in sales)
        labels.append(d.strftime('%a %d'))
        data.append(total)
    return jsonify({'labels': labels, 'data': data})


@dashboard_bp.route('/api/top-products')
@login_required
def api_top_products():
    """REST API: Top selling products (last 30 days)."""
    days_ago = datetime.now() - timedelta(days=30)
    items = (
        Sale.query.join(SalesItem).join(Product)
        .filter(Sale.created_at >= days_ago)
        .with_entities(Product.name, func.sum(SalesItem.quantity).label('qty'))
        .group_by(Product.id)
        .order_by(func.sum(SalesItem.quantity).desc())
        .limit(10)
        .all()
    )
    return jsonify({
        'labels': [i[0] for i in items],
        'data': [int(i[1]) for i in items]
    })
