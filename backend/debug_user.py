import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.restaurant import Restaurant
from app.config import settings
from app.core.security import verify_password

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    async with session_maker() as db:
        res = await db.execute(select(Restaurant).where(Restaurant.admin_id == "TBZ-260001"))
        r = res.scalar_one_or_none()
        if r:
            print(f"ID: {r.admin_id}")
            print(f"Email: {r.email}")
            print(f"Active: {r.is_active}")
            print(f"Verified: {r.email_verified}")
            is_valid = verify_password("kitchen123!", r.password_hash)
            print(f"Password Check ('kitchen123!'): {is_valid}")
        else:
            print("USER NOT FOUND")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
