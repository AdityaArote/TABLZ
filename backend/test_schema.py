from app.schemas.auth import LoginRequest
from pydantic import ValidationError

try:
    req = LoginRequest(admin_id="TBZ-260001", password="kitchen123!")
    print("SUCCESS: VALID")
except ValidationError as e:
    print(f"ERROR: {e.json()}")
