import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.restaurant import Restaurant
from app.config import settings

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    async with session_maker() as db:
        res = await db.execute(select(Restaurant).where(Restaurant.email == "kitchen@tablz.app"))
        restaurant = res.scalar_one_or_none()
        if restaurant:
            print(f"ID: {restaurant.admin_id}, Password: password123")
        else:
            print("NOT FOUND")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
