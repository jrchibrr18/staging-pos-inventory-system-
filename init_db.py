"""Initialize database with sample data (optional). Run after first setup."""
import sys
from app import create_app
from models import db, User, Category, Product, Supplier

def init_sample_data():
    """Create sample categories and products if empty."""
    app = create_app()
    with app.app_context():
        if Category.query.first():
            print('Categories already exist. Skipping sample data.')
            return
        # Sample categories
        categories = [
            Category(name='Beverages', description='Drinks and refreshments'),
            Category(name='Snacks', description='Chips, crackers, candies'),
            Category(name='Groceries', description='Rice, canned goods, condiments'),
            Category(name='Personal Care', description='Soap, shampoo, toiletries'),
        ]
        for c in categories:
            db.session.add(c)
        db.session.commit()
        print('Created sample categories:', [c.name for c in categories])

        # Sample supplier
        supplier = Supplier(name='Sample Supplier', contact_person='Juan', phone='09171234567')
        db.session.add(supplier)
        db.session.commit()

        # Sample products
        products = [
            Product(name='Coke 8oz', category_id=1, selling_price=15, cost_price=10, quantity=50, unit='bottle', min_stock=10, supplier_id=1),
            Product(name='Pandesal (10pcs)', category_id=3, selling_price=25, cost_price=18, quantity=30, unit='pack', min_stock=5, supplier_id=1),
            Product(name='Chippy BBQ', category_id=2, selling_price=12, cost_price=8, quantity=100, unit='pack', min_stock=20, supplier_id=1),
            Product(name='Safeguard Soap', category_id=4, selling_price=35, cost_price=28, quantity=24, unit='bar', min_stock=5, supplier_id=1),
            Product(name='Royal 1.5L', category_id=1, selling_price=45, cost_price=38, quantity=20, unit='bottle', min_stock=5, supplier_id=1),
        ]
        for p in products:
            db.session.add(p)
        db.session.commit()
        print('Created sample products:', [p.name for p in products])
        print('Done! Login and start using the POS.')

if __name__ == '__main__':
    init_sample_data()
