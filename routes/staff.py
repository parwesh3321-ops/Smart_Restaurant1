from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from io import BytesIO
from urllib.parse import urlparse
import qrcode
from flask import Blueprint, render_template, session, redirect, jsonify, abort, send_file, request
from sqlalchemy import select, func
from database import db
from models import (User, Restaurant, DiningTable, Visit, Category, MenuItem, Order,
                    OrderItem, Payment, WaiterRequest, Review, Notification, now)
from .common import (role_required, payload, string, integer, boolean, money, get_or_404,
                     active_visit, bill_json, order_json, payment_json, iso, notify)

staff = Blueprint('staff', __name__)
ROLES = ('admin', 'waiter', 'kitchen')
IMAGES = {'pasta.jpg', 'pizza.jpg', 'salad.jpg', 'soup.jpg', 'curry.jpg', 'bowl.jpg',
          'cake.jpg', 'icecream.jpg', 'coffee.jpg', 'lemonade.jpg', 'bread.jpg', 'grill.jpg'}


def table_json(table):
    visit = active_visit(table.id)
    bill = bill_json(visit) if visit else None
    restaurant = db.session.get(Restaurant, table.restaurant_id)
    return dict(id=table.id, number=table.number, capacity=table.capacity, zone=table.zone,
                status=table.status, reservation_name=table.reservation_name,
                guests=visit.guest_count if visit else 0, visit_id=visit.id if visit else None,
                total=bill['total'] if bill else 0, remaining=bill['remaining'] if bill else 0,
                opened_at=iso(visit.opened_at) if visit else None,
                menu_url=restaurant.public_base_url + '/menu/' + table.token,
                menu_path='/menu/' + table.token)


def menu_json(item):
    return dict(id=item.id, category_id=item.category_id, category=item.category.name, name=item.name,
                description=item.description, price=item.price, image=item.image,
                vegetarian=item.vegetarian, available=item.available)


@staff.get('/staff')
def staff_page():
    user = db.session.get(User, session.get('user_id')) if session.get('user_id') else None
    if not user:
        return redirect('/login')
    return render_template('staff.html', user=user, restaurant=db.session.scalar(select(Restaurant)))


@staff.get('/api/staff/bootstrap')
@role_required(*ROLES)
def bootstrap():
    user = db.session.get(User, session['user_id'])
    restaurant = db.session.scalar(select(Restaurant))
    data = dict(user=dict(name=user.name, role=user.role), restaurant=dict(name=restaurant.name, address=restaurant.address),
                orders=[order_json(o) for o in db.session.scalars(select(Order).order_by(Order.id.desc()))])
    if user.role != 'kitchen':
        data['tables'] = [table_json(t) for t in db.session.scalars(select(DiningTable).where(DiningTable.active.is_(True)).order_by(DiningTable.number))]
        data['requests'] = [dict(id=w.id, table_number=w.visit.table.number, kind=w.kind, note=w.note,
                                  status=w.status, created_at=iso(w.created_at)) for w in db.session.scalars(select(WaiterRequest).order_by(WaiterRequest.id.desc()).limit(100))]
        data['notifications'] = [dict(id=n.id, message=n.message, read=n.read, created_at=iso(n.created_at)) for n in db.session.scalars(select(Notification).order_by(Notification.id.desc()).limit(30))]
    if user.role == 'admin':
        data['menu'] = [menu_json(m) for m in db.session.scalars(select(MenuItem).where(MenuItem.active.is_(True)).order_by(MenuItem.id))]
        data['categories'] = [dict(id=c.id, name=c.name) for c in db.session.scalars(select(Category).order_by(Category.sort_order, Category.id))]
        data['payments'] = [payment_json(p) for p in db.session.scalars(select(Payment).order_by(Payment.id.desc()))]
        data['reviews'] = [dict(id=r.id, customer=r.customer.name, table_number=r.visit.table.number, food_rating=r.food_rating,
                                service_rating=r.service_rating, comment=r.comment, created_at=iso(r.created_at)) for r in db.session.scalars(select(Review).order_by(Review.id.desc()).limit(100))]
        data['settings'] = dict(name=restaurant.name, address=restaurant.address, wifi_name=restaurant.wifi_name,
                                wifi_password=restaurant.wifi_password, public_base_url=restaurant.public_base_url, tax_bps=restaurant.tax_bps)
        today = datetime.now(ZoneInfo('Asia/Kolkata')).date()
        midnight = datetime.combine(today, datetime.min.time(), tzinfo=ZoneInfo('Asia/Kolkata')).astimezone(timezone.utc).replace(tzinfo=None)
        data['stats'] = dict(total_orders=db.session.scalar(select(func.count(Order.id))),
            today_orders=db.session.scalar(select(func.count(Order.id)).where(Order.created_at >= midnight)),
            daily_revenue=db.session.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == 'success', Payment.created_at >= midnight)))
        revenue = []
        for offset in range(6, -1, -1):
            start = midnight - timedelta(days=offset)
            amount = db.session.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == 'success', Payment.created_at >= start, Payment.created_at < start+timedelta(days=1)))
            revenue.append(dict(day=(today-timedelta(days=offset)).strftime('%a'), amount=amount))
        data['revenue'] = revenue
        popular = db.session.execute(select(OrderItem.name, func.sum(OrderItem.quantity).label('qty')).group_by(OrderItem.name).order_by(func.sum(OrderItem.quantity).desc()).limit(4)).all()
        data['popular'] = [dict(name=name, quantity=qty) for name, qty in popular]
    return jsonify(data)


