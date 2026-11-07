import secrets
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Blueprint, render_template, session, jsonify, abort
from sqlalchemy import select, delete
from database import db
from models import (Restaurant, DiningTable, Visit, Category, MenuItem, Customer, Order,
                    OrderItem, WaiterRequest, Payment, BillSplit, Review, Reward, now)
from .common import (payload, string, integer, money, key, get_or_404, active_visit,
                     guest, order_json, bill_json, points, notify, iso, payment_json)
from .staff import menu_json

customer = Blueprint('customer', __name__)
QUESTIONS = [
    ('Which herb is traditionally used in pesto?', ['Basil', 'Mint', 'Dill'], 0),
    ('What is the main ingredient in hummus?', ['Potato', 'Chickpeas', 'Rice'], 1),
    ('Which drink is made from espresso and steamed milk?', ['Lemonade', 'Iced tea', 'Cappuccino'], 2),
    ('Which spice gives turmeric rice its golden colour?', ['Turmeric', 'Cinnamon', 'Pepper'], 0),
    ('Which fruit is used in guacamole?', ['Mango', 'Avocado', 'Apple'], 1),
]


def today():
    return datetime.now(ZoneInfo('Asia/Kolkata')).date()


def game_data(customer_id):
    day = today()
    index = day.toordinal() % len(QUESTIONS)
    question, options, _ = QUESTIONS[index]
    source = f'game:{customer_id}:{day.isoformat()}'
    played = db.session.scalar(select(Reward).where(Reward.source == source))
    return dict(question=question, options=options, played=bool(played), earned=played.points if played else None)


@customer.get('/menu/<token>')
def menu_page(token):
    table = db.session.scalar(select(DiningTable).where(DiningTable.token == token, DiningTable.active.is_(True)))
    if not table:
        abort(404, description='This table QR is no longer available. Ask a member of staff.')
    restaurant = db.session.get(Restaurant, table.restaurant_id)
    return render_template('customer.html', table=table, restaurant=restaurant)


@customer.get('/api/menu/<token>')
def public_menu(token):
    table = db.session.scalar(select(DiningTable).where(DiningTable.token == token, DiningTable.active.is_(True)))
    if not table:
        abort(404)
    restaurant = db.session.get(Restaurant, table.restaurant_id)
    return jsonify(restaurant=dict(name=restaurant.name, tax_bps=restaurant.tax_bps),
        table=dict(number=table.number, capacity=table.capacity, status=table.status),
        categories=[dict(id=c.id, name=c.name) for c in db.session.scalars(select(Category).order_by(Category.sort_order, Category.id))],
        items=[menu_json(m) for m in db.session.scalars(select(MenuItem).where(MenuItem.active.is_(True)).order_by(MenuItem.id))])


@customer.post('/api/guest/join')
def join():
    data = payload()
    token = string(data, 'token', 10, 80)
    table = db.session.scalar(select(DiningTable).where(DiningTable.token == token, DiningTable.active.is_(True)))
    if not table:
        abort(404, description='Invalid table QR.')
    if table.status == 'reserved':
        abort(409, description='This table is reserved. Please ask staff to seat your group first.')
    name = string(data, 'name', 1, 100)
    count = integer(data, 'guest_count', 1, table.capacity)
    customer_record = db.session.get(Customer, session.get('customer_id')) if session.get('customer_id') else None
    if not customer_record:
        customer_record = Customer(name=name)
        db.session.add(customer_record)
        db.session.flush()
    else:
        customer_record.name = name
    visit = active_visit(table.id)
    if not visit:
        visit = Visit(table_id=table.id, guest_count=count)
        db.session.add(visit)
        db.session.flush()
    # A second phone joins the same group; it does not overwrite the party size.
    table.status = 'occupied'
    session['customer_id'] = customer_record.id
    session['visit_id'] = visit.id
    session.permanent = True
    db.session.commit()
    return jsonify(message='Welcome to your table.', visit_id=visit.id), 201


@customer.get('/api/guest/state')
def state():
    person, visit = guest()
    restaurant = db.session.get(Restaurant, visit.table.restaurant_id)
    return jsonify(customer=dict(id=person.id, name=person.name, points=points(person.id)),
        table=dict(number=visit.table.number, guests=visit.guest_count, token=visit.table.token),
        bill=bill_json(visit), wifi=dict(name=restaurant.wifi_name, password=restaurant.wifi_password),
        requests=[dict(id=r.id, kind=r.kind, status=r.status, created_at=iso(r.created_at)) for r in db.session.scalars(select(WaiterRequest).where(WaiterRequest.visit_id == visit.id).order_by(WaiterRequest.id.desc()))],
        reviewed=bool(db.session.scalar(select(Review.id).where(Review.visit_id == visit.id, Review.customer_id == person.id))),
        game=game_data(person.id), rewards=[dict(points=r.points, description=r.description, created_at=iso(r.created_at)) for r in db.session.scalars(select(Reward).where(Reward.customer_id == person.id).order_by(Reward.id.desc()).limit(20))])


@customer.post('/api/guest/orders')
def place_order():
    person, visit = guest(True)
    data = payload()
    request_key = key(data)
    existing = db.session.scalar(select(Order).where(Order.request_key == request_key))
    if existing:
        if existing.customer_id != person.id or existing.visit_id != visit.id:
            abort(409, description='Request key already used.')
        return jsonify(order=order_json(existing)), 200
    if visit.splits or any(p.status == 'success' for p in visit.payments):
        abort(409, description='Checkout has started. Finish this bill before starting another dining session.')
    lines = data.get('items')
    if not isinstance(lines, list) or not 1 <= len(lines) <= 50 or not all(isinstance(line, dict) for line in lines):
        abort(400, description='Your cart must contain 1–50 different items.')
    items, seen, subtotal = [], set(), 0
    for line in lines:
        ident = integer(line, 'id')
        qty = integer(line, 'quantity', 1, 50)
        if ident in seen:
            abort(400, description='Combine duplicate items into one cart line.')
        seen.add(ident)
        item = get_or_404(MenuItem, ident)
        if not item.active or not item.available:
            abort(409, description=f'{item.name} is currently unavailable. Remove it from your cart.')
        subtotal += item.price * qty
        items.append(OrderItem(menu_item_id=item.id, name=item.name, quantity=qty, unit_price=item.price))
    restaurant = db.session.get(Restaurant, visit.table.restaurant_id)
    tax = (subtotal * restaurant.tax_bps + 5000) // 10000
    order = Order(visit_id=visit.id, table_id=visit.table_id, customer_id=person.id,
                  request_key=request_key, subtotal=subtotal, tax=tax, total=subtotal+tax,
                  notes=string(data, 'notes', 0, 300), items=items)
    db.session.add(order)
    db.session.flush()
    visit.table.status = 'occupied'
    notify('order', f'New order #{order.id:04} · Table {visit.table.number:02}')
    db.session.commit()
    return jsonify(order=order_json(order)), 201


@customer.post('/api/guest/requests')
def call_waiter():
    person, visit = guest(True)
    data = payload()
    kind = string(data, 'kind', 1, 30)
    if kind not in ('service', 'water', 'bill'):
        abort(400, description='Choose service, water or bill.')
    existing = db.session.scalar(select(WaiterRequest).where(WaiterRequest.visit_id == visit.id, WaiterRequest.kind == kind, WaiterRequest.status != 'completed'))
    if existing:
        return jsonify(message='Staff already have your request.', id=existing.id)
    req = WaiterRequest(visit_id=visit.id, customer_id=person.id, kind=kind, note=string(data, 'note', 0, 300))
    db.session.add(req)
    notify('service', f'Table {visit.table.number:02} requested {kind}.')
    db.session.commit()
    return jsonify(message='Your waiter has been notified.', id=req.id), 201


@customer.post('/api/guest/splits')
def split_bill():
    _, visit = guest(True)
    data = payload()
    bill = bill_json(visit)
    if bill['paid'] or any(p.split_id for p in visit.payments):
        abort(409, description='Splits cannot change after a payment attempt against a share or a successful payment.')
    if bill['total'] <= 0:
        abort(409, description='Place an order before splitting the bill.')
    if data.get('mode') == 'equal':
        count = integer(data, 'count', 2, 20)
        base, extra = divmod(bill['total'], count)
        entries = [(f'Guest {i+1}', base + (1 if i < extra else 0)) for i in range(count)]
    elif data.get('mode') == 'custom':
        shares = data.get('shares')
        if not isinstance(shares, list) or not 2 <= len(shares) <= 20 or not all(isinstance(s, dict) for s in shares):
            abort(400, description='Add 2–20 custom shares.')
        entries = [(string(s, 'label', 1, 60), money(s.get('amount'))) for s in shares]
        if sum(a for _, a in entries) != bill['total']:
            abort(400, description='Custom shares must add up to the full bill, including tax.')
    else:
        abort(400, description='Choose equal or custom splitting.')
    if any(amount <= 0 for _, amount in entries):
        abort(400, description='The bill is too small for that many shares.')
    for split in list(visit.splits):
        db.session.delete(split)
    db.session.flush()
    db.session.add_all([BillSplit(visit_id=visit.id, label=label, amount=amount) for label, amount in entries])
    db.session.commit()
    return jsonify(bill=bill_json(visit)), 201


