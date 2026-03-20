"""POS routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from sqlalchemy import or_, and_
from models import Sale, SalesItem, Product, Category, Customer
from services.pos_service import add_item_to_cart, create_sale, get_daily_summary

pos_bp = Blueprint('pos', __name__)


@pos_bp.route('/')
@login_required
def index():
    """POS main interface."""
    categories = Category.query.order_by(Category.name).all()
    products = Product.query.filter(Product.quantity > 0).order_by(Product.name).all()
    summary = get_daily_summary()
    return render_template('pos/index.html', categories=categories, products=products, summary=summary)


@pos_bp.route('/api/products')
@login_required
def api_products():
    """REST API: List products for POS (with optional category filter)."""
    category_id = request.args.get('category_id', type=int)
    q = Product.query.filter(Product.quantity > 0)
    if category_id:
        q = q.filter(Product.category_id == category_id)
    products = q.order_by(Product.name).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'sku': p.sku,
        'barcode': p.barcode,
        'price': float(p.selling_price),
        'quantity': p.quantity,
        'unit': p.unit
    } for p in products])


@pos_bp.route('/api/product/<int:id>')
@login_required
def api_product(id):
    """REST API: Get single product by ID or barcode."""
    product = Product.query.get_or_404(id)
    if product.quantity <= 0:
        return jsonify({'error': 'Out of stock'}), 400
    return jsonify({
        'id': product.id,
        'name': product.name,
        'sku': product.sku,
        'barcode': product.barcode,
        'price': float(product.selling_price),
        'quantity': product.quantity,
        'unit': product.unit
    })


@pos_bp.route('/api/customers')
@login_required
def api_customers():
    """REST API: Search customers for POS dropdown."""
    q = request.args.get('q', '').strip()
    if not q:
        customers = Customer.query.order_by(Customer.name).limit(50).all()
    else:
        customers = Customer.query.filter(
            or_(
                Customer.name.ilike(f'%{q}%'),
                and_(Customer.phone.isnot(None), Customer.phone.ilike(f'%{q}%'))
            )
        ).order_by(Customer.name).limit(20).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'phone': c.phone or ''
    } for c in customers])


@pos_bp.route('/api/product/barcode/<barcode>')
@login_required
def api_product_by_barcode(barcode):
    """REST API: Get product by barcode."""
    product = Product.query.filter_by(barcode=barcode).first()
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    if product.quantity <= 0:
        return jsonify({'error': 'Out of stock'}), 400
    return jsonify({
        'id': product.id,
        'name': product.name,
        'sku': product.sku,
        'barcode': product.barcode,
        'price': float(product.selling_price),
        'quantity': product.quantity,
        'unit': product.unit
    })


@pos_bp.route('/api/sale', methods=['POST'])
@login_required
def api_create_sale():
    """REST API: Create sale from cart."""
    data = request.get_json() or {}
    items = data.get('items', [])
    customer_id = data.get('customer_id')
    customer_name = data.get('customer_name', '').strip()
    
    # --- UPDATED: Capture amount_received from the frontend ---
    amount_received = data.get('amount_received', 0)
    
    discount_amount = data.get('discount_amount', 0) or 0
    discount_percent = data.get('discount_percent', 0) or 0
    payment_method = data.get('payment_method', 'cash')
    notes = data.get('notes', '').strip()
    
    if not items:
        return jsonify({'error': 'Cart is empty'}), 400
    
    try:
        # --- UPDATED: Pass amount_received to the service function ---
        sale = create_sale(
            items=items,
            customer_id=customer_id,
            customer_name=customer_name,
            amount_received=amount_received,  # Added this
            discount_amount=discount_amount,
            discount_percent=discount_percent,
            payment_method=payment_method,
            cashier_id=current_user.id,
            notes=notes
        )
        
        # Calculate change for the response if needed
        change = float(sale.amount_received) - float(sale.total_amount)
        
        return jsonify({
            'success': True,
            'sale_id': sale.id,
            'receipt_number': sale.receipt_number,
            'total': float(sale.total_amount),
            'amount_received': float(sale.amount_received),
            'change': round(change, 2)
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@pos_bp.route('/receipt/<int:sale_id>')
@login_required
def receipt(sale_id):
    """Print/view receipt."""
    sale = Sale.query.get_or_404(sale_id)
    # The template 'pos/receipt.html' will now have a sale object 
    # that contains the correct 'amount_received'
    return render_template('pos/receipt.html', sale=sale)