"""Create tables and seed sample data without deleting existing records."""
from app import create_app
from database import db
from seed import seed_database

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        added = seed_database(app.config['PUBLIC_BASE_URL'])
        print('Database created with demo accounts and sample data.' if added else 'Database already initialized. Your data was preserved.')
        print('Next: python app.py\nOpen: http://127.0.0.1:5001')
