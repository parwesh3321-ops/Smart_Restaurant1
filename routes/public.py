"""Public entry points make the guest dining experience easy to discover."""
from flask import Blueprint, current_app, render_template, session
from sqlalchemy import select
from database import db
from models import Customer, DiningTable, Restaurant, Visit

public = Blueprint('public', __name__)


def current_guest_visit():
    """Offer a continuation only for the browser's existing, open visit."""
    customer_id, visit_id = session.get('customer_id'), session.get('visit_id')
    if not customer_id or not visit_id or not db.session.get(Customer, customer_id):
        return None
    visit = db.session.get(Visit, visit_id)
    if visit and not visit.closed_at and visit.table.active:
        return visit
    return None


@public.get('/')
def home():
    return render_template('welcome.html', restaurant=db.session.scalar(select(Restaurant)),
                           current_visit=current_guest_visit())


@public.get('/customer')
def customer_entry():
    # The table directory is a convenience for the local demo. In a real service,
    # disable it and let customers use the unique QR already on their table.
    picker_enabled = current_app.config['ENABLE_TABLE_PICKER']
    tables = db.session.scalars(select(DiningTable).where(
        DiningTable.active.is_(True)).order_by(DiningTable.zone, DiningTable.number)).all() if picker_enabled else []
    return render_template('customer_entry.html', restaurant=db.session.scalar(select(Restaurant)),
                           tables=tables, picker_enabled=picker_enabled,
                           current_visit=current_guest_visit())
