import psycopg
import sys



def setup_postgres_database():
    """Создание базы данных и пользователя для PostgreSQL"""

    print("🚀 Настройка PostgreSQL базы данных...")

    try:
        conn = psycopg.connect(
            "postgresql://postgres:postgres@localhost:5432/postgres"
        )
        conn.autocommit = True

        with conn.cursor() as cur:
            print("👤 Создаю пользователя inventory_user...")
            try:
                cur.execute("CREATE USER inventory_user WITH PASSWORD 'Beliimay123';")
                print("✅ Пользователь создан")
            except Exception as e:
                print(f"ℹ️ Пользователь уже существует: {e}")

            print("🗄️ Создаю базу данных inventory...")
            try:
                cur.execute("CREATE DATABASE inventory OWNER inventory_user;")
                print("✅ База данных создана")
            except Exception as e:
                print(f"ℹ️ База данных уже существует: {e}")

            print("🔑 Настраиваю права...")
            cur.execute("GRANT ALL PRIVILEGES ON DATABASE inventory TO inventory_user;")
            print("✅ Права настроены")

        print("\n🎉 Настройка PostgreSQL завершена успешно!")
        print("📋 Дальнейшие действия:")
        print("   1. Запустите приложение: python run.py")
        print("   2. Откройте в браузере: http://localhost:5000")
        print("   3. Используйте логины: admin/admin123 или user/user123")
        return True

    except Exception as e:
        print(f"\n❌ Ошибка настройки PostgreSQL: {e}")
        print("\n📋 ВОЗМОЖНЫЕ РЕШЕНИЯ:")
        print("1. Убедитесь, что PostgreSQL установлен и запущен")
        print("2. Проверьте пароль пользователя postgres")
        print("3. Или используйте Docker:")
        print("   docker-compose up -d")
        print("4. Или временно используйте SQLite")
        return False

    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    setup_postgres_database()