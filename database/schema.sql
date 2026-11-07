-- SQLite schema reference. Use python init_db.py to initialize safely.

PRAGMA foreign_keys=ON;


CREATE TABLE customers (
	id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE login_attempts (
	id INTEGER NOT NULL, 
	"key" VARCHAR(64) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE INDEX ix_login_attempts_key ON login_attempts ("key");


CREATE TABLE notifications (
	id INTEGER NOT NULL, 
	kind VARCHAR(30) NOT NULL, 
	message VARCHAR(250) NOT NULL, 
	read BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE restaurants (
	id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	address VARCHAR(200) NOT NULL, 
	wifi_name VARCHAR(80) NOT NULL, 
	wifi_password VARCHAR(80) NOT NULL, 
	tax_bps INTEGER NOT NULL, 
	public_base_url VARCHAR(250) NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE users (
	id INTEGER NOT NULL, 
	username VARCHAR(80) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	password_hash VARCHAR(256) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (role IN ('admin','waiter','kitchen')), 
	UNIQUE (username)
)

;


CREATE TABLE menu_categories (
	id INTEGER NOT NULL, 
	restaurant_id INTEGER NOT NULL, 
	name VARCHAR(60) NOT NULL, 
	sort_order INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id), 
	UNIQUE (name)
)

;


CREATE TABLE tables (
	id INTEGER NOT NULL, 
	restaurant_id INTEGER NOT NULL, 
	number INTEGER NOT NULL, 
	capacity INTEGER NOT NULL, 
	zone VARCHAR(40) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	token VARCHAR(80) NOT NULL, 
	reservation_name VARCHAR(100) NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (capacity BETWEEN 1 AND 20), 
	CHECK (status IN ('available','occupied','reserved')), 
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id), 
	UNIQUE (number), 
	UNIQUE (token)
)

;


CREATE TABLE menu_items (
	id INTEGER NOT NULL, 
	category_id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description VARCHAR(500) NOT NULL, 
	price INTEGER NOT NULL, 
	image VARCHAR(80) NOT NULL, 
	vegetarian BOOLEAN NOT NULL, 
	available BOOLEAN NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (price > 0), 
	FOREIGN KEY(category_id) REFERENCES menu_categories (id)
)

;


CREATE TABLE visits (
	id INTEGER NOT NULL, 
	table_id INTEGER NOT NULL, 
	guest_count INTEGER NOT NULL, 
	opened_at DATETIME NOT NULL, 
	closed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(table_id) REFERENCES tables (id)
)

;

CREATE INDEX ix_visits_table_id ON visits (table_id);


CREATE TABLE bill_splits (
	id INTEGER NOT NULL, 
	visit_id INTEGER NOT NULL, 
	label VARCHAR(60) NOT NULL, 
	amount INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (amount > 0), 
	FOREIGN KEY(visit_id) REFERENCES visits (id)
)

;


CREATE TABLE orders (
	id INTEGER NOT NULL, 
	visit_id INTEGER NOT NULL, 
	table_id INTEGER NOT NULL, 
	customer_id INTEGER NOT NULL, 
	request_key VARCHAR(80) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	notes VARCHAR(300) NOT NULL, 
	subtotal INTEGER NOT NULL, 
	tax INTEGER NOT NULL, 
	total INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (status IN ('pending','preparing','ready','served')), 
	FOREIGN KEY(visit_id) REFERENCES visits (id), 
	FOREIGN KEY(table_id) REFERENCES tables (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	UNIQUE (request_key)
)

;

CREATE INDEX ix_orders_status ON orders (status);

CREATE INDEX ix_orders_visit_id ON orders (visit_id);

CREATE INDEX ix_orders_created_at ON orders (created_at);


CREATE TABLE reviews (
	id INTEGER NOT NULL, 
	visit_id INTEGER NOT NULL, 
	customer_id INTEGER NOT NULL, 
	food_rating INTEGER NOT NULL, 
	service_rating INTEGER NOT NULL, 
	comment VARCHAR(1000) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (visit_id, customer_id), 
	CHECK (food_rating BETWEEN 1 AND 5), 
	CHECK (service_rating BETWEEN 1 AND 5), 
	FOREIGN KEY(visit_id) REFERENCES visits (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id)
)

;


CREATE TABLE waiter_requests (
	id INTEGER NOT NULL, 
	visit_id INTEGER NOT NULL, 
	customer_id INTEGER NOT NULL, 
	kind VARCHAR(30) NOT NULL, 
	note VARCHAR(300) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	accepted_by INTEGER, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (status IN ('pending','accepted','completed')), 
	FOREIGN KEY(visit_id) REFERENCES visits (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(accepted_by) REFERENCES users (id)
)

;


CREATE TABLE order_items (
	id INTEGER NOT NULL, 
	order_id INTEGER NOT NULL, 
	menu_item_id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	quantity INTEGER NOT NULL, 
	unit_price INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (quantity BETWEEN 1 AND 50), 
	FOREIGN KEY(order_id) REFERENCES orders (id), 
	FOREIGN KEY(menu_item_id) REFERENCES menu_items (id)
)

;


CREATE TABLE payments (
	id INTEGER NOT NULL, 
	visit_id INTEGER NOT NULL, 
	customer_id INTEGER NOT NULL, 
	split_id INTEGER, 
	reference VARCHAR(80) NOT NULL, 
	request_key VARCHAR(80) NOT NULL, 
	amount INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	method VARCHAR(30) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (amount > 0), 
	CHECK (status IN ('success','failed')), 
	FOREIGN KEY(visit_id) REFERENCES visits (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(split_id) REFERENCES bill_splits (id), 
	UNIQUE (reference), 
	UNIQUE (request_key)
)

;

CREATE INDEX ix_payments_visit_id ON payments (visit_id);

CREATE INDEX ix_payments_created_at ON payments (created_at);


CREATE TABLE rewards (
	id INTEGER NOT NULL, 
	customer_id INTEGER NOT NULL, 
	order_id INTEGER, 
	source VARCHAR(100) NOT NULL, 
	points INTEGER NOT NULL, 
	description VARCHAR(150) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id), 
	UNIQUE (source)
)

;

CREATE INDEX ix_rewards_customer_id ON rewards (customer_id);
