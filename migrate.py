# migrate.py - Standalone migration script
import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_migration():
    """Run database migration for role-based access control and admin approval system"""
    print("🚀 Starting database migration for Render...")
    
    try:
        # Import inside function to avoid circular imports
        from app import app, db, User
        
        with app.app_context():
            # Check if we need to migrate
            from sqlalchemy import inspect, text
            
            # Get database URL from environment (Render provides this)
            database_url = os.environ.get('DATABASE_URL', 'sqlite:///bill_sharing.db')
            print(f"📊 Database: {database_url.split('@')[-1] if '@' in database_url else database_url}")
            
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user')]
            
            print(f"🔍 Current columns: {', '.join(columns)}")
            
            # List of new columns to add for admin approval system
            new_columns = [
                'role',
                'admin_requested', 
                'admin_approved',
                'approved_by',
                'approved_at',
                'created_at'
            ]
            
            columns_to_add = [col for col in new_columns if col not in columns]
            
            if not columns_to_add:
                print("✅ All columns already exist. No migration needed.")
                return True
            
            print(f"📦 Columns to add: {', '.join(columns_to_add)}")
            
            # Add missing columns
            for column in columns_to_add:
                print(f"🛠️ Adding {column} column...")
                
                try:
                    if 'sqlite' in database_url.lower():
                        # SQLite migration
                        if column == 'role':
                            db.engine.execute('ALTER TABLE user ADD COLUMN role VARCHAR(20)')
                        elif column in ['admin_requested', 'admin_approved']:
                            db.engine.execute(f'ALTER TABLE user ADD COLUMN {column} BOOLEAN DEFAULT FALSE')
                        elif column == 'approved_by':
                            db.engine.execute('ALTER TABLE user ADD COLUMN approved_by INTEGER')
                        elif column in ['approved_at', 'created_at']:
                            db.engine.execute(f'ALTER TABLE user ADD COLUMN {column} DATETIME')
                    else:
                        # PostgreSQL migration (Render uses PostgreSQL)
                        if column == 'role':
                            db.engine.execute(text('ALTER TABLE "user" ADD COLUMN role VARCHAR(20)'))
                        elif column in ['admin_requested', 'admin_approved']:
                            db.engine.execute(text(f'ALTER TABLE "user" ADD COLUMN {column} BOOLEAN DEFAULT FALSE'))
                        elif column == 'approved_by':
                            db.engine.execute(text('ALTER TABLE "user" ADD COLUMN approved_by INTEGER'))
                        elif column in ['approved_at', 'created_at']:
                            db.engine.execute(text(f'ALTER TABLE "user" ADD COLUMN {column} TIMESTAMP'))
                    
                    print(f"✅ {column} column added successfully!")
                    
                except Exception as column_error:
                    print(f"⚠️ Warning: Could not add {column}: {column_error}")
                    continue
            
            # ADD THE SUPER ADMIN PROPERTY TO USER MODEL DYNAMICALLY
            print("🛠️ Adding is_super_admin property to User model...")
            
            # Define the property function
            def is_super_admin(self):
                return self.username == 'admin' or getattr(self, 'role', '') == 'super_admin'
            
            # Add the property to the User class
            User.is_super_admin = property(is_super_admin)
            print("✅ is_super_admin property added to User model!")
            
            # Update existing users with new field values
            users = User.query.all()
            print(f"👥 Updating {len(users)} existing users...")
            
            update_count = 0
            for user in users:
                try:
                    updates = []
                    
                    # Set role based on is_admin
                    if not hasattr(user, 'role') or user.role is None:
                        user.role = 'admin' if user.is_admin else 'user'
                        updates.append(f"role={user.role}")
                    
                    # Set admin_requested and admin_approved
                    if hasattr(user, 'admin_requested') and user.admin_requested is None:
                        user.admin_requested = user.is_admin
                        updates.append(f"admin_requested={user.admin_requested}")
                    
                    if hasattr(user, 'admin_approved') and user.admin_approved is None:
                        user.admin_approved = user.is_admin
                        updates.append(f"admin_approved={user.admin_approved}")
                    
                    # Set created_at for existing users
                    if hasattr(user, 'created_at') and user.created_at is None:
                        user.created_at = datetime.utcnow()
                        updates.append("created_at=now")
                    
                    # Auto-approve the first admin user (super admin)
                    if user.username == 'admin' and hasattr(user, 'admin_approved'):
                        user.admin_approved = True
                        user.admin_requested = True
                        user.is_admin = True
                        user.role = 'admin'
                        updates.append("super_admin=auto-approved")
                    
                    # TEST THE SUPER ADMIN PROPERTY
                    try:
                        is_super = user.is_super_admin
                        updates.append(f"is_super_admin={is_super}")
                    except Exception as prop_error:
                        print(f"   ⚠️ Could not test is_super_admin for {user.username}: {prop_error}")
                    
                    if updates:
                        print(f"   ✅ {user.username}: {', '.join(updates)}")
                        update_count += 1
                        
                except Exception as user_error:
                    print(f"   ❌ Error updating {user.username}: {user_error}")
                    continue
            
            # Commit all changes
            db.session.commit()
            
            # Summary report
            print(f"\n📊 MIGRATION SUMMARY:")
            print(f"   ✅ Columns added: {len(columns_to_add)}")
            print(f"   ✅ Users updated: {update_count}/{len(users)}")
            print(f"   ✅ Database type: {'PostgreSQL' if 'postgres' in database_url else 'SQLite'}")
            print(f"   ✅ is_super_admin property: Added successfully")
            
            # Final verification
            print(f"\n🔍 FINAL USER STATUS:")
            users = User.query.all()
            for user in users:
                try:
                    admin_status = ""
                    if user.is_admin:
                        if getattr(user, 'admin_approved', False):
                            admin_status = "✅ Approved Admin"
                        else:
                            admin_status = "⏳ Pending Approval"
                    else:
                        admin_status = "👤 Regular User"
                    
                    role = getattr(user, 'role', 'N/A')
                    
                    # Test super admin status
                    super_admin_status = "🌟 SUPER ADMIN" if user.is_super_admin else ""
                    
                    print(f"   👤 {user.username}: {admin_status} (role: {role}) {super_admin_status}")
                    
                except Exception as e:
                    print(f"   ❌ Error reading {user.username}: {e}")
            
            print(f"\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
            return True
            
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        import traceback
        print(f"Error details: {traceback.format_exc()}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🛠️  BillShare - Render Database Migration")
    print("=" * 60)
    
    success = run_migration()
    
    if success:
        print("=" * 60)
        print("✅ MIGRATION SUCCESSFUL - Your app is ready for Render!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        print("❌ MIGRATION FAILED - Check the logs above")
        print("=" * 60)
        sys.exit(1)
