import sys
import os

# Add your project directory to the Python path
project_home = '/home/NPrem30/bill_sharing_app'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['FLASK_APP'] = 'app.py'

# Import your Flask app
from app import app as application

# Initialize database
print("Initializing database...")
try:
    with application.app_context():
        from app import db
        db.create_all()

        # Create default admin user if not exists
        from app import User
        from werkzeug.security import generate_password_hash

        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                password=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created")
    print("Database initialized successfully")
except Exception as e:
    print(f"Database initialization failed: {e}")