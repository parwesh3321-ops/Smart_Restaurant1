"""Repeatable demo seed. Existing databases are left untouched."""
from datetime import timedelta
from werkzeug.security import generate_password_hash
from sqlalchemy import select
from database import db
from models import (User, Restaurant, DiningTable, Category, MenuItem, Customer, Visit,
                    Order, OrderItem, Payment, WaiterRequest, Review, Reward, Notification, now)

MENU = [
 ('Starters', 'Garden chickpea salad', 'Chickpeas, avocado, crunchy garden vegetables and a lemon dressing.', 34000, 'salad.jpg', True),
 ('Starters', 'Roasted tomato soup', 'Slow-roasted tomatoes, fresh cream and a warm garlic toast.', 22000, 'soup.jpg', True),
 ('Starters', 'Warm sourdough basket', 'Oven-baked sourdough with garlic butter and garden herbs.', 19000, 'bread.jpg', True),
 ('Main course', 'Basil pesto farfalle', 'Farfalle tossed with basil pesto, parmesan and cherry tomatoes.', 42000, 'pasta.jpg', True),
 ('Main course', 'Margherita sourdough', 'Wood-fired pizza, San Marzano tomatoes, mozzarella and basil.', 39000, 'pizza.jpg', True),
 ('Main course', 'Paneer makhani', 'Soft paneer in a rich tomato and cashew sauce. Served with rice.', 38000, 'curry.jpg', True),
 ('Main course', 'Harvest garden bowl', 'Seasonal vegetables, fresh garden leaves and lemon tahini dressing.', 35000, 'bowl.jpg', True),
 ('Main course', 'Flame-grilled chicken', 'Tender grilled chicken with a herb dressing and seasonal sides.', 49000, 'grill.jpg', False),
 ('Desserts', 'Chocolate indulgence', 'Rich chocolate cake with a smooth dark chocolate ganache.', 26000, 'cake.jpg', True),
 ('Desserts', 'Vanilla bean sundae', 'Vanilla ice cream, chocolate drizzle and a little crunch.', 21000, 'icecream.jpg', True),
 ('Beverages', 'House cappuccino', 'A balanced espresso with velvety steamed milk.', 16000, 'coffee.jpg', True),
 ('Beverages', 'House fruit coolers', 'Seasonal fruit blends served chilled. Ask for today’s flavours.', 14000, 'lemonade.jpg', True),
]


def seed_database(base_url):
    if db.session.scalar(select(Restaurant.id).limit(1)):
        return False
    restaurant = Restaurant(name='Ember & Olive', address='12 Garden Lane, Mumbai · Demo restaurant',
                            wifi_name='EmberOlive_Guest', wifi_password='GoodFood2026', public_base_url=base_url)
    db.session.add(restaurant)
    db.session.flush()
    for username, name, role, password in [('admin','Nishant Sharma','admin','Admin@12345'),
        ('waiter','Aarav Mehta','waiter','Waiter@12345'), ('kitchen','Chef Mira','kitchen','Kitchen@12345')]:
        db.session.add(User(username=username, name=name, role=role, password_hash=generate_password_hash(password)))
    categories = {}
    for index, name in enumerate(['Starters', 'Main course', 'Desserts', 'Beverages']):
        category = Category(name=name, restaurant_id=restaurant.id, sort_order=index)
        db.session.add(category)
        db.session.flush()
        categories[name] = category.id
    items = []
    for category, name, description, price, image, vegetarian in MENU:
        item = MenuItem(category_id=categories[category], name=name, description=description, price=price, image=image, vegetarian=vegetarian)
        db.session.add(item)
        items.append(item)
    tables = []
    for number in range(1, 13):
        table = DiningTable(restaurant_id=restaurant.id, number=number, capacity=6 if number in (4,8,12) else 4 if number % 2 == 0 else 2,
                            zone='Terrace' if number > 8 else 'Main dining')
        db.session.add(table)
        tables.append(table)
    people = [Customer(name=name) for name in ['Ananya', 'Rohan', 'Sana', 'Kabir', 'Meera', 'Dev']]
    db.session.add_all(people)
    db.session.flush()
    counter = 0
    def make_order(visit, person, selections, status, timestamp):
        nonlocal counter
        counter += 1
        subtotal = sum(items[index].price * qty for index, qty in selections)
        tax = (subtotal * 500 + 5000) // 10000
        order = Order(visit_id=visit.id, table_id=visit.table_id, customer_id=person.id, request_key=f'seed-order-{counter:08}',
                      status=status, subtotal=subtotal, tax=tax, total=subtotal+tax, created_at=timestamp, updated_at=timestamp,
                      items=[OrderItem(menu_item_id=items[index].id, name=items[index].name, unit_price=items[index].price, quantity=qty) for index,qty in selections])
        db.session.add(order)
        db.session.flush()
        return order
    # Completed sample visits for a seven-day chart, including today.
    for day in range(6, -1, -1):
        for offset in range(2 + (day % 3)):
            stamp = now() - timedelta(days=day, minutes=70 + offset*30)
            table = tables[offset]
            person = people[offset]
            visit = Visit(table_id=table.id, guest_count=2, opened_at=stamp-timedelta(minutes=40), closed_at=stamp)
            db.session.add(visit)
            db.session.flush()
            order = make_order(visit, person, [(3, 2), (offset % 3, 1), (10+offset%2, 2)], 'served', stamp-timedelta(minutes=30))
            db.session.add(Payment(visit_id=visit.id, customer_id=person.id, reference=f'DEMO-SEED-{counter:06}', request_key=f'seed-payment-{counter:08}',
                                  amount=order.total, status='success', created_at=stamp))
            db.session.add(Reward(customer_id=person.id, order_id=order.id, source=f'order:{order.id}', points=order.total//10000, description=f'Paid order #{order.id:04}', created_at=stamp))
            if day in (0,1) and offset == 0:
                db.session.add(Review(visit_id=visit.id, customer_id=person.id, food_rating=5, service_rating=5,
                                      comment='The pesto pasta was lovely. Warm service and a beautiful space.', created_at=stamp))
    for index, status in [(1,'pending'), (3,'preparing'), (5,'ready'), (8,'served')]:
        table = tables[index]
        table.status = 'occupied'
        stamp = now()-timedelta(minutes=4+index*2)
        visit = Visit(table_id=table.id, guest_count=min(table.capacity, 3), opened_at=stamp)
        db.session.add(visit)
        db.session.flush()
        make_order(visit, people[index % len(people)], [(index % 8, 2), (11, 2)], status, stamp)
        if status == 'preparing':
            db.session.add(WaiterRequest(visit_id=visit.id, customer_id=people[3].id, kind='water', note='A bottle of still water, please.'))
    for index, name in [(6, 'Sharma · 2 guests'), (11, 'Patel · 6 guests')]:
        tables[index].status = 'reserved'
        tables[index].reservation_name = name
    db.session.add(Notification(kind='system', message='Welcome to Ember & Olive. Sample data is ready to explore.'))
    db.session.commit()
    return True
