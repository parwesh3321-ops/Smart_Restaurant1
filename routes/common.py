from decimal import Decimal, InvalidOperation
from functools import wraps
import re
from flask import session, abort, request
from sqlalchemy import select, func
from database import db
from models import User, Visit, Customer, Reward, Order, Payment, Notification


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            user = db.session.get(User, session.get('user_id')) if session.get('user_id') else None
            if not user:
                abort(401, description='Please sign in to continue.')
            if user.role not in roles:
                abort(403, description='Your role cannot perform this action.')
            return fn(*args, **kwargs)
        return wrapped
    return decorator


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description='Send a JSON object.')
    return data


def string(data, key, minimum=1, maximum=100):
    value = data.get(key, '')
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        abort(400, description=f'{key.replace("_", " ").title()} must contain {minimum}–{maximum} characters.')
    return value.strip()


def integer(data, key, minimum=1, maximum=1000000):
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        abort(400, description=f'{key.replace("_", " ").title()} must be a whole number between {minimum} and {maximum}.')
    return value


def boolean(data, key, default=False):
    value = data.get(key, default)
    if not isinstance(value, bool):
        abort(400, description=f'{key} must be true or false.')
    return value


def money(value):
    try:
        if isinstance(value, bool):
            raise ValueError()
        number = Decimal(str(value))
        if not number.is_finite() or number <= 0 or number > 1000000 or number * 100 != (number * 100).to_integral_value():
            raise ValueError()
        return int(number * 100)
    except (ValueError, InvalidOperation, TypeError):
        abort(400, description='Enter a positive amount with no more than two decimal places.')


def key(data):
    value = string(data, 'request_key', 16, 80)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        abort(400, description='Invalid request key.')
    return value


def get_or_404(model, ident):
    obj = db.session.get(model, ident)
    if obj is None:
        abort(404, description='This record could not be found.')
    return obj


def active_visit(table_id):
    return db.session.scalar(select(Visit).where(Visit.table_id == table_id, Visit.closed_at.is_(None)))


def guest(open_only=False):
    cid, vid = session.get('customer_id'), session.get('visit_id')
    customer = db.session.get(Customer, cid) if cid else None
    visit = db.session.get(Visit, vid) if vid else None
    if not customer or not visit:
        abort(401, description='Scan your table QR and join the table first.')
    if open_only and visit.closed_at:
        abort(409, description='This dining session has ended. Please join a new table session.')
    return customer, visit


def iso(value):
    return value.isoformat() + 'Z' if value else None


def order_json(order):
    return dict(id=order.id, table_number=order.table.number, visit_id=order.visit_id,
                customer=order.customer.name, status=order.status, notes=order.notes,
                subtotal=order.subtotal, tax=order.tax, total=order.total,
                created_at=iso(order.created_at), updated_at=iso(order.updated_at),
                items=[dict(id=i.id, menu_item_id=i.menu_item_id, name=i.name, quantity=i.quantity, unit_price=i.unit_price) for i in order.items])


def payment_json(p):
    return dict(id=p.id, reference=p.reference, amount=p.amount, status=p.status,
                split_id=p.split_id, table_number=p.visit.table.number, visit_id=p.visit_id, created_at=iso(p.created_at))


def bill_json(visit):
    subtotal = sum(o.subtotal for o in visit.orders)
    tax = sum(o.tax for o in visit.orders)
    total = subtotal + tax
    paid = sum(p.amount for p in visit.payments if p.status == 'success')
    return dict(visit_id=visit.id, table_number=visit.table.number, subtotal=subtotal, tax=tax, total=total,
                paid=paid, remaining=total-paid, closed=bool(visit.closed_at),
                orders=[order_json(o) for o in visit.orders],
                payments=[payment_json(p) for p in visit.payments],
                splits=[dict(id=s.id, label=s.label, amount=s.amount,
                             paid=sum(p.amount for p in visit.payments if p.split_id == s.id and p.status == 'success')) for s in visit.splits])


def points(customer_id):
    return db.session.scalar(select(func.coalesce(func.sum(Reward.points), 0)).where(Reward.customer_id == customer_id))


def notify(kind, message):
    db.session.add(Notification(kind=kind, message=message))
