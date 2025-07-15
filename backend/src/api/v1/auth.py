from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.security import create_access_token, verify_password
from src.core.settings import get_settings
from src.db.postgresql import get_session
from src.db.models.user import User as UserModel
from pydantic import BaseModel, EmailStr
from src.core.security import get_password_hash
import datetime

settings = get_settings()

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str

DBSession = Annotated[AsyncSession, Depends(get_session)]

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_create: UserCreate, session: DBSession):
    statement = select(UserModel).where(UserModel.email == user_create.email)
    existing_user = (await session.exec(statement)).first()
    if existing_user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    
    new_user = UserModel(
        email=user_create.email, 
        hashed_password=get_password_hash(user_create.password)
    )
    session.add(new_user)
    await session.commit()
    return {"message": "User created successfully"}

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
    session: DBSession
):
    statement = select(UserModel).where(UserModel.email == form_data.username)
    user = (await session.exec(statement)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            {"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")