from passlib.context import CryptContext
from datetime import timedelta, datetime, timezone
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from typing import Optional
import jwt
from dotenv import load_dotenv
import os

load_dotenv()




SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    print("🔑 Verifying password...")
    result = pwd_context.verify(plain_password, hashed_password)
    print(f"✅ Password verification result: {result}")
    return result

def get_password_hash(password: str) -> str:
    print("🔒 Hashing password...")
    hashed = pwd_context.hash(password)
    print(f"🔑 Hashed password: {hashed}")
    return hashed

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    print("🪙 Creating access token...")
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    print(f"📅 Token expiration set to: {expire}")
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    print(f"🔐 Generated token: {token}")
    return token

