"""Real HTTP requests against isolated, temporary SQLite databases."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import uuid
import pytest
from PIL import Image
from sqlalchemy import select, text, func
from database import db
from models import DiningTable, MenuItem, Order, Reward, Restaurant, Visit, Payment


def csrf(client):
    client.get('/login')
    with client.session_transaction() as session:
        return session['csrf']


def send(client, path, data=None, method='POST'):
    return client.open(path, method=method, json=data or {}, headers={'X-CSRF-Token':csrf(client)})


def login(client, role='admin'):
    response = send(client, '/api/login', {'username':role, 'password':role.capitalize()+'@12345'})
    assert response.status_code == 200, response.json


def join(app, client, table_number=1, name='Test guest'):
    with app.app_context():
        token = db.session.scalar(select(DiningTable.token).where(DiningTable.number == table_number))
    assert client.get('/menu/'+token).status_code == 200
    response=send(client, '/api/guest/join', {'token':token, 'name':name, 'guest_count':2})
    assert response.status_code==201, response.json
    return token, response.json['visit_id']


def order(client, quantity=1, item=1, request_key=None):
    return send(client, '/api/guest/orders', {'items':[{'id':item,'quantity':quantity}], 'notes':'Test note', 'request_key':request_key or uuid.uuid4().hex})


def pay(client, amount, outcome='success', split_id=None, request_key=None):
    return send(client, '/api/guest/payments', {'amount':amount,'outcome':outcome,'split_id':split_id,'request_key':request_key or uuid.uuid4().hex})


def current_bill(client):
    return client.get('/api/guest/state').json['bill']


def test_login_logout_and_password(client):
    assert client.get('/staff').status_code==302
    assert send(client,'/api/login',{'username':'admin','password':'wrong'}).status_code==401
    login(client)
    assert client.get('/staff').status_code==200
    assert client.get('/api/staff/bootstrap').json['user']['role']=='admin'
    assert send(client,'/api/password',{'current_password':'wrong','new_password':'Changed@12345'}).status_code==400
    assert send(client,'/api/password',{'current_password':'Admin@12345','new_password':'Changed@12345'}).status_code==200
    assert send(client,'/api/logout').status_code==200
    assert client.get('/api/staff/bootstrap').status_code==401
    assert send(client,'/api/login',{'username':'admin','password':'Changed@12345'}).status_code==200


def test_csrf_and_security_headers(client):
    response=client.get('/login')
    assert response.headers['X-Content-Type-Options']=='nosniff'
    assert "frame-ancestors 'none'" in response.headers['Content-Security-Policy']
    assert client.post('/api/login',json={'username':'admin','password':'Admin@12345'}).status_code==400


def test_login_rate_limit(client):
    for i in range(10):
        assert send(client,'/api/login',{'username':f'guess{i}','password':'wrong'}).status_code==401
    assert send(client,'/api/login',{'username':'admin','password':'Admin@12345'}).status_code==429


@pytest.mark.parametrize('role', ['waiter','kitchen'])
def test_role_boundaries(client, role):
    login(client,role)
    assert send(client,'/api/tables',{'number':99,'capacity':4,'zone':'Main'}).status_code==403
    assert send(client,'/api/menu',{}).status_code==403
    assert send(client,'/api/settings',{},'PUT').status_code==403
    data=client.get('/api/staff/bootstrap').json
    assert 'payments' not in data and 'settings' not in data and 'reviews' not in data
    if role=='kitchen':
        assert 'tables' not in data
        assert client.get('/api/tables/1/qr').status_code==403


def test_table_crud_and_qr(client):
    login(client)
    response=send(client,'/api/tables',{'number':99,'capacity':6,'zone':'Garden'})
    assert response.status_code==201
    ident=response.json['table']['id']
    qr=client.get(f'/api/tables/{ident}/qr?download=1')
    assert qr.status_code==200 and qr.mimetype=='image/png'
    image=Image.open(BytesIO(qr.data));assert image.width>200
    path=response.json['table']['menu_path']
    assert client.get(path).status_code==200
    assert send(client,f'/api/tables/{ident}',{'capacity':8,'zone':'Terrace'},'PATCH').status_code==200
    assert send(client,f'/api/tables/{ident}',{},'DELETE').status_code==200
    assert client.get(path).status_code==404


def test_duplicate_table_number_and_invalid_capacity(client):
    login(client)
    assert send(client,'/api/tables',{'number':1,'capacity':4,'zone':'Main'}).status_code==409
    assert send(client,'/api/tables',{'number':99,'capacity':0,'zone':'Main'}).status_code==400
    assert send(client,'/api/tables',{'number':99,'capacity':True,'zone':'Main'}).status_code==400


def test_reserve_seat_resize_and_close(client):
    login(client)
    assert send(client,'/api/tables/1',{'status':'reserved','reservation_name':'Test party'},'PATCH').status_code==200
    assert send(client,'/api/tables/1',{'status':'occupied','guest_count':2},'PATCH').status_code==200
    assert send(client,'/api/tables/1',{'status':'occupied','guest_count':1},'PATCH').status_code==200
    table=next(t for t in client.get('/api/staff/bootstrap').json['tables'] if t['id']==1)
    assert table['guests']==1
    assert send(client,'/api/tables/1',{'status':'available'},'PATCH').status_code==409
    assert send(client,'/api/tables/1/close').status_code==200


def test_category_menu_crud_and_original_price(app, client):
    login(client)
    category=send(client,'/api/categories',{'name':'Seasonal'}).json['id']
    data={'category_id':category,'name':'Test soup','description':'Fresh soup','price':'10.03','image':'soup.jpg','vegetarian':True,'available':True}
    response=send(client,'/api/menu',data);assert response.status_code==201
    ident=response.json['id']
    guest=app.test_client();join(app,guest)
    placed=order(guest,item=ident);assert placed.status_code==201
    assert placed.json['order']['subtotal']==1003 and placed.json['order']['tax']==50
    data['price']='20.00'
    assert send(client,f'/api/menu/{ident}',data,'PUT').status_code==200
    assert current_bill(guest)['total']==1053
    assert send(client,f'/api/menu/{ident}',{},'DELETE').status_code==200
    assert order(guest,item=ident).status_code==409
    assert send(client,f'/api/categories/{category}',{},'DELETE').status_code==409
    empty_id=send(client,'/api/categories',{'name':'Empty category'}).json['id']
    assert send(client,f'/api/categories/{empty_id}',{'name':'Renamed'},'PATCH').status_code==200
    assert send(client,f'/api/categories/{empty_id}',{},'DELETE').status_code==200


def test_invalid_item_image_and_price(client):
    login(client)
    data={'name':'Dish','description':'Description','price':'12.001','category_id':1,'image':'pasta.jpg'}
    assert send(client,'/api/menu',data).status_code==400
    data.update(price='10.00',image='../../config.py')
    assert send(client,'/api/menu',data).status_code==400


def test_guest_requires_table_and_reserved_table(app, client):
    assert client.get('/api/guest/state').status_code==401
    assert order(client).status_code==401
    with app.app_context(): token=db.session.get(DiningTable,7).token
    assert send(client,'/api/guest/join',{'token':token,'name':'Test','guest_count':2}).status_code==409
    assert client.get('/menu/not-a-token').status_code==404


def test_group_join_shares_bill_and_keeps_guest_count(app, client):
    token,visit=join(app,client)
    assert order(client).status_code==201
    other=app.test_client()
    assert send(other,'/api/guest/join',{'token':token,'name':'Other guest','guest_count':1}).json['visit_id']==visit
    assert current_bill(other)['total']==35700
    assert other.get('/api/guest/state').json['table']['guests']==2
    assert order(other,quantity=2,item=2).status_code==201
    assert len(current_bill(client)['orders'])==2


def test_order_idempotency_and_server_prices(app, client):
    join(app,client)
    key=uuid.uuid4().hex
    a=order(client,request_key=key);b=order(client,request_key=key)
    assert a.status_code==201 and b.status_code==200
    assert a.json['order']['id']==b.json['order']['id']
    assert len(current_bill(client)['orders'])==1
    assert current_bill(client)['total']==35700


@pytest.mark.parametrize('quantity', [0,-1,51,True,'2',2.5])
def test_invalid_order_quantities(app,client,quantity):
    join(app,client)
    assert order(client,quantity=quantity).status_code==400
    assert current_bill(client)['total']==0


def test_unavailable_and_duplicate_items(app,client):
    join(app,client)
    with app.app_context():
        db.session.get(MenuItem,1).available=False;db.session.commit()
    assert order(client).status_code==409
    assert send(client,'/api/guest/orders',{'request_key':uuid.uuid4().hex,'items':[{'id':2,'quantity':1},{'id':2,'quantity':1}]}).status_code==400


def test_kitchen_flow_and_role_permissions(app,client):
    join(app,client);ident=order(client).json['order']['id']
    kitchen=app.test_client();login(kitchen,'kitchen')
    waiter=app.test_client();login(waiter,'waiter')
    assert send(kitchen,f'/api/orders/{ident}/status',{'status':'served'},'PATCH').status_code==409
    assert send(waiter,f'/api/orders/{ident}/status',{'status':'preparing'},'PATCH').status_code==403
    for status in ['preparing','ready']:
        assert send(kitchen,f'/api/orders/{ident}/status',{'status':status},'PATCH').status_code==200
    assert send(kitchen,f'/api/orders/{ident}/status',{'status':'served'},'PATCH').status_code==403
    assert send(waiter,f'/api/orders/{ident}/status',{'status':'served'},'PATCH').status_code==200
    assert current_bill(client)['orders'][0]['status']=='served'


def test_waiter_request_lifecycle(app,client):
    join(app,client)
    a=send(client,'/api/guest/requests',{'kind':'water','note':'Please'})
    b=send(client,'/api/guest/requests',{'kind':'water','note':'Again'})
    assert a.status_code==201 and b.json['id']==a.json['id']
    staff=app.test_client();login(staff,'waiter');ident=a.json['id']
    assert send(staff,f'/api/requests/{ident}',{'status':'completed'},'PATCH').status_code==409
    for status in ['accepted','completed']:
        assert send(staff,f'/api/requests/{ident}',{'status':status},'PATCH').status_code==200
    assert client.get('/api/guest/state').json['requests'][0]['status']=='completed'


def test_equal_split_paise_remainder_and_freeze(app,client):
    join(app,client);order(client)
    response=send(client,'/api/guest/splits',{'mode':'equal','count':8})
    assert response.status_code==201
    splits=response.json['bill']['splits'];assert sum(s['amount'] for s in splits)==35700
    assert max(s['amount'] for s in splits)-min(s['amount'] for s in splits)==1
    assert order(client).status_code==409


def test_custom_split_validation(app,client):
    join(app,client);order(client)
    assert send(client,'/api/guest/splits',{'mode':'custom','shares':[{'label':'A','amount':'100'},{'label':'B','amount':'200'}]}).status_code==400
    response=send(client,'/api/guest/splits',{'mode':'custom','shares':[{'label':'A','amount':'100.01'},{'label':'B','amount':'256.99'}]})
    assert response.status_code==201
    split=response.json['bill']['splits'][0]
    assert pay(client,'100.02',split_id=split['id']).status_code==409
    assert pay(client,'100.01',split_id=split['id']).status_code==201
    assert current_bill(client)['remaining']==25699


def test_failed_payment_partial_success_idempotency_and_rewards(app,client):
    join(app,client);order(client)
    response=pay(client,'100',outcome='failed');assert response.status_code==201
    assert current_bill(client)['remaining']==35700
    key=uuid.uuid4().hex
    a=pay(client,'100',request_key=key);b=pay(client,'100',request_key=key)
    assert a.status_code==201 and b.status_code==200
    assert a.json['payment']['id']==b.json['payment']['id']
    assert current_bill(client)['remaining']==25700
    assert order(client).status_code==409
    assert pay(client,'257.01').status_code==409
    assert pay(client,'257').status_code==201
    assert current_bill(client)['remaining']==0
    assert client.get('/api/guest/state').json['customer']['points']==3
    assert pay(client,'1').status_code==409


@pytest.mark.parametrize('amount', ['0','-1','NaN','Infinity','0.001',True,'1000001'])
def test_invalid_payment_amounts(app,client,amount):
    join(app,client);order(client)
    assert pay(client,amount).status_code==400
    assert current_bill(client)['remaining']==35700


def test_split_payment_requires_correct_share_and_cannot_resplit(app,client):
    join(app,client);order(client)
    splits=send(client,'/api/guest/splits',{'mode':'equal','count':2}).json['bill']['splits']
    assert pay(client,'1').status_code==400
    assert pay(client,'1',split_id=999999).status_code==409
    assert pay(client,'1','failed',splits[0]['id']).status_code==201
    assert send(client,'/api/guest/splits',{'mode':'equal','count':3}).status_code==409


def test_two_simultaneous_payments_do_not_overcharge(app,client):
    token,visit=join(app,client);order(client)
    other=app.test_client();join(app,other)
    # Prime both cookie jars; each thread has its own client/connection.
    csrf(client);csrf(other)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results=list(executor.map(lambda c:pay(c,'357'),[client,other]))
    assert sorted(r.status_code for r in results)==[201,409]
    assert current_bill(client)['paid']==35700
    with app.app_context():
        assert db.session.scalar(select(func.count(Reward.id)).where(Reward.source.like('order:%'),Reward.customer_id==client.get('/api/guest/state').json['customer']['id']))==1


def test_close_table_requires_paid_served_and_new_visit_is_clean(app,client):
    token,visit=join(app,client);ident=order(client).json['order']['id']
    staff=app.test_client();login(staff)
    assert send(staff,'/api/tables/1/close').status_code==409
    pay(client,'357')
    assert send(staff,'/api/tables/1/close').status_code==409
    for status in ['preparing','ready','served']:
        assert send(staff,f'/api/orders/{ident}/status',{'status':status},'PATCH').status_code==200
    assert send(staff,'/api/tables/1/close').status_code==200
    assert order(client).status_code==409
    assert client.get(f'/bill/{visit}').status_code==200
    other=app.test_client();_,new_visit=join(app,other)
    assert new_visit!=visit and current_bill(other)['total']==0
    assert client.get('/api/guest/state').json['bill']['visit_id']==visit
    assert other.get(f'/bill/{visit}').status_code==403


def test_reviews_rewards_and_game_daily_limit(app,client):
    join(app,client)
    data={'food_rating':5,'service_rating':4,'comment':'Lovely <script>alert(1)</script>'}
    assert send(client,'/api/guest/reviews',data).status_code==409
    assert send(client,'/api/guest/game',{'answer':1}).status_code==409
    order(client)
    assert send(client,'/api/guest/reviews',{**data,'food_rating':6}).status_code==400
    assert send(client,'/api/guest/reviews',data).status_code==201
    assert send(client,'/api/guest/reviews',data).status_code==409
    from routes.customer import QUESTIONS,today
    answer=QUESTIONS[today().toordinal()%len(QUESTIONS)][2]
    assert send(client,'/api/guest/game',{'answer':answer}).json['points']==10
    assert send(client,'/api/guest/game',{'answer':answer}).status_code==409
    assert client.get('/api/guest/state').json['customer']['points']==10


def test_wrong_game_answer_recorded_once(app,client):
    join(app,client);order(client)
    from routes.customer import QUESTIONS,today
    answer=(QUESTIONS[today().toordinal()%len(QUESTIONS)][2]+1)%3
    assert send(client,'/api/guest/game',{'answer':answer}).json['points']==0
    assert send(client,'/api/guest/game',{'answer':answer}).status_code==409


def test_private_bill_and_guest_cannot_reach_staff(app,client):
    _,visit=join(app,client);order(client)
    other=app.test_client();join(app,other,table_number=3)
    assert other.get(f'/bill/{visit}').status_code==403
    assert client.get('/api/staff/bootstrap').status_code==401
    assert send(client,'/api/orders/1/status',{'status':'preparing'},'PATCH').status_code==401


def test_settings_notifications_and_local_qr_url(client):
    login(client)
    data=client.get('/api/staff/bootstrap').json['settings']
    data['public_base_url']='http://192.168.1.20:5001'
    assert send(client,'/api/settings',data,'PUT').status_code==200
    table=client.get('/api/staff/bootstrap').json['tables'][0]
    assert table['menu_url'].startswith(data['public_base_url'])
    for url in ['javascript:alert(1)','https://user:password@example.com','http://localhost:5001/path','http://localhost:bad']:
        data['public_base_url']=url
        assert send(client,'/api/settings',data,'PUT').status_code==400
    assert send(client,'/api/notifications/read').status_code==200
    assert all(n['read'] for n in client.get('/api/staff/bootstrap').json['notifications'])


def test_database_foreign_keys_and_required_schema(app):
    with app.app_context():
        assert db.session.execute(text('PRAGMA foreign_keys')).scalar()==1
        assert db.session.execute(text('PRAGMA foreign_key_check')).all()==[]
        names=set(db.metadata.tables)
        assert {'users','restaurants','tables','menu_categories','menu_items','customers','orders','order_items','waiter_requests','payments','bill_splits','reviews','rewards','notifications'}<=names


def test_receipt_print_page_and_bundled_assets(app,client):
    join(app,client);order(client);visit=current_bill(client)['visit_id']
    response=client.get(f'/bill/{visit}');assert response.status_code==200
    assert b'DEMO RECEIPT' in response.data
    login(client)
    assert client.get('/staff/qr-print').status_code==200
    for path in ['css/app.css','js/common.js','js/staff.js','js/customer.js','vendor/chart.umd.js','vendor/lucide.js','images/pasta.jpg','images/lemonade.jpg']:
        assert client.get('/static/'+path).status_code==200


def test_models_compile_for_mysql(app):
    from sqlalchemy.schema import CreateTable
    from sqlalchemy.dialects import mysql
    with app.app_context():
        for table in db.metadata.sorted_tables:
            ddl=str(CreateTable(table).compile(dialect=mysql.dialect()))
            assert 'CREATE TABLE' in ddl and 'PRIMARY KEY' in ddl


def test_public_customer_entry_is_read_only(app, client):
    with app.app_context():
        visits_before = db.session.scalar(select(func.count(Visit.id)))
        orders_before = db.session.scalar(select(func.count(Order.id)))
    home = client.get('/')
    assert home.status_code == 200
    assert b'Customer View' in home.data and b'href="/customer"' in home.data
    assert b'href="/login"' in home.data
    picker = client.get('/customer')
    assert picker.status_code == 200
    assert b'View menu at Table 01' in picker.data
    with app.app_context():
        assert db.session.scalar(select(func.count(Visit.id))) == visits_before
        assert db.session.scalar(select(func.count(Order.id))) == orders_before
        assert db.session.get(DiningTable, 1).status == 'available'
    with client.session_transaction() as state:
        assert 'customer_id' not in state and 'user_id' not in state
    assert client.get('/api/staff/bootstrap').status_code == 401


def test_picker_hides_archived_and_reserved_links_and_private_names(app, client):
    with app.app_context():
        reserved = db.session.get(DiningTable, 7)
        reserved.reservation_name = 'PRIVATE_RESERVATION_SENTINEL'
        reserved_token = reserved.token
        archived = db.session.get(DiningTable, 12)
        archived.active = False
        archived_token = archived.token
        db.session.commit()
    html = client.get('/customer').get_data(as_text=True)
    assert reserved_token not in html and archived_token not in html
    assert 'PRIVATE_RESERVATION_SENTINEL' not in html
    assert 'Please speak to your waiter' in html
    assert 'Table <span>12</span>' not in html
    assert client.get('/menu/' + archived_token).status_code == 404


def test_qr_only_mode_keeps_direct_menu_available(app, client):
    app.config['ENABLE_TABLE_PICKER'] = False
    with app.app_context():
        tokens = db.session.scalars(select(DiningTable.token)).all()
    page = client.get('/customer').get_data(as_text=True)
    assert 'Scan the QR code' in page
    assert all(token not in page for token in tokens)
    assert client.get('/menu/' + tokens[0]).status_code == 200
    assert client.get('/api/staff/bootstrap').status_code == 401


def test_customer_entry_to_order_without_staff_login(app, client):
    from html.parser import HTMLParser

    class TableLinks(HTMLParser):
        menu_path = None
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'a' and attrs.get('aria-label') == 'View menu at Table 01':
                self.menu_path = attrs['href']

    parser = TableLinks()
    parser.feed(client.get('/customer').get_data(as_text=True))
    assert parser.menu_path
    page = client.get(parser.menu_path)
    assert page.status_code == 200 and b'Start dining' in page.data
    response = send(client, '/api/guest/join', {
        'token': parser.menu_path.rsplit('/', 1)[-1],
        'name': 'Customer entry test', 'guest_count': 2,
    })
    assert response.status_code == 201
    placed = order(client)
    assert placed.status_code == 201
    state = client.get('/api/guest/state').json
    assert state['table']['number'] == 1
    assert state['bill']['total'] == placed.json['order']['total']
    with client.session_transaction() as session:
        assert 'customer_id' in session and 'user_id' not in session
    assert client.get('/api/staff/bootstrap').status_code == 401


def test_continue_table_only_for_current_open_visit(app, client):
    from models import now
    assert b'Continue Table' not in client.get('/customer').data
    token, visit_id = join(app, client)
    assert b'Continue Table 01' in client.get('/customer').data
    assert b'Continue dining at Table 01' in client.get('/').data
    stranger = app.test_client()
    assert b'Continue Table' not in stranger.get('/customer').data
    with app.app_context():
        db.session.get(Visit, visit_id).closed_at = now()
        db.session.commit()
    assert b'Continue Table' not in client.get('/customer').data
    assert b'Continue dining at Table' not in client.get('/').data
