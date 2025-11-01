"""
Settings Manager
Helper functions to read and write application settings
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.settings import Settings


async def get_setting(db: AsyncSession, key: str, default=None):
    """
    Get a setting value by key
    Returns the typed value or default if not found
    """
    result = await db.execute(select(Settings).where(Settings.key == key))
    setting = result.scalar_one_or_none()

    if setting:
        return setting.get_typed_value()
    return default


async def set_setting(db: AsyncSession, key: str, value: str, value_type: str = "string", description: str = None):
    """
    Set a setting value
    Creates new setting if it doesn't exist, updates if it does
    """
    result = await db.execute(select(Settings).where(Settings.key == key))
    setting = result.scalar_one_or_none()

    if setting:
        # Update existing
        setting.value = str(value)
        if value_type:
            setting.value_type = value_type
        if description:
            setting.description = description
    else:
        # Create new
        setting = Settings(
            key=key,
            value=str(value),
            value_type=value_type,
            description=description
        )
        db.add(setting)

    await db.commit()
    return setting


async def is_registration_open(db: AsyncSession) -> bool:
    """
    Check if new user registration is allowed
    """
    return await get_setting(db, "registration_open", default=True)


async def get_max_users(db: AsyncSession) -> int:
    """
    Get maximum allowed users (0 = unlimited)
    """
    return await get_setting(db, "max_users", default=0)


async def get_user_count(db: AsyncSession) -> int:
    """
    Get current number of users
    """
    from sqlalchemy import func
    from models.user import User

    result = await db.execute(select(func.count(User.id)))
    return result.scalar()


async def can_register_new_user(db: AsyncSession) -> tuple[bool, str]:
    """
    Check if a new user can be registered
    Returns (can_register, reason)
    """
    # Check if registration is open
    if not await is_registration_open(db):
        return False, "Registrierung ist derzeit geschlossen"

    # Check user limit
    max_users = await get_max_users(db)
    if max_users > 0:
        current_users = await get_user_count(db)
        if current_users >= max_users:
            return False, f"Maximale Anzahl von {max_users} Benutzern erreicht"

    return True, "OK"
