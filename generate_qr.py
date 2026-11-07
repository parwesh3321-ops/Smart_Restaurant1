"""Export printable table QR PNGs using the current Settings base URL."""
from pathlib import Path
import qrcode
from sqlalchemy import select
from app import create_app
from database import db
from models import Restaurant, DiningTable

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        restaurant = db.session.scalar(select(Restaurant))
        if not restaurant:
            raise SystemExit('First run: python init_db.py')
        folder = Path(__file__).resolve().parent / 'qr_codes'
        folder.mkdir(exist_ok=True)
        for table in db.session.scalars(select(DiningTable).where(DiningTable.active.is_(True))):
            qrcode.make(restaurant.public_base_url + '/menu/' + table.token).save(folder / f'table-{table.number:02}.png')
        print(f'QR images saved in {folder}\nBase URL: {restaurant.public_base_url}')
