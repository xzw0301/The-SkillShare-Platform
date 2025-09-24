
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Annotated
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt

# Create an instance of the FastAPI application.
app = FastAPI()

# --- Security Configuration ---
# You should use a strong, randomly generated secret key in a real application.
# It should be stored securely, e.g., in an environment variable.
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# We use HTTPBearer to get the token directly from the Authorization header.
# This forces the Swagger UI to display a simple "Value" input.
security_scheme = HTTPBearer()

# --- Password Hashing Setup ---
# This is a secure context for managing password hashes.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """
    Hashes a password.
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
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Pydantic Models ---
# These models define the data structure for the objects in our application.
# FastAPI uses them to validate request bodies and format responses.

class User(BaseModel):
    """
    Model for user data with validation.
    This is used for incoming requests (e.g., signup, login).
    """
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

    @validator('password')
    def password_complexity(cls, v):
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        special_count = sum(1 for char in v if char in special_chars)

        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isalpha() for char in v):
            raise ValueError('Password must contain at least one letter')
        if special_count != 1:
            raise ValueError('Password must contain exactly one special character')
        return v

class UserInDB(BaseModel):
    """
    Internal model for a user stored in the database.
    This model contains the hashed password.
    """
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    hashed_password: str

class Token(BaseModel):
    """
    Model for a JWT access token.
    """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """
    Model for the data contained within a JWT.
    """
    email: Optional[str] = None

class UserResponse(BaseModel):
    """
    Model for user data returned in a response (without the password hash).
    """
    id: int
    username: str
    email: EmailStr
    created_at: datetime

class Card(BaseModel):
    """
    Model for a knowledge card.
    """
    title: str = Field(..., min_length=5, max_length=100)
    content: str = Field(..., min_length=10)
    author_id: int
    tags: Optional[List[str]] = []

class CardInDB(Card):
    """
    Model for a knowledge card stored in the database.
    Adds a unique ID and other metadata.
    """
    id: int
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

class MessageResponse(BaseModel):
    """
    A simple model for a success message.
    """
    message: str

# In-memory "database" to store our data.
# In a real application, this would be a real database like PostgreSQL.
db = {
    "users": [],
    "cards": [],
    "likes": [],
    "comments": []
}

# --- Dependency Functions ---
# This function will be used by other endpoints to protect them.
async def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)]):
    """
    Verifies the JWT token and returns the current user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    # In a real app, you would look up the user in the database
    user = next((u for u in db["users"] if u.email == token_data.email), None)
    if user is None:
        raise credentials_exception
    return user


# --- API Endpoints ---
# These endpoints implement the core logic for your platform.

# Endpoint for creating a new user (User Management).
@app.post("/users/", response_model=UserResponse)
async def create_user(user: User):
    """
    Create a new user.
    """
    # Check if a user with this email already exists
    if any(u.email == user.email for u in db["users"]):
        raise HTTPException(status_code=400, detail="Email already registered")
        
    new_id = len(db["users"]) + 1
    # Hash the password before storing it.
    hashed_password = get_password_hash(user.password)
    
    # Create the user object with the hashed password for internal storage.
    new_user_in_db = UserInDB(
        id=new_id,
        username=user.username,
        email=user.email,
        created_at=datetime.now(),
        hashed_password=hashed_password
    )
    db["users"].append(new_user_in_db)

    # Return the user data without the password hash.
    return new_user_in_db

# Endpoint for login (User Management)
@app.post("/users/login", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    Log in to an account and get an access token.
    """
    found_user = next((u for u in db["users"] if u.email == form_data.username), None)

    if found_user and verify_password(form_data.password, found_user.hashed_password):
        # Create an access token for the user.
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": found_user.email}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

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
@app.post("/cards/", response_model=CardInDB)
async def create_card(card: Card, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    """
    Create a new knowledge card.
    """
    # Use the current_user object to get the author's ID
    card.author_id = current_user.id
    
    new_id = len(db["cards"]) + 1
    new_card = CardInDB(id=new_id, created_at=datetime.now(), **card.dict())
    db["cards"].append(new_card)
    return new_card

# Endpoint for retrieving a single card.
@app.get("/cards/{card_id}", response_model=CardInDB)
async def get_card(card_id: int):
    """
    Retrieve a specific card by its ID.
    """
    for card in db["cards"]:
        if card.id == card_id:
            return card
    raise HTTPException(status_code=404, detail="Card not found")

# Endpoint for retrieving all cards.
@app.get("/cards/", response_model=List[CardInDB])
async def get_all_cards():
    """
    Retrieve a list of all knowledge cards.
    """
    return db["cards"]

# Endpoint for updating a card.
@app.put("/cards/{card_id}", response_model=CardInDB)
async def update_card(card_id: int, card_update: Card, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    """
    Update an existing card.
    Requires authentication.
    """
    for index, card in enumerate(db["cards"]):
        if card.id == card_id:
            # Check if the current user is the author of the card
            if card.author_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this card")
            
            updated_card = CardInDB(id=card_id, created_at=card.created_at, **card_update.dict())
            db["cards"][index] = updated_card
            return updated_card
    raise HTTPException(status_code=404, detail="Card not found")

# Endpoint for deleting a card.
@app.delete("/cards/{card_id}")
async def delete_card(card_id: int, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    """
    Delete a card by its ID.
    Requires authentication.
    """
    for index, card in enumerate(db["cards"]):
        if card.id == card_id:
            # Check if the current user is the author of the card
            if card.author_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this card")
            
            del db["cards"][index]
            return {"message": "Card deleted successfully"}
    raise HTTPException(status_code=404, detail="Card not found")