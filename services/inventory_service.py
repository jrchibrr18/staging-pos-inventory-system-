"""Inventory management service."""
from datetime import datetime
from decimal import Decimal

from models import db, Product, Category, Supplier, InventoryLog, User


def create_product(name, sku=None, barcode=None, category_id=None, supplier_id=None,
                   selling_price=0, cost_price=0, quantity=0, unit='pcs', min_stock=5, expiry_date=None):
    """Create a new product."""
    product = Product(
        name=name,
        sku=sku,
        barcode=barcode,
        category_id=category_id,
        supplier_id=supplier_id,
        selling_price=Decimal(str(selling_price)),
        cost_price=Decimal(str(cost_price)),
        quantity=int(quantity),
        unit=unit,
        min_stock=int(min_stock),
        expiry_date=expiry_date
    )
    db.session.add(product)
    db.session.commit()
    return product


def update_product(product_id, **kwargs):
    """Update product."""
    product = Product.query.get_or_404(product_id)
    for k, v in kwargs.items():
        if hasattr(product, k) and k not in ('id', 'created_at'):
            setattr(product, k, v)
    db.session.commit()
    return product


def stock_in(product_id, quantity, notes=None, user_id=None, reference=None):
    """Stock in (add inventory)."""
    product = Product.query.get_or_404(product_id)
    qty = int(quantity)
    prev = product.quantity
    product.quantity += qty
    
    log = InventoryLog(
        product_id=product.id,
        type='in',
        quantity=qty,
        previous_qty=prev,
        new_qty=product.quantity,
        reference=reference,
        notes=notes,
        user_id=user_id
    )
    db.session.add(log)
    db.session.commit()
    return product


def stock_out(product_id, quantity, notes=None, user_id=None, reference=None):
    """Stock out (reduce inventory)."""
    product = Product.query.get_or_404(product_id)
    qty = int(quantity)
    if product.quantity < qty:
        raise ValueError('Insufficient stock')
    prev = product.quantity
    product.quantity -= qty
    
    log = InventoryLog(
        product_id=product.id,
        type='out',
        quantity=-qty,
        previous_qty=prev,
        new_qty=product.quantity,
        reference=reference,
        notes=notes,
        user_id=user_id
    )
    db.session.add(log)
    db.session.commit()
    return product


def stock_adjustment(product_id, new_quantity, notes=None, user_id=None):
    """Adjust stock to a new quantity."""
    product = Product.query.get_or_404(product_id)
    new_qty = int(new_quantity)
    prev = product.quantity
    diff = new_qty - prev
    
    log = InventoryLog(
        product_id=product.id,
        type='adjustment',
        quantity=diff,
        previous_qty=prev,
        new_qty=new_qty,
        notes=notes,
        user_id=user_id
    )
    db.session.add(log)
    product.quantity = new_qty
    db.session.add(log)
    db.session.commit()
    return product


def get_low_stock_products(threshold=None):
    """Get products below minimum stock threshold."""
    thresh = threshold or 10
    return Product.query.filter(Product.quantity <= Product.min_stock).all()


def get_expiring_products(days=30):
    """Get products expiring within N days."""
    from datetime import timedelta
    end = datetime.now().date() + timedelta(days=days)
    return Product.query.filter(
        Product.expiry_date.isnot(None),
        Product.expiry_date <= end,
        Product.quantity > 0
    ).order_by(Product.expiry_date).all()
