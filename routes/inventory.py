"""Inventory management routes."""
import pandas as pd
from io import BytesIO
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from flask.views import MethodView

from sqlalchemy import or_, and_
from models import db, Product, Category, Supplier, InventoryLog
from services.inventory_service import (
    create_product, update_product, stock_in, stock_out, stock_adjustment,
    get_low_stock_products, get_expiring_products
)

inventory_bp = Blueprint('inventory', __name__)

# --- DECORATORS ---
def admin_required(f):
    """Decorator: require admin role."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated

# --- DASHBOARD & LISTS ---

@inventory_bp.route('/')
@login_required
def index():
    """Inventory dashboard."""
    products = Product.query.order_by(Product.name).paginate(
        page=request.args.get('page', 1, type=int),
        per_page=20
    )
    low_stock = get_low_stock_products()
    expiring = get_expiring_products(30)
    return render_template('inventory/index.html', products=products,
                          low_stock=low_stock, expiring=expiring)

# --- BULK ACTIONS (EXCEL) ---

@inventory_bp.route('/export/excel')
@login_required
def export_excel():
    """Export current inventory to Excel template/file."""
    products = Product.query.all()
    data = []
    for p in products:
        data.append({
            'Name': p.name,
            'SKU': p.sku or '',
            'Barcode': p.barcode or '',
            'Category': p.category.name if p.category else '',
            'Supplier': p.supplier.name if p.supplier else '',
            'Cost Price': p.cost_price,
            'Selling Price': p.selling_price,
            'Quantity': p.quantity,
            'Unit': p.unit or 'pcs',
            'Min Stock': p.min_stock
        })
    
    df = pd.DataFrame(data) if data else pd.DataFrame(columns=[
        'Name', 'SKU', 'Barcode', 'Category', 'Supplier', 
        'Cost Price', 'Selling Price', 'Quantity', 'Unit', 'Min Stock'
    ])
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f"inventory_export_{datetime.now().strftime('%Y%m%d')}.xlsx"
    )

@inventory_bp.route('/import/excel', methods=['POST'])
@login_required
def import_excel():
    """Import products from Excel file with safety checks for empty cells."""
    file = request.files.get('excel_file')
    if not file or not file.filename.endswith(('.xlsx', '.xls')):
        flash('Please upload a valid Excel file (.xlsx).', 'danger')
        return redirect(url_for('inventory.index'))

    try:
        df = pd.read_excel(file)
        df = df.dropna(subset=['Name'])
        
        count = 0
        skipped = 0
        for _, row in df.iterrows():
            name = str(row['Name']).strip()
            
            # HELPER: Safely clean strings and handle 'nan' from Excel
            def clean_val(key):
                val = row.get(key)
                if pd.isna(val): return None
                val_str = str(val).strip()
                # Fix for 'NoneType' error: Check content before calling .lower()
                if val_str and val_str.lower() == 'nan': return None
                return val_str if val_str else None

            sku = clean_val('SKU')
            barcode = clean_val('Barcode')
            cat_name = clean_val('Category')
            sup_name = clean_val('Supplier')
            
            # Prevent duplicates by checking Name or SKU (only if SKU exists)
            existing = Product.query.filter(
                or_(
                    Product.name == name, 
                    and_(Product.sku.isnot(None), Product.sku == sku) if sku else False
                )
            ).first()
            
            if existing:
                skipped += 1
                continue

            # Resolve Category/Supplier
            cat = Category.query.filter_by(name=cat_name).first() if cat_name else None
            sup = Supplier.query.filter_by(name=sup_name).first() if sup_name else None

            qty = int(row.get('Quantity', 0))

            # Create new product
            p = Product(
                name=name,
                sku=sku,
                barcode=barcode,
                category_id=cat.id if cat else None,
                supplier_id=sup.id if sup else None,
                cost_price=float(row.get('Cost Price', 0)),
                selling_price=float(row.get('Selling Price', 0)),
                quantity=qty,
                unit=str(row.get('Unit', 'pcs')),
                min_stock=int(row.get('Min Stock', 5))
            )
            db.session.add(p)
            db.session.flush() 

            # Create initial inventory log
            log = InventoryLog(
                product_id=p.id,
                user_id=current_user.id,
                type='adjustment',
                quantity=qty,
                previous_qty=0,
                new_qty=qty,
                notes="Initial Bulk Import"
            )
            db.session.add(log)
            count += 1

        db.session.commit()
        msg = f'Successfully imported {count} items.'
        if skipped > 0:
            msg += f' ({skipped} existing items skipped).'
        flash(msg, 'success')
        
    except Exception as e:
        db.session.rollback() # Fixes PendingRollbackError
        flash(f'Import Error: {str(e)}', 'danger')
    
    return redirect(url_for('inventory.index'))

# --- PRODUCT ROUTES ---

@inventory_bp.route('/products')
@login_required
def products():
    """Product list with search and filter."""
    category_id = request.args.get('category', type=int)
    search = request.args.get('q', '').strip()
    
    q = Product.query
    if category_id:
        q = q.filter(Product.category_id == category_id)
    if search:
        q = q.filter(or_(
            Product.name.ilike(f'%{search}%'),
            and_(Product.sku.isnot(None), Product.sku.ilike(f'%{search}%')),
            and_(Product.barcode.isnot(None), Product.barcode.ilike(f'%{search}%'))
        ))
    
    products = q.order_by(Product.name).paginate(page=request.args.get('page', 1, type=int), per_page=20)
    categories = Category.query.order_by(Category.name).all()
    return render_template('inventory/products.html', products=products, categories=categories)

@inventory_bp.route('/products/new', methods=['GET', 'POST'])
@login_required
def product_new():
    """Create product manually."""
    if request.method == 'POST':
        try:
            # Handle empty strings as None for unique constraints
            sku = request.form.get('sku', '').strip() or None
            barcode = request.form.get('barcode', '').strip() or None
            
            product = create_product(
                name=request.form.get('name', '').strip(),
                sku=sku,
                barcode=barcode,
                category_id=request.form.get('category_id') or None,
                supplier_id=request.form.get('supplier_id') or None,
                selling_price=request.form.get('selling_price', 0),
                cost_price=request.form.get('cost_price', 0),
                quantity=request.form.get('quantity', 0),
                unit=request.form.get('unit', 'pcs'),
                min_stock=request.form.get('min_stock', 5),
                expiry_date=request.form.get('expiry_date') or None
            )
            flash(f'Product "{product.name}" created.', 'success')
            return redirect(url_for('inventory.products'))
        except Exception as e:
            db.session.rollback()
            flash(str(e), 'danger')
    
    categories = Category.query.order_by(Category.name).all()
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('inventory/product_form.html', product=None, categories=categories, suppliers=suppliers)

@inventory_bp.route('/products/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def product_edit(id):
    """Edit product manually."""
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        try:
            sku = request.form.get('sku', '').strip() or None
            barcode = request.form.get('barcode', '').strip() or None

            update_product(product.id,
                name=request.form.get('name', '').strip(),
                sku=sku,
                barcode=barcode,
                category_id=request.form.get('category_id') or None,
                supplier_id=request.form.get('supplier_id') or None,
                selling_price=request.form.get('selling_price', 0),
                cost_price=request.form.get('cost_price', 0),
                min_stock=request.form.get('min_stock', 5),
                expiry_date=request.form.get('expiry_date') or None,
                unit=request.form.get('unit', 'pcs')
            )
            flash('Product updated.', 'success')
            return redirect(url_for('inventory.products'))
        except Exception as e:
            db.session.rollback() # Essential to clear the failed transaction
            flash(str(e), 'danger')
    
    categories = Category.query.order_by(Category.name).all()
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('inventory/product_form.html', product=product, categories=categories, suppliers=suppliers)

# --- STOCK OPERATIONS ---

@inventory_bp.route('/stock-in/<int:id>', methods=['GET', 'POST'])
@login_required
def stock_in_view(id):
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        qty = request.form.get('quantity', 0, type=int)
        notes = request.form.get('notes', '').strip()
        if qty <= 0:
            flash('Quantity must be positive.', 'danger')
        else:
            stock_in(product.id, qty, notes=notes or None, user_id=current_user.id)
            flash(f'Added {qty} {product.unit} to {product.name}.', 'success')
            return redirect(url_for('inventory.products'))
    return render_template('inventory/stock_in.html', product=product)

@inventory_bp.route('/stock-out/<int:id>', methods=['GET', 'POST'])
@login_required
def stock_out_view(id):
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        qty = request.form.get('quantity', 0, type=int)
        notes = request.form.get('notes', '').strip()
        if qty <= 0:
            flash('Quantity must be positive.', 'danger')
        elif qty > product.quantity:
            flash('Insufficient stock.', 'danger')
        else:
            stock_out(product.id, qty, notes=notes or None, user_id=current_user.id)
            flash(f'Removed {qty} {product.unit} from {product.name}.', 'success')
            return redirect(url_for('inventory.products'))
    return render_template('inventory/stock_out.html', product=product)

# --- CATEGORIES, SUPPLIERS, AND LOGS ---

@inventory_bp.route('/categories')
@login_required
def categories():
    categories = Category.query.order_by(Category.name).all()
    return render_template('inventory/categories.html', categories=categories)

@inventory_bp.route('/categories/new', methods=['GET', 'POST'])
@login_required
def category_new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        desc = request.form.get('description', '').strip()
        if name:
            c = Category(name=name, description=desc or None)
            db.session.add(c)
            db.session.commit()
            flash(f'Category "{name}" created.', 'success')
            return redirect(url_for('inventory.categories'))
        flash('Name is required.', 'danger')
    return render_template('inventory/category_form.html', category=None)

@inventory_bp.route('/categories/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def category_edit(id):
    category = Category.query.get_or_404(id)
    if request.method == 'POST':
        category.name = request.form.get('name', '').strip()
        category.description = request.form.get('description', '').strip()
        db.session.commit()
        flash('Category updated.', 'success')
        return redirect(url_for('inventory.categories'))
    return render_template('inventory/category_form.html', category=category)

@inventory_bp.route('/suppliers')
@login_required
def suppliers():
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('inventory/suppliers.html', suppliers=suppliers)

@inventory_bp.route('/suppliers/new', methods=['GET', 'POST'])
@login_required
def supplier_new():
    if request.method == 'POST':
        s = Supplier(
            name=request.form.get('name', '').strip(),
            contact_person=request.form.get('contact_person', '').strip() or None,
            phone=request.form.get('phone', '').strip() or None,
            email=request.form.get('email', '').strip() or None,
            address=request.form.get('address', '').strip() or None
        )
        db.session.add(s)
        db.session.commit()
        flash('Supplier created.', 'success')
        return redirect(url_for('inventory.suppliers'))
    return render_template('inventory/supplier_form.html', supplier=None)
                      
@inventory_bp.route('/suppliers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def supplier_edit(id):
    supplier = Supplier.query.get_or_404(id)
    if request.method == 'POST':
        supplier.name = request.form.get('name', '').strip()
        supplier.contact_person = request.form.get('contact_person', '').strip() or None
        supplier.phone = request.form.get('phone', '').strip() or None
        supplier.email = request.form.get('email', '').strip() or None
        supplier.address = request.form.get('address', '').strip() or None
        db.session.commit()
        flash('Supplier updated.', 'success')
        return redirect(url_for('inventory.suppliers'))
    return render_template('inventory/supplier_form.html', supplier=supplier)

@inventory_bp.route('/logs')
@login_required
def logs():
    logs = InventoryLog.query.order_by(InventoryLog.created_at.desc()).paginate(
        page=request.args.get('page', 1, type=int), per_page=30
    )
    return render_template('inventory/logs.html', logs=logs)