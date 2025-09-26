
from typing import List, Optional, Annotated
import datetime
import uuid # for generating a long hexa char randomly
import os # for reading environment variables

# FastAPI imports
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# Pydantic imports for data modeling and validation
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime, timedelta, timezone

# Third-party library imports
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv # import library to load .env file

# - - - Configuration - - - 

# Load environment variables from the .env file in the backend directory
# This command looks for the .env file and loads its contents into os.environ
load_dotenv() 

# --- Security Configuration ---
# Security setup for password hashing and JWT
# BEST PRACTICE: read SECRET_KEY from environment variables.
# The second argument is a fallback key used for local development/testing only.
SECRET_KEY = os.getenv("SECRET_KEY") 
if SECRET_KEY is None or len(SECRET_KEY) < 32:
    # If the key is not set or too short, raise an error.
    # This ensures the app is never run in production with an insecure default.
    # For local development, set SECRET_KEY in your environment or a .env file.
    raise ValueError("SECRET_KEY environment variable is not set or is too short (min 32 chars).")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Dummy in-memory database (will be replaced by a real database later)
# We use a dictionaary where the key is the user ID and the value is the UserInDB model
FAKE_USERS_DB = {}
FAKE_CARDS_DB = {}

# OAuth2 scheme for token-based authentication
# This tells FastAPI to expect the token in the Authorization header as "Bearer <token>"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

# --- Password Hashing Setup ---
# This is a secure context for managing password hashes.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """
    Hashes a password using bcrypt.
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a password against a hash.
    """
    return pwd_context.verify(plain_password, hashed_password)

# --- JWT Token Functions ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Creates a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Pydantic Models ---
# These models define the data structure for the objects in our application.
# FastAPI uses them to validate request bodies and format responses.

# 1. Request Models (Input from user/client)
class UserBase(BaseModel):
    """
    Base model for user data that can be publicly shared or used in requests.
    """
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr 

class User(UserBase):
    """
    Model for user data with validation.
    This is used for incoming requests (e.g., signup, login).
    """
    password: str = Field(..., min_length=8)

    @field_validator('password')
    @classmethod
    def password_complexity(cls, value: str) -> str:
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        special_count = sum(1 for char in value if char in special_chars)

        if not any(char.isdigit() for char in value):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isalpha() for char in value):
            raise ValueError('Password must contain at least one letter')
        if special_count != 1:
            raise ValueError('Password must contain exactly one special character (!@#$%^&*).')
        return value

class Token(BaseModel):
    """
    Model for a JWT access token.
    """
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """
    Model for the data contained within a JWT.
    """
    email: Optional[str] = None

class CardBase(BaseModel):
    """
    Base model for a knowledge card.
    """
    title: str = Field(..., min_length=5, max_length=100)
    content: str = Field(..., min_length=10)
    
# 2. Database Models (Internal/Stored data)
class UserInDB(UserBase):
    """
    Internal model for a user stored in the database.
    This model contains the hashed password.
    """
    id: int
    created_at: datetime
    hashed_password: str

class CardInDB(CardBase):
    """
    Model for a knowledge card stored in the database.
    Adds a unique ID and other metadata.
    """
    id: uuid.UUID
    likes_count: int = 0
    created_at: datetime

class Like(BaseModel):
    """
    Model for a like on a card.
    """
    card_id: int
    user_id: int

class Comment(BaseModel):
    """
    Model for a comment on a card.
    """
    card_id: int
    user_id: int
    text: str

# 3. Response Models (Output to the client)
class MessageResponse(BaseModel):
    """
    A simple model for a success message.
    """
    message: str

class UserResponse(UserBase):
    """
    Model for user data returned in a response (without the password hash).
    """
    id: int
    created_at: datetime

class CardResponse(CardBase):
    """
    Model for the public card response.
    """
    id: uuid.UUID
    author_id: int
    created_at: datetime

# - - - Core Application Logic - - - 

# Function to simulate fetching a user by username or email
def get_user(username_or_email: str) -> Optional[UserInDB]:
    """Finds a user by matching username or email"""
    # Look up by email (used for login)
    for user_id in FAKE_USERS_DB:
        user = FAKE_USERS_DB[user_id]
        if user.email == username_or_email or user.username == username_or_email:
            return user
    return None

def authenticate_user(form_data: OAuth2PasswordRequestForm) -> Optional[UserInDB]:
    """Authenticates a user by email and password"""
    user = get_user(form_data.username)
    if not user:
        return None
    if not verify_password(form_data.password, user.hashed_password):
        return None
    return user

# --- Dependency Functions ---
# This function will be used by other endpoints to protect them.
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserInDB:
    """
    Dependency that extracts and validates the JWT token to get the current authenticated user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the token using the secret key and algorithm
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
    except JWTError:
        # If decoding fails (e.g., token expired, invalid signature)
        raise credentials_exception
    
    # Use the username from the token to look up the user in the database
    user = get_user(username)
    if user is None:
        raise credentials_exception
    
    return user

