"""POS transaction service."""
from datetime import datetime
from decimal import Decimal

from models import db, Sale, SalesItem, Payment, Product, InventoryLog, User


def generate_receipt_number():
    """Generate unique receipt number (e.g. RCP-20250215-0001)."""
    today = datetime.now().strftime('%Y%m%d')
    last = Sale.query.filter(Sale.receipt_number.like(f'RCP-{today}-%')).order_by(Sale.id.desc()).first()
    seq = 1 if not last else int(last.receipt_number.split('-')[-1]) + 1
    return f'RCP-{today}-{seq:04d}'


def add_item_to_cart(product_id, quantity, unit_price=None):
    """Get product for POS cart (validates stock)."""
    product = Product.query.get_or_404(product_id)
    if product.quantity < quantity:
        raise ValueError(f'Insufficient stock. Available: {product.quantity}')
    price = unit_price if unit_price is not None else float(product.selling_price)
    return {
        'id': product.id,
        'name': product.name,
        'sku': product.sku,
        'quantity': quantity,
        'unit_price': price,
        'total': quantity * price
    }


def create_sale(items, customer_id=None, customer_name=None, amount_received=0, 
                discount_amount=0, discount_percent=0, payment_method='cash', 
                cashier_id=None, notes=None):
    """Create a sale transaction and update inventory."""
    if not items:
        raise ValueError('Cart is empty')
    
    # Calculate totals
    subtotal = sum(item['quantity'] * item['unit_price'] for item in items)
    disc_amt = Decimal(str(discount_amount))
    disc_pct = Decimal(str(discount_percent))
    discount_total = disc_amt + (Decimal(str(subtotal)) * disc_pct / 100)
    total = Decimal(str(subtotal)) - discount_total
    
    # UPDATED: amount_received is now passed and saved
    sale = Sale(
        receipt_number=generate_receipt_number(),
        customer_id=customer_id,
        customer_name=customer_name,
        subtotal=Decimal(str(subtotal)),
        discount_amount=discount_total,
        discount_percent=disc_pct,
        total_amount=total,
        amount_received=Decimal(str(amount_received)), # <-- CRITICAL FIX
        payment_status='paid',
        cashier_id=cashier_id,
        notes=notes
    )
    
    db.session.add(sale)
    # Use flush to get sale.id before committing
    db.session.flush()
    
    for item in items:
        product = Product.query.get(item['id'])
        if not product:
            continue
            
        qty = item['quantity']
        price = Decimal(str(item['unit_price']))
        cost = Decimal(str(product.cost_price or 0))
        item_total = qty * price
        
        si = SalesItem(
            sale_id=sale.id,
            product_id=product.id,
            quantity=qty,
            unit_price=price,
            cost_price=cost,
            total=item_total
        )
        db.session.add(si)
        
        # --- STOCK LOGIC FIX ---
        # Capture current quantity specifically to avoid NULL IntegrityError
        prev_qty = product.quantity if product.quantity is not None else 0
        product.quantity = prev_qty - qty
        
        log = InventoryLog(
            product_id=product.id,
            type='out',
            quantity=-qty,
            previous_qty=prev_qty, # Fixed
            new_qty=product.quantity, # Fixed
            reference=str(sale.receipt_number), # Using receipt number for better tracking
            notes=f'Sale #{sale.receipt_number}',
            user_id=cashier_id
        )
        db.session.add(log)
    
    # Payment record
    pay = Payment(
        sale_id=sale.id, 
        amount=total, 
        payment_method=payment_method
    )
    db.session.add(pay)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Transaction failed: {str(e)}")
        
    return sale


def get_daily_summary(date=None):
    """Get daily sales summary."""
    d = date or datetime.now().date()
    sales = Sale.query.filter(
        db.func.date(Sale.created_at) == d
    ).all()
    total = sum(float(s.total_amount) for s in sales)
    return {'count': len(sales), 'total': total, 'date': d}