@staff.post('/api/tables')
@role_required('admin')
def create_table():
    data = payload()
    table = DiningTable(restaurant_id=db.session.scalar(select(Restaurant.id)), number=integer(data, 'number', 1, 999),
                        capacity=integer(data, 'capacity', 1, 20), zone=string(data, 'zone', 1, 40))
    db.session.add(table)
    db.session.commit()
    return jsonify(table=table_json(table)), 201


@staff.patch('/api/tables/<int:table_id>')
@role_required('admin', 'waiter')
def update_table(table_id):
    table = get_or_404(DiningTable, table_id)
    if not table.active:
        abort(404)
    data = payload()
    role = db.session.get(User, session['user_id']).role
    if role != 'admin' and any(k in data for k in ('number', 'capacity', 'zone')):
        abort(403, description='Only an admin can edit table configuration.')
    visit = active_visit(table.id)
    if 'number' in data:
        table.number = integer(data, 'number', 1, 999)
    if 'capacity' in data:
        capacity = integer(data, 'capacity', 1, 20)
        if visit and capacity < visit.guest_count:
            abort(409, description='Capacity cannot be lower than the seated guest count.')
        table.capacity = capacity
    if 'zone' in data:
        table.zone = string(data, 'zone', 1, 40)
    if 'guest_count' in data and visit:
        visit.guest_count = integer(data, 'guest_count', 1, table.capacity)
    elif 'guest_count' in data and data.get('status') != 'occupied':
        abort(409, description='Seat this table before changing its guest count.')
    if 'status' in data:
        status = data['status']
        if status not in ('available', 'occupied', 'reserved'):
            abort(400, description='Invalid table status.')
        if visit and status != 'occupied':
            abort(409, description='Close the current dining session first.')
        if status == 'occupied' and not visit:
            db.session.add(Visit(table_id=table.id, guest_count=integer(data, 'guest_count', 1, table.capacity)))
        table.status = status
        table.reservation_name = string(data, 'reservation_name', 1, 100) if status == 'reserved' else ''
    db.session.commit()
    return jsonify(message='Table updated.')


@staff.delete('/api/tables/<int:table_id>')
@role_required('admin')
def delete_table(table_id):
    table = get_or_404(DiningTable, table_id)
    if active_visit(table.id) or table.status != 'available':
        abort(409, description='Only an available table with no active session can be archived.')
    table.active = False  # Preserve historical order and payment relationships.
    db.session.commit()
    return jsonify(message='Table archived. Its history is retained.')


@staff.get('/api/tables/<int:table_id>/bill')
@role_required('admin', 'waiter')
def table_bill(table_id):
    table = get_or_404(DiningTable, table_id)
    visit = active_visit(table.id)
    if not visit:
        abort(404, description='No current bill for this table.')
    return jsonify(bill=bill_json(visit))


@staff.post('/api/tables/<int:table_id>/close')
@role_required('admin', 'waiter')
def close_table(table_id):
    table = get_or_404(DiningTable, table_id)
    visit = active_visit(table.id)
    if not visit:
        abort(409, description='No active dining session.')
    if bill_json(visit)['remaining']:
        abort(409, description='The bill must be paid before closing the table.')
    if any(o.status != 'served' for o in visit.orders):
        abort(409, description='Serve every order before closing the table.')
    visit.closed_at = now()
    table.status = 'available'
    table.reservation_name = ''
    for req in db.session.scalars(select(WaiterRequest).where(WaiterRequest.visit_id == visit.id, WaiterRequest.status != 'completed')):
        req.status = 'completed'
        req.updated_at = now()
    notify('table', f'Table {table.number:02} is ready for the next guests.')
    db.session.commit()
    return jsonify(message='Table closed and available.')


@staff.get('/api/tables/<int:table_id>/qr')
@role_required('admin', 'waiter')
def table_qr(table_id):
    table = get_or_404(DiningTable, table_id)
    if not table.active:
        abort(404)
    restaurant = db.session.get(Restaurant, table.restaurant_id)
    image = qrcode.make(restaurant.public_base_url + '/menu/' + table.token)
    output = BytesIO()
    image.save(output, format='PNG')
    output.seek(0)
    return send_file(output, mimetype='image/png', as_attachment=request.args.get('download') == '1', download_name=f'table-{table.number:02}-qr.png')


@staff.get('/staff/qr-print')
@role_required('admin', 'waiter')
def qr_print():
    return render_template('qr_print.html', restaurant=db.session.scalar(select(Restaurant)),
                           tables=db.session.scalars(select(DiningTable).where(DiningTable.active.is_(True)).order_by(DiningTable.number)).all())


@staff.post('/api/categories')
@role_required('admin')
def create_category():
    category = Category(name=string(payload(), 'name', 1, 60), restaurant_id=db.session.scalar(select(Restaurant.id)))
    db.session.add(category)
    db.session.commit()
    return jsonify(id=category.id), 201


@staff.patch('/api/categories/<int:ident>')
@role_required('admin')
def update_category(ident):
    get_or_404(Category, ident).name = string(payload(), 'name', 1, 60)
    db.session.commit()
    return jsonify(message='Category updated.')


@staff.delete('/api/categories/<int:ident>')
@role_required('admin')
def delete_category(ident):
    category = get_or_404(Category, ident)
    if db.session.scalar(select(MenuItem.id).where(MenuItem.category_id == ident).limit(1)):
        abort(409, description='This category contains current or archived items. Move those items to another category first.')
    db.session.delete(category)
    db.session.commit()
    return jsonify(message='Category deleted.')


def apply_item(item, data):
    item.name = string(data, 'name', 1, 100)
    item.description = string(data, 'description', 1, 500)
    item.category_id = get_or_404(Category, integer(data, 'category_id')).id
    item.price = money(data.get('price'))
    image = string(data, 'image', 1, 80)
    if image not in IMAGES:
        abort(400, description='Choose an image from the provided gallery.')
    item.image = image
    item.vegetarian = boolean(data, 'vegetarian', True)
    item.available = boolean(data, 'available', True)


@staff.post('/api/menu')
@role_required('admin')
def create_item():
    item = MenuItem()
    apply_item(item, payload())
    db.session.add(item)
    db.session.commit()
    return jsonify(id=item.id), 201


@staff.put('/api/menu/<int:ident>')
@role_required('admin')
def update_item(ident):
    item = get_or_404(MenuItem, ident)
    if not item.active:
        abort(404)
    apply_item(item, payload())
    db.session.commit()
    return jsonify(message='Menu item updated.')


@staff.delete('/api/menu/<int:ident>')
@role_required('admin')
def delete_item(ident):
    item = get_or_404(MenuItem, ident)
    item.active = False
    item.available = False
    db.session.commit()
    return jsonify(message='Menu item archived. Past orders are unchanged.')


@staff.patch('/api/orders/<int:ident>/status')
@role_required(*ROLES)
def update_order(ident):
    order = get_or_404(Order, ident)
    target = string(payload(), 'status', 1, 20)
    transitions = {'pending': 'preparing', 'preparing': 'ready', 'ready': 'served'}
    if transitions.get(order.status) != target:
        abort(409, description='Orders must follow Pending → Preparing → Ready → Served.')
    role = db.session.get(User, session['user_id']).role
    if role == 'waiter' and target != 'served' or role == 'kitchen' and target == 'served':
        abort(403, description='Kitchen prepares orders; waiters mark ready orders as served.')
    order.status = target
    order.updated_at = now()
    notify('order', f'Order #{order.id:04} · Table {order.table.number:02} is {target}.')
    db.session.commit()
    return jsonify(order=order_json(order))


@staff.patch('/api/requests/<int:ident>')
@role_required('admin', 'waiter')
def update_request(ident):
    req = get_or_404(WaiterRequest, ident)
    target = string(payload(), 'status', 1, 20)
    if {'pending': 'accepted', 'accepted': 'completed'}.get(req.status) != target:
        abort(409, description='Requests must be accepted before they can be completed.')
    req.status = target
    req.updated_at = now()
    if target == 'accepted':
        req.accepted_by = session['user_id']
    db.session.commit()
    return jsonify(message='Request updated.')


@staff.post('/api/notifications/read')
@role_required('admin', 'waiter')
def read_notifications():
    for item in db.session.scalars(select(Notification).where(Notification.read.is_(False))):
        item.read = True
    db.session.commit()
    return jsonify(message='Notifications marked as read.')


@staff.put('/api/settings')
@role_required('admin')
def settings():
    data = payload()
    restaurant = db.session.scalar(select(Restaurant))
    restaurant.name = string(data, 'name', 1, 100)
    restaurant.address = string(data, 'address', 1, 200)
    restaurant.wifi_name = string(data, 'wifi_name', 1, 80)
    restaurant.wifi_password = string(data, 'wifi_password', 1, 80)
    url = string(data, 'public_base_url', 1, 250).rstrip('/')
    parsed = urlparse(url)
    try:
        parsed.port
    except ValueError:
        abort(400, description='Invalid port in QR base URL.')
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path or any(c.isspace() for c in url):
        abort(400, description='Use a base URL such as http://192.168.1.20:5001 with no path.')
    restaurant.public_base_url = url
    db.session.commit()
    return jsonify(message='Settings saved. Download or print fresh QR codes after changing the base URL.')
