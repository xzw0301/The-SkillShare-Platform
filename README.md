# The-SkillShare-Platform

This is a full-stack project for a knowledge-sharing platform.

##SkillShare Platform - FastAPI Backend
This document details the setup and available endpoints for the SkillShare knowledge-sharing platform API, built using FastAPI, Pydantic, and bcrypt for security.

🚀 Getting Started (Local Development)
1. Prerequisites
You must have Python 3.9+ and the required packages installed:
        # Ensure you are in the 'backend' directory
        pip install -r requirements.txt
2. Secure Configuration
The application requires a secure secret key to run. This key is loaded from an environment file.
    1. Create the .env file: In the root of this backend/ directory, create a file named .env.
    2. Add the SECRET_KEY: Add a long, random string (at least 32 characters) for the SECRET_KEY.
        # backend/.env
        SECRET_KEY="a_very_secure_and_long_random_key_for_local_dev_only_123456" 
    3. Ensure Security: The application uses python-dotenv to load this file and validates that the key is present and secure, preventing accidental insecure deployment.
3. Running the Server
Run the application using Uvicorn with automatic reloading:
        uvicorn main:app --reload
The API will be accessible at http://127.0.0.1:8000.4. 
4. Documentation
Once running, access the interactive API documentation (Swagger UI) at:
http://127.0.0.1:8000/docs

🔒 Authentication & User Endpoints
| **Method** | **Endpoint** | **Description** | **Status Code** |
| :--- | :--- | :--- | :--- |
| **GET** | `/` | Health check for the API. | 200 |
| **POST** | `/users/` | **Create** a new user account. | 201 |
| **POST** | `/users/login` | Authenticate user and receive a **JWT Access Token**. | 200 |
| **GET** | `/users/me` | Retrieve the authenticated user's profile using the JWT. | 200 |

📰 Knowledge Card Endpoints (CRUD)

All Card endpoints except GET /cards/ and GET /cards/{card_id} require a valid JWT Access Token passed in the Authorization: Bearer <TOKEN> header.

| **Method** | **Endpoint** | **Description** | **Security** | 
 | ----- | ----- | ----- | ----- | 
| **POST** | `/cards/` | **CREATE** a new knowledge card. | Auth Required | 
| **GET** | `/cards/` | **READ** all knowledge cards. | Public | 
| **GET** | `/cards/{card_id}` | **READ** a specific card by ID. | Public | 
| **PUT** | `/cards/{card_id}` | **UPDATE** an existing card's title/content. | Auth & Authorization (Must be Author) | 
| **DELETE** | `/cards/{card_id}` | **DELETE** a card. | Auth & Authorization (Must be Author) |

💻 Development Log: Evolution and Security
This section tracks the major technical decisions, refactoring, and stability fixes implemented during development.

1. Database & Performance Refactoring

Change | Rationale | Impact | 
 | ----- | ----- | ----- | 
| **List to Dictionary Database** | The original in-memory database used slow lists (`db["users"]: []`). This was refactored to use dictionaries keyed by ID (`FAKE_USERS_DB: {}`). | **Performance:** Enabled faster, direct O(1) lookups and updates for users and cards, simulating a real database more accurately. | 
| **UUIDs for Card IDs** | Switched from sequential integers to **Universally Unique Identifiers (UUIDs)** for card IDs. | **Consistency:** Ensured every card ID is globally unique, avoiding collisions and following modern API design best practices. |

2. Stability and Compatibility Fixes
During the initial test runs, several errors and deprecation warnings were addressed:

| Issue / Warning | Cause | Resolution | 
 | ----- | ----- | ----- | 
| `AttributeError: 'TokenData' object has no attribute 'username'` | Tests were failing due to an issue with re-instantiating the `TokenData` Pydantic model in the `get_current_user` dependency. | Refactored `get_current_user` to directly use the extracted email string (`payload.get("sub")`) instead of wrapping it in the redundant `TokenData` object. | 
| `DeprecationWarning: datetime.utcnow()` | Python flagged the use of non-timezone-aware datetime functions. | Replaced all instances of `datetime.utcnow()` with the modern, timezone-aware **`datetime.now(timezone.utc)`** for future stability. |

3. Production Readiness and Security

| Change | Rationale | Impact | 
 | ----- | ----- | ----- | 
| **`python-dotenv` Integration** | The application relied on a hardcoded fallback `SECRET_KEY` for local testing. | **Clean Separation:** Sensitive variables are now loaded from the ignored `backend/.env` file, keeping secrets out of the codebase. | 
| **Strict SECRET_KEY Validation** | The code was updated to remove the insecure fallback key and validate the length of the loaded key (`>= 32 characters`). | **Security:** The application now explicitly **fails loudly** (`ValueError`) if the `SECRET_KEY` is missing or too short, ensuring it can never be deployed in an insecure state. |

