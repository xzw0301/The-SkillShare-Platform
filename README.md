# The-SkillShare-Platform

This is a full-stack project for a knowledge-sharing platform.

## SkillShare Platform Backend API
This project is a RESTful API built with FastAPI that serves as the backend for a knowledge-sharing platform. It handles user authentication, card creation, and basic data management.

### Features
* User registration with password validation

* User login with JWT (JSON Web Token) authentication

* Protected routes that require a valid access token

* CRUD operations for knowledge cards

* In-memory database for demonstration purposes

### Getting Started
Prerequisites
You need Python 3.8+ and pip installed.

Installation
Clone the repository:

        git clone [https://github.com/your-username/the-skillshare-platform.git](https://github.com/your-username/the-skillshare-platform.git)
        cd the-skillshare-platform/backend


Create and activate a virtual environment:

        python -m venv venv
        source venv/bin/activate  # On Windows, use `venv\Scripts\activate`


Install the dependencies:

        pip install "fastapi[all]" "passlib[bcrypt]" "python-jose[cryptography]"


Running the Server
To start the API server, run the following command from the backend directory:

        uvicorn main:app --reload


The server will be available at http://127.0.0.1:8000.

### Testing the API Endpoints
You can manually test all API endpoints using the interactive documentation available at http://127.0.0.1:8000/docs.

1. Sign Up:

*  Open POST /users/ and click "Try it out."

* Enter a username, email, and a password that meets the security requirements.

* Click "Execute" and verify the 200 status code.

2. Log In and Get a Token:

* Open POST /users/login and click "Try it out."

* Enter the email and password you just used.

* Click "Execute" and copy the access_token from the response body.

3. Authorize Your Requests:

* Click the green "Authorize" button at the top of the page.

* Paste the copied token into the "Value" field and click "Authorize."

4. Test Protected Endpoints:

* Now, test a protected endpoint like GET /users/me or POST /cards/ to ensure your token is working. The lock icon will be closed for authorized requests.

### API Endpoints
The API documentation is automatically generated and available at http://127.0.0.1:8000/docs.

### Authentication
POST /users/

* Description: Creates a new user.

* Request Body: username, email, password.

* Returns: New user information.

POST /users/login

* Description: Logs in a user and returns a JWT access token.

* Request Body: username (email), password.

* Returns: access_token and token_type.

Protected Endpoints (Require a Bearer Token)
GET /users/me

* Description: Retrieves information about the currently authenticated user.

POST /cards/

* Description: Creates a new knowledge card. The author_id is automatically set to the authenticated user's ID.

* Request Body: title, content.

PUT /cards/{card_id}

* Description: Updates an existing card.

DELETE /cards/{card_id}

* Description: Deletes a card.

Public Endpoints

GET /cards/

* Description: Retrieves a list of all knowledge cards.

GET /cards/{card_id}

* Description: Retrieves a single card by its ID.