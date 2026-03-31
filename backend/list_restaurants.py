import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.restaurant import Restaurant
from app.config import settings

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    async with session_maker() as db:
        res = await db.execute(select(Restaurant))
        restaurants = res.scalars().all()
        if restaurants:
            for r in restaurants:
                print(f"ID: {r.admin_id}, Email: {r.email}, Name: {r.name}")
        else:
            print("NO RESTAURANTS CONFIGURED")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
