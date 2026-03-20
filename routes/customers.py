"""Customer management routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required

from models import db, Customer, Sale

customers_bp = Blueprint('customers', __name__)


@customers_bp.route('/')
@login_required
def index():
    """Customer list."""
    search = request.args.get('q', '').strip()
    q = Customer.query
    if search:
        q = q.filter(Customer.name.ilike(f'%{search}%') | Customer.phone.ilike(f'%{search}%'))
    customers = q.order_by(Customer.name).paginate(
        page=request.args.get('page', 1, type=int), per_page=20
    )
    return render_template('customers/index.html', customers=customers)


@customers_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Create customer."""
    if request.method == 'POST':
        c = Customer(
            name=request.form.get('name', '').strip(),
            phone=request.form.get('phone', '').strip() or None,
            email=request.form.get('email', '').strip() or None,
            address=request.form.get('address', '').strip() or None,
            credit_limit=request.form.get('credit_limit', 0) or 0
        )
        db.session.add(c)
        db.session.commit()
        flash(f'Customer "{c.name}" created.', 'success')
        return redirect(url_for('customers.index'))
    return render_template('customers/form.html', customer=None)


@customers_bp.route('/<int:id>')
@login_required
def detail(id):
    """Customer detail with purchase history."""
    customer = Customer.query.get_or_404(id)
    sales = Sale.query.filter_by(customer_id=id).order_by(Sale.created_at.desc()).limit(50).all()
    return render_template('customers/detail.html', customer=customer, sales=sales)


@customers_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit customer."""
    customer = Customer.query.get_or_404(id)
    if request.method == 'POST':
        customer.name = request.form.get('name', '').strip()
        customer.phone = request.form.get('phone', '').strip() or None
        customer.email = request.form.get('email', '').strip() or None
        customer.address = request.form.get('address', '').strip() or None
        customer.credit_limit = request.form.get('credit_limit', 0) or 0
        db.session.commit()
        flash('Customer updated.', 'success')
        return redirect(url_for('customers.detail', id=id))
    return render_template('customers/form.html', customer=customer)
