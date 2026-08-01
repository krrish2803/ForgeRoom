import sys
import os

# Add the backend folder to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("Verifying ForgeRoom Backend imports and syntax...")

try:
    from app.config import settings
    print("✓ config.py loaded successfully.")
    
    from app.database import get_db
    print("✓ database.py loaded successfully.")
    
    from app.models.user import UserResponse
    from app.models.room import RoomResponse
    from app.models.message import MessageResponse
    print("✓ models/ loaded successfully.")
    
    from app.auth import security, routes
    print("✓ auth/ loaded successfully.")
    
    from app.rooms import routes as room_routes
    print("✓ rooms/ loaded successfully.")
    
    from app.websocket.manager import manager
    print("✓ websocket/ loaded successfully.")
    
    from app.agent import nvidia, checkpoint, graph
    print("✓ agent/ loaded successfully.")
    
    from app.main import app
    print("✓ main.py loaded successfully.")
    
    print("\n🎉 ALL BACKEND PACKAGES IMPORTED SUCCESSFULLY WITH NO SYNTAX ERRORS!")
    sys.exit(0)

except Exception as e:
    print(f"\n❌ VERIFICATION FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
