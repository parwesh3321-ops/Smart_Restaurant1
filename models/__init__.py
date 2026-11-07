"""Amounts are integer paise; timestamps are UTC. Never use floats for billing."""
from datetime import datetime, timezone
import secrets
from database import db


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    __table_args__ = (db.CheckConstraint("role IN ('admin','waiter','kitchen')"),)


class Restaurant(db.Model):
    __tablename__ = 'restaurants'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    wifi_name = db.Column(db.String(80), nullable=False)
    wifi_password = db.Column(db.String(80), nullable=False)
    tax_bps = db.Column(db.Integer, default=500, nullable=False)
    public_base_url = db.Column(db.String(250), nullable=False)


class DiningTable(db.Model):
    __tablename__ = 'tables'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    number = db.Column(db.Integer, unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    zone = db.Column(db.String(40), nullable=False, default='Main dining')
    status = db.Column(db.String(20), nullable=False, default='available')
    token = db.Column(db.String(80), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    reservation_name = db.Column(db.String(100), default='', nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    __table_args__ = (db.CheckConstraint('capacity BETWEEN 1 AND 20'),
                      db.CheckConstraint("status IN ('available','occupied','reserved')"))


class Visit(db.Model):
    __tablename__ = 'visits'
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=False, index=True)
    guest_count = db.Column(db.Integer, nullable=False)
    opened_at = db.Column(db.DateTime, default=now, nullable=False)
    closed_at = db.Column(db.DateTime)
    table = db.relationship('DiningTable')
    orders = db.relationship('Order', back_populates='visit', order_by='Order.id')
    payments = db.relationship('Payment', back_populates='visit', order_by='Payment.id')
    splits = db.relationship('BillSplit', back_populates='visit', order_by='BillSplit.id')


class Category(db.Model):
    __tablename__ = 'menu_categories'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    name = db.Column(db.String(60), unique=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)


class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('menu_categories.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(80), nullable=False, default='pasta.jpg')
    vegetarian = db.Column(db.Boolean, default=True, nullable=False)
    available = db.Column(db.Boolean, default=True, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    category = db.relationship('Category')
    __table_args__ = (db.CheckConstraint('price > 0'),)


class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False, index=True)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    request_key = db.Column(db.String(80), unique=True, nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    notes = db.Column(db.String(300), default='', nullable=False)
    subtotal = db.Column(db.Integer, nullable=False)
    tax = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=now, nullable=False)
    visit = db.relationship('Visit', back_populates='orders')
    customer = db.relationship('Customer')
    table = db.relationship('DiningTable')
    items = db.relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')
    __table_args__ = (db.CheckConstraint("status IN ('pending','preparing','ready','served')"),)


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Integer, nullable=False)
    order = db.relationship('Order', back_populates='items')
    __table_args__ = (db.CheckConstraint('quantity BETWEEN 1 AND 50'),)


class WaiterRequest(db.Model):
    __tablename__ = 'waiter_requests'
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    kind = db.Column(db.String(30), nullable=False)
    note = db.Column(db.String(300), default='', nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)
    accepted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, nullable=False)
    visit = db.relationship('Visit')
    __table_args__ = (db.CheckConstraint("status IN ('pending','accepted','completed')"),)


class BillSplit(db.Model):
    __tablename__ = 'bill_splits'
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    label = db.Column(db.String(60), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    visit = db.relationship('Visit', back_populates='splits')
    __table_args__ = (db.CheckConstraint('amount > 0'),)


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    split_id = db.Column(db.Integer, db.ForeignKey('bill_splits.id'))
    reference = db.Column(db.String(80), unique=True, nullable=False)
    request_key = db.Column(db.String(80), unique=True, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    method = db.Column(db.String(30), default='demo', nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False, index=True)
    visit = db.relationship('Visit', back_populates='payments')
    __table_args__ = (db.CheckConstraint('amount > 0'), db.CheckConstraint("status IN ('success','failed')"))


class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    food_rating = db.Column(db.Integer, nullable=False)
    service_rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(1000), default='', nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    customer = db.relationship('Customer')
    visit = db.relationship('Visit')
    __table_args__ = (db.UniqueConstraint('visit_id', 'customer_id'), db.CheckConstraint('food_rating BETWEEN 1 AND 5'), db.CheckConstraint('service_rating BETWEEN 1 AND 5'))


class Reward(db.Model):
    __tablename__ = 'rewards'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    source = db.Column(db.String(100), unique=True, nullable=False)
    points = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(30), nullable=False)
    message = db.Column(db.String(250), nullable=False)
    read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)


class LoginAttempt(db.Model):
    __tablename__ = 'login_attempts'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