# - - - FASTAPI application setup - - -
app = FastAPI(
    title="SkillShare Platform API",
    description="Backend for a skill-sharing platform built with FastAPI.",
    version="0.1.0"
)

# --- API Endpoints ---
# These endpoints implement the core logic for the platform.

@app.get("/")
def read_root():
    """Root endpoint for a simple health check."""
    return {"message": "Welcome to the SkillShare Platform API!"}

# Endpoint for creating a new user (User Management).
@app.post("/users/", response_model=UserResponse)
async def create_user(user: User):
    """
    Create a new user account.
    """
    if get_user(user.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash the password before storing it.
    hashed_password = get_password_hash(user.password)
    
    # Simulate saving to the database
    new_id = len(FAKE_USERS_DB) + 1
    new_user_in_db = UserInDB(
        id=new_id,
        username=user.username,
        email=user.email,
        created_at=datetime.now(timezone.utc),
        hashed_password=hashed_password
    )
    FAKE_USERS_DB[new_id] = new_user_in_db

    # Return the user data without the password hash.
    return new_user_in_db

# Endpoint for login (User Management)
@app.post("/users/login", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    Log in to an account and get an access token.
    """
    user = authenticate_user(form_data)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # The subject of the token is the email (which is unique)
    access_token = create_access_token(
        data={"sub": user.email}
    )
    return {"access_token": access_token, "token_type": "bearer"}

# A new endpoint to get the currently logged-in user's data.
# This endpoint demonstrates how to use the dependency to protect an endpoint.
@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[UserInDB, Depends(get_current_user)]):
    """
    Get the currently authenticated user.
    """
    # Use the UserResponse model to strip the password hash from the response
    return current_user

# Endpoint for creating a new card (Data Management).
# This endpoint now requires authentication.
@app.post("/cards/", response_model=CardResponse)
async def create_card(card: CardBase, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    """
    Create a new knowledge card.
    
    Use the current_user object to get the author's ID
    Requires anthentication.
    The author_id is automatically taken from the authenticated user.
    """
    # 1. Simulate saving the new card to the database
    new_id = uuid.uuid4()
    new_card_in_db = CardInDB(
        id=new_id, 
        author_id = current_user.id,
        title=card.title,
        content=card.content,
        created_at=datetime.now(timezone.utc)
        )
    FAKE_CARDS_DB[new_id] = new_card_in_db
    # 2. Return the public card response
    return new_card_in_db

# Endpoint for retrieving a single card.
@app.get("/cards/{card_id}", response_model=CardResponse)
async def get_card(card_id: uuid.UUID):
    """
    Retrieve a specific card by its ID.
    """
    card = FAKE_CARDS_DB.get(card_id)
    if card:
        return card
    raise HTTPException(status_code=404, detail="Card not found")

# Endpoint for retrieving all cards.
@app.get("/cards/", response_model=List[CardResponse])
async def get_all_cards():
    """
    Retrieve a list of all knowledge cards.
    """
    return FAKE_CARDS_DB.values()

# Endpoint for updating a card.
@app.put("/cards/{card_id}", response_model=CardResponse)
async def update_card(
    card_id: uuid.UUID, 
    card_update: CardBase, 
    current_user: Annotated[UserInDB, Depends(get_current_user)]):
    """
    Update an existing card.
    Requires authentication and authorization (must be the card's author).
    """
    existing_card = FAKE_CARDS_DB.get(card_id)
    if not existing_card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    if existing_card.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this card")
            
    updated_card = CardInDB(
        id=card_id,
        author_id=existing_card.author_id,
        title=card_update.title, 
        content=card_update.content, 
        created_at=existing_card.created_at)
    FAKE_CARDS_DB[card_id] = updated_card

    return updated_card
    

# Endpoint for deleting a card.
@app.delete("/cards/{card_id}", response_model=MessageResponse)
async def delete_card(card_id: uuid.UUID, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    """
    Delete a card by its ID.
    Requires authentication.
    """
    existing_card = FAKE_CARDS_DB.get(card_id)
    if not existing_card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    if existing_card.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete the card")
    
    del FAKE_CARDS_DB[card_id]
    
    return {"message": "Card deleted successfully"}