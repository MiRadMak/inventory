from app import create_app
import os

os.environ['USE_SQLITE'] = '1'

app = create_app()

if __name__ == '__main__':
    print("🚀 Starting Inventory Management System")
    print("📍 Using SQLite database: inventory.db")
    print("👤 Demo accounts:")
    print("   - Admin: admin / admin123")
    print("   - User:  user / user123")
    print("🌐 Server: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)