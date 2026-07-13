# Identity Reconciliation Service

This is the backend web service for Identity Reconciliation (Task 1). It uses Python, FastAPI, SQLAlchemy, and SQLite to link multiple purchases by a single person using varying contact information.

## Technology Stack
*   **Python 3.11+**
*   **FastAPI**: High-performance API framework.
*   **SQLAlchemy**: Object-Relational Mapping (ORM) for secure database interactions.
*   **SQLite**: Lightweight, zero-configuration local database.
*   **Pytest**: For unit testing.

## Prerequisites
*   Python 3 installed.

## Setup & Execution

### 1. Clone the Repository
```bash
git clone https://github.com/Nidhi200501/identity-reconciliation-service.git
cd identity-reconciliation-service
```

### 2. Install Dependencies
Create a virtual environment and install the required Python packages:
```bash
# Create virtual environment
python -m venv venv

# Activate it (Windows)
.\venv\Scripts\activate
# OR (macOS/Linux)
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Run the API Server
Start the FastAPI application using Uvicorn:
```bash
uvicorn main:app --reload
```
The API will be available at `http://127.0.0.1:8000`. 
*(Note: A local `identity.db` file will automatically be created to store your data).*

### 3. Interactive Testing (Swagger UI)
FastAPI automatically generates an interactive documentation page. Navigate to `http://127.0.0.1:8000/docs` in your browser to test the `/identify` endpoint directly without needing Postman.

**How to test using the UI:**
1. Click on the green **`POST /identify`** bar to expand it.
2. Click the **"Try it out"** button on the right side.
3. In the **"Request body"** text box, delete the default text and paste a test case:
   ```json
   {
     "email": "doc@gmail.com",
     "phoneNumber": "1111"
   }
   ```
4. Click the large blue **"Execute"** button.
5. Scroll down to the **"Server response"** section to see the JSON output! You can repeatedly change the email or phone number in the box and hit "Execute" to watch the system dynamically link new information and merge primary contacts.

## Running Tests
To verify the core reconciliation logic (including edge cases like merging two primary contacts), run the test suite using pytest:
```bash
pytest test_main.py -v
```
