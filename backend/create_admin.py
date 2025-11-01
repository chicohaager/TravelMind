"""
Create an admin user for TravelMind
"""
import asyncio
import sys
from sqlalchemy import select
from models.database import AsyncSessionLocal, init_db
from models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_admin_user(username: str, email: str, password: str, full_name: str = None):
    """Create an admin user in the database"""

    # Initialize database
    await init_db()

    async with AsyncSessionLocal() as session:
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.username == username)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"❌ User '{username}' already exists!")

            # Ask if we should make them admin
            make_admin = input(f"Make '{username}' an admin? (y/n): ").lower()
            if make_admin == 'y':
                existing_user.is_superuser = True
                await session.commit()
                print(f"✅ User '{username}' is now an admin!")
            return

        # Hash the password
        hashed_password = pwd_context.hash(password)

        # Create the admin user
        admin_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name or username,
            is_active=True,
            is_superuser=True
        )

        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)

        print(f"✅ Admin user created successfully!")
        print(f"   Username: {admin_user.username}")
        print(f"   Email: {admin_user.email}")
        print(f"   Full Name: {admin_user.full_name}")
        print(f"   Admin: {admin_user.is_superuser}")
        print(f"\n🔑 You can now login with these credentials.")


async def main():
    """Main function"""
    print("=" * 50)
    print("TravelMind - Create Admin User")
    print("=" * 50)
    print()

    # Get user input
    username = input("Enter username (default: admin): ").strip() or "admin"
    email = input("Enter email (default: admin@travelmind.local): ").strip() or "admin@travelmind.local"
    full_name = input("Enter full name (default: Admin User): ").strip() or "Admin User"
    password = input("Enter password (default: admin123): ").strip() or "admin123"

    print()
    print("Creating admin user...")
    print()

    await create_admin_user(username, email, password, full_name)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
