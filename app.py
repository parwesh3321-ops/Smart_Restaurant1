"""Application factory, security policy and development entry point."""
import os
import secrets
from pathlib import Path
from flask import Flask, request, session, jsonify, render_template
from sqlalchemy import text, select
from sqlalchemy.exc import IntegrityError, OperationalError
from werkzeug.exceptions import HTTPException
from config import Config, ROOT
from database import db


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    (ROOT / 'database').mkdir(exist_ok=True)
    if not app.config.get('SECRET_KEY'):
        path = ROOT / 'database' / '.secret_key'
        if not path.exists():
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(fd, 'w') as file:
                    file.write(secrets.token_hex(32))
            except FileExistsError:
                pass
        app.config['SECRET_KEY'] = path.read_text().strip()
    db.init_app(app)
    from models import Restaurant, DiningTable
    from routes.auth import auth
    from routes.staff import staff
    from routes.customer import customer
    from routes.public import public
    app.register_blueprint(auth)
    app.register_blueprint(staff)
    app.register_blueprint(customer)
    app.register_blueprint(public)

    @app.before_request
    def protect_requests():
        session.setdefault('csrf', secrets.token_urlsafe(32))
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
            if not secrets.compare_digest(token, session['csrf']):
                return jsonify(error='Your session changed. Refresh the page and try again.'), 400
            # Lock all writes before reading balances. Prevents concurrent double payments,
            # competing table joins, and stale split totals. MySQL uses a restaurant row lock.
            if db.engine.dialect.name == 'sqlite':
                db.session.execute(text('BEGIN IMMEDIATE'))
            else:
                db.session.execute(select(Restaurant).with_for_update()).all()

    @app.after_request
    def finish_request(response):
        # Every write endpoint commits explicitly. Release read/write locks on all paths.
        db.session.rollback()
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if not request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.errorhandler(HTTPException)
    def http_error(exc):
        if request.path.startswith('/api/'):
            return jsonify(error=exc.description), exc.code
        return render_template('error.html', code=exc.code, message=exc.description), exc.code

    @app.errorhandler(IntegrityError)
    def conflict(_):
        db.session.rollback()
        return jsonify(error='This record already exists or is referenced by another record.'), 409

    @app.errorhandler(OperationalError)
    def busy(exc):
        db.session.rollback()
        app.logger.warning('Database operation failed: %s', type(exc).__name__)
        return jsonify(error='Database unavailable. Initialize it with python init_db.py, or retry shortly if it is busy.'), 503

    @app.errorhandler(500)
    def server_error(_):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify(error='Something went wrong. Please try again.'), 500
        return render_template('error.html', code=500, message='Something went wrong. Please try again.'), 500

    @app.get('/health')
    def health():
        db.session.execute(select(Restaurant.id).limit(1)).all()
        return jsonify(status='ok')

    @app.cli.command('init-db')
    def initialize():
        from seed import seed_database
        db.create_all()
        seed_database(app.config['PUBLIC_BASE_URL'])
        print('Database ready. Open http://127.0.0.1:5001')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host=os.getenv('HOST', '127.0.0.1'), port=app.config['PORT'], debug=False)
