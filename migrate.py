# migrate.py - Standalone migration script
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def run_migration():
    """Run database migration for role-based access control"""
    print("Starting database migration...")
    
    try:
        with app.app_context():
            # Check if we need to migrate
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user')]
            
            if 'role' not in columns:
                print("Adding role column to user table...")
                
                # Handle different database types
                database_url = os.environ.get('DATABASE_URL', 'sqlite:///bill_sharing.db')
                
                if 'sqlite' in database_url:
                    # SQLite migration
                    db.engine.execute('ALTER TABLE user ADD COLUMN role VARCHAR(20)')
                else:
                    # PostgreSQL migration
                    db.engine.execute('ALTER TABLE "user" ADD COLUMN role VARCHAR(20)')
                
                print("Role column added successfully!")
                
                # Update existing users
                users = User.query.all()
                for user in users:
                    user.role = 'admin' if user.is_admin else 'user'
                    print(f"Updated user {user.username} with role: {user.role}")
                
                db.session.commit()
                print("User roles updated successfully!")
                
            else:
                print("Role column already exists. No migration needed.")
                
            # Verify migration
            users = User.query.all()
            print("\nCurrent users and roles:")
            for user in users:
                print(f"  - {user.username}: is_admin={user.is_admin}, role={user.role}")
                
            print("\n✅ Migration completed successfully!")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.session.rollback()

if __name__ == '__main__':
    run_migration()
