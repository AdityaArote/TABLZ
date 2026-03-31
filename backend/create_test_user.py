import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.services.auth_service import AuthService
from app.config import settings
from app.database import Base

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    async with session_maker() as db:
        try:
            # Register user
            res = await AuthService.register(
                db=db,
                name="Demo Kitchen",
                email="kitchen@tablz.app",
                password="password123",
            )
            admin_id = res["admin_id"]
            token = res["_dev_verification_token"]
            
            # Verify user
            await AuthService.verify_email(db, token)
            print(f"SUCCESS: System ID is '{admin_id}' and Passcode is 'password123'")
        except Exception as e:
            print("ERROR", e)
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
