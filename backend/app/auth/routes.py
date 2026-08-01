from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user
)
from app.database import get_db
from app.models.user import UserCreate, UserLogin, UserResponse, UserInDB, Token
import jwt
from jwt.exceptions import PyJWTError
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate):
    db = get_db()
    
    # Check if user already exists
    existing_user = await db["users"].find_one({"email": user_in.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
        
    # Create new user
    hashed_password = get_password_hash(user_in.password)
    user_db = UserInDB(
        name=user_in.name,
        email=user_in.email,
        hashed_password=hashed_password
    )
    
    # Save to MongoDB
    result = await db["users"].insert_one(user_db.model_dump(by_alias=True, exclude=["id"]))
    user_doc = await db["users"].find_one({"_id": result.inserted_id})
    return UserResponse(**user_doc)

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    db = get_db()
    
    # Find user
    user_doc = await db["users"].find_one({"email": credentials.email})
    if not user_doc or not verify_password(credentials.password, user_doc["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id = str(user_doc["_id"])
    
    # Generate tokens
    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)
    
    return Token(access_token=access_token, refresh_token=refresh_token)

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh credentials",
    )
    try:
        payload = jwt.decode(refresh_token, settings.jwt_refresh_secret_key, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "refresh":
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception
        
    db = get_db()
    # Confirm user exists
    from bson import ObjectId
    user_doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        raise credentials_exception
        
    # Issue new access token
    new_access_token = create_access_token(subject=user_id)
    new_refresh_token = create_refresh_token(subject=user_id)
    
    return Token(access_token=new_access_token, refresh_token=new_refresh_token)

@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: UserInDB = Depends(get_current_user)):
    return UserResponse(
        _id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        created_at=current_user.created_at
    )
