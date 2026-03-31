import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.restaurant import Restaurant
from app.config import settings
from app.core.security import hash_password, generate_admin_id

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    async with session_maker() as db:
        # Check if already exists
        res = await db.execute(select(Restaurant).where(Restaurant.email == "admin@tablz.app"))
        existing = res.scalar_one_or_none()
        
        if existing:
            print(f"SUCCESS: System ID is '{existing.admin_id}' and Passcode is 'kitchen123!'")
            return

        # Generate admin_id
        count_result = await db.execute(select(func.count(Restaurant.id)))
        count = count_result.scalar() or 0
        admin_id = generate_admin_id(count + 1)

        # Create restaurant
        restaurant = Restaurant(
            id=uuid.uuid4(),
            admin_id=admin_id,
            name="Demo Kitchen",
            email="admin@tablz.app",
            password_hash=hash_password("kitchen123!"),
            email_verified=True,
            is_active=True,
            subscription_tier="pro",
            timezone="Asia/Kolkata",
            currency="INR"
        )
        db.add(restaurant)
        await db.commit()
        print(f"SUCCESS: System ID is '{admin_id}' and Passcode is 'kitchen123!'")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