@customer.post('/api/guest/payments')
def pay():
    person, visit = guest(True)
    data = payload()
    request_key = key(data)
    existing = db.session.scalar(select(Payment).where(Payment.request_key == request_key))
    if existing:
        if existing.customer_id != person.id or existing.visit_id != visit.id:
            abort(409, description='Request key already used.')
        return jsonify(payment=payment_json(existing), bill=bill_json(visit))
    amount = money(data.get('amount'))
    bill = bill_json(visit)
    if not bill['total'] or amount > bill['remaining']:
        abort(409, description='Payment exceeds the current remaining balance. Refresh the bill.')
    outcome = string(data, 'outcome', 1, 20)
    if outcome not in ('success', 'failed'):
        abort(400, description='Choose a demo success or failure result.')
    split_id = None
    if visit.splits:
        split_id = integer(data, 'split_id')
        split = next((s for s in bill['splits'] if s['id'] == split_id), None)
        if not split or amount > split['amount'] - split['paid']:
            abort(409, description='Payment exceeds this share’s remaining balance.')
    elif data.get('split_id') is not None:
        abort(400, description='This bill has no payment shares.')
    payment = Payment(visit_id=visit.id, customer_id=person.id, split_id=split_id, request_key=request_key,
                      reference='DEMO-' + secrets.token_hex(6).upper(), amount=amount, status=outcome)
    db.session.add(payment)
    if outcome == 'success' and amount == bill['remaining']:
        for order in visit.orders:
            source = f'order:{order.id}'
            if not db.session.scalar(select(Reward.id).where(Reward.source == source)):
                db.session.add(Reward(customer_id=order.customer_id, order_id=order.id, source=source,
                                      points=order.total // 10000, description=f'Paid order #{order.id:04}'))
        notify('payment', f'Table {visit.table.number:02} paid in full (demo).')
    db.session.commit()
    return jsonify(payment=payment_json(payment), bill=bill_json(visit)), 201


@customer.get('/bill/<int:visit_id>')
def receipt(visit_id):
    visit = get_or_404(Visit, visit_id)
    if session.get('visit_id') != visit.id:
        from models import User
        user = db.session.get(User, session.get('user_id')) if session.get('user_id') else None
        if not user or user.role not in ('admin', 'waiter'):
            abort(403, description='You cannot view another table’s bill.')
    return render_template('bill.html', bill=bill_json(visit), restaurant=db.session.get(Restaurant, visit.table.restaurant_id), visit=visit)


@customer.post('/api/guest/reviews')
def review():
    person, visit = guest()
    if not visit.orders:
        abort(409, description='Place an order before leaving a review.')
    if db.session.scalar(select(Review.id).where(Review.visit_id == visit.id, Review.customer_id == person.id)):
        abort(409, description='You have already reviewed this visit. Thank you!')
    data = payload()
    db.session.add(Review(visit_id=visit.id, customer_id=person.id,
                          food_rating=integer(data, 'food_rating', 1, 5), service_rating=integer(data, 'service_rating', 1, 5),
                          comment=string(data, 'comment', 0, 1000)))
    db.session.commit()
    return jsonify(message='Thank you for sharing your experience.'), 201


@customer.post('/api/guest/game')
def game():
    person, visit = guest(True)
    if not visit.orders:
        abort(409, description='Place your first order to unlock the daily quiz.')
    source = f'game:{person.id}:{today().isoformat()}'
    if db.session.scalar(select(Reward.id).where(Reward.source == source)):
        abort(409, description='You have already played today. Come back tomorrow!')
    answer = integer(payload(), 'answer', 0, 2)
    correct = QUESTIONS[today().toordinal() % len(QUESTIONS)][2]
    earned = 10 if answer == correct else 0
    db.session.add(Reward(customer_id=person.id, source=source, points=earned, description='Daily foodie quiz'))
    db.session.commit()
    return jsonify(points=earned, correct_answer=correct, message='Delicious! You earned 10 points.' if earned else 'Good try! Come back tomorrow for another question.')
