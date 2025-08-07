from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenPair(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    email: EmailStr
    username: str

class TokenData(BaseModel):
    email: str | None = None 