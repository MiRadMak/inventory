from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему'
    login_manager.login_message_category = 'info'

    from app.auth import auth_bp
    from app.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        from app.models import User, Equipment

        try:
            db.create_all()

            if User.query.first() is None:
                print("Первый запуск — создаю администратора и демо-данные...")

                # Создаём пользователей
                admin = User(username='admin', email='admin@vu.ru', role='admin')
                admin.set_password('admin123')

                user = User(username='user', email='user@vu.ru', role='user')
                user.set_password('user123')

                db.session.add_all([admin, user])
                db.session.commit()

                demo_equipment = [
                    Equipment(
                        name='Сервер Dell PowerEdge R740',
                        model='R740',
                        type='Сервер',
                        location='Серверная 301',
                        status='Активно',
                        inventory_number='INV-0001',
                        ip_address='192.168.10.10',
                        description='Основной сервер кафедры',
                        created_by=1
                    ),
                    Equipment(
                        name='Проектор Epson EB-X51',
                        model='EB-X51',
                        type='Проектор',
                        location='Аудитория 101',
                        status='Активно',
                        inventory_number='PRJ-001',
                        description='Проектор для лекционных занятий',
                        created_by=1
                    ),
                    Equipment(
                        name='МФУ Kyocera ECOSYS M3145dn',
                        model='M3145dn',
                        type='МФУ',
                        location='Кабинет 205',
                        status='Активно',
                        inventory_number='MFP-001',
                        ip_address='192.168.10.55',
                        description='Многофункциональное устройство',
                        created_by=1
                    ),
                    Equipment(
                        name='Ноутбук Lenovo ThinkPad T14',
                        model='T14 Gen 3',
                        type='Ноутбук',
                        location='Кабинет 410',
                        status='На обслуживании',
                        inventory_number='LAP-042',
                        ip_address='192.168.20.142',
                        description='Ноутбук для преподавателя',
                        created_by=1
                    ),
                    Equipment(
                        name='Коммутатор Cisco Catalyst 2960',
                        model='WS-C2960X-24TS-L',
                        type='Коммутатор',
                        location='Шкаф 302',
                        status='Активно',
                        inventory_number='SW-005',
                        ip_address='192.168.1.1',
                        description='Сетевой коммутатор 24 порта',
                        created_by=1
                    ),
                    Equipment(
                        name='Рабочая станция HP Z4',
                        model='Z4 G4',
                        type='Компьютер',
                        location='Лаборатория 315',
                        status='Неактивно',
                        inventory_number='PC-128',
                        description='Мощная рабочая станция для CAD',
                        created_by=1
                    ),
                ]
                db.session.add_all(demo_equipment)
                db.session.commit()

                print("ДЕМО-ДАННЫЕ СОЗДАНЫ!")
                print("   admin / admin123")
                print("   user / user123")
            else:
                print(f"База уже инициализирована: {User.query.count()} пользователей, "
                      f"{Equipment.query.count()} единиц оборудования")

        except Exception as e:
            print(f"Ошибка подключения к базе данных: {e}")
            print("Подсказки:")
            if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
                print(" → Вы используете SQLite — всё должно работать")
            else:
                print(" → Попробуйте запустить: python setup_postgres.py")
                print(" → Или временно переключитесь на SQLite: USE_SQLITE=1 python run.py")
            raise

    return app