# Book Bridge Backend Guide

## 1. What this backend does

Book Bridge is a digital library system for students. This FastAPI backend provides APIs for user accounts, books, borrowing and returning books, reservation queues, reviews, and ratings. A React frontend can call these APIs over HTTP and display the returned JSON data.

The server also creates any missing database tables when it starts. This is convenient for this college project. For a larger production application, database migrations would be a better next step.

## 2. Technology stack

| Technology | Why it is used |
| --- | --- |
| Python | Backend programming language |
| FastAPI | Defines API endpoints and automatic Swagger documentation |
| SQLAlchemy | Maps Python models to PostgreSQL tables |
| PostgreSQL | Stores users, books, loans, reservations, and reviews |
| Pydantic | Validates incoming JSON and formats responses |
| bcrypt | Hashes passwords before they are stored |
| python-jose | Creates and validates JWT login tokens |

## 3. Important folders

```text
Backend/
├── app/
│   ├── main.py          # Creates FastAPI, CORS, tables, and registers routers
│   ├── config.py        # Reads safe configuration values from .env
│   ├── database.py      # SQLAlchemy engine, base class, and DB session helper
│   ├── dependencies.py  # Current-user and role-checking dependencies
│   ├── models/          # SQLAlchemy database table definitions
│   ├── schemas/         # Pydantic request and response JSON shapes
│   ├── routers/         # API endpoints grouped by feature
│   └── services/        # Reusable authentication helpers
├── requirements.txt     # Python packages to install
├── .env.example         # Safe configuration template
└── BACKEND_GUIDE.md     # This guide
```

## 4. Install and configure the project

### Create or activate a virtual environment

From the `Backend` folder in PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell does not allow activation, run commands through the virtual environment directly instead:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Configure `.env`

Copy `.env.example` to `.env`, then replace the placeholders with your own PostgreSQL connection details and a long random JWT secret. `.env` is already ignored by Git and must stay private.

```powershell
Copy-Item .env.example .env
```

These are the settings:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection URL used by SQLAlchemy |
| `JWT_SECRET_KEY` | Private key used to sign login tokens |
| `JWT_EXPIRY_MINUTES` | Login-token lifetime; defaults to 30 minutes |
| `CORS_ORIGINS` | Comma-separated React/browser origins allowed to call the API |

Example format only—do not put real passwords or secrets in documentation or Git:

```dotenv
DATABASE_URL=postgresql+psycopg2://YOUR_USER:YOUR_PASSWORD@localhost:5432/book_bridge
JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_EXPIRY_MINUTES=30
```

## 5. Start PostgreSQL and the API

1. Start the PostgreSQL service. On Windows this is usually done through the **Services** app or pgAdmin. The exact service name depends on the installed PostgreSQL version.
2. Create the database named in `DATABASE_URL` if it does not already exist. For example, in `psql`:

   ```sql
   CREATE DATABASE book_bridge;
   ```

3. From the `Backend` folder, start FastAPI:

   ```powershell
   .\venv\Scripts\python.exe -m uvicorn app.main:app --reload
   ```

4. The API will normally be available at `http://127.0.0.1:8000`.

Check that it is running by opening `http://127.0.0.1:8000/health`. A successful response looks like:

```json
{"status":"healthy","version":"0.1.0"}
```

## 6. Swagger API documentation

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) while the server is running. Swagger lists every endpoint, its request body, response format, and expected status codes.

For protected endpoints:

1. Call `POST /auth/login` with an email and password.
2. Copy the returned `access_token` value.
3. Click **Authorize** in Swagger and paste the token value in the BearerAuth dialog.
4. Swagger will send `Authorization: Bearer <token>` for protected requests.

## 7. Authentication and roles

`POST /auth/register` creates a new account with the `student` role. Passwords are hashed with bcrypt; the plain password is never stored or returned.

`POST /auth/login` verifies the password and returns a signed JWT access token. Send that token on protected requests:

```http
Authorization: Bearer <access_token>
```

| Role | Main permissions |
| --- | --- |
| `student` | Borrow, return own loans, reserve unavailable books, and write/delete own reviews |
| `librarian` | Student permissions plus create, update, delete books; view all loans and reservation queues; moderate returns, reservations, and reviews |
| `admin` | Same elevated permissions as librarian in the current project |

The public registration endpoint intentionally does not let someone choose an elevated role. Set up the initial librarian/admin through a trusted project/database-administration process, not through public self-registration.

## 8. Main API endpoints

All paths below are relative to `http://127.0.0.1:8000` during local development.

| Method | Path | Purpose | Authentication |
| --- | --- | --- | --- |
| `POST` | `/auth/register` | Create a student account | Public |
| `POST` | `/auth/login` | Get a JWT token | Public |
| `GET` | `/auth/me` | Get the logged-in user's profile | Required |
| `GET` | `/books/` | List books | Public |
| `GET` | `/books/{book_id}` | Get one book | Public |
| `GET` | `/books/search/?query=text` | Search title, author, or category | Public |
| `POST` | `/books/` | Add a book | Librarian/admin |
| `PUT` | `/books/{book_id}` | Update a book | Librarian/admin |
| `DELETE` | `/books/{book_id}` | Delete a book | Librarian/admin |
| `POST` | `/borrows/` | Borrow a book | Required |
| `POST` | `/borrows/{borrow_id}/return` | Return a book | Borrower or librarian/admin |
| `GET` | `/borrows/my` | View the current user's borrowing history | Required |
| `GET` | `/borrows/` | View all borrow records | Librarian/admin |
| `POST` | `/reservations/` | Reserve an unavailable book | Required |
| `GET` | `/reservations/my` | View the current user's reservations | Required |
| `DELETE` | `/reservations/{reservation_id}` | Cancel a pending reservation | Owner or librarian/admin |
| `GET` | `/reservations/book/{book_id}` | View a book's queue | Librarian/admin |
| `POST` | `/reviews/` | Create a 1–5 rating and optional comment | Required |
| `GET` | `/reviews/book/{book_id}` | List a book's reviews | Public |
| `GET` | `/reviews/book/{book_id}/rating` | Get average rating and review count | Public |
| `DELETE` | `/reviews/{review_id}` | Delete a review | Owner or librarian/admin |

Useful HTTP status codes:

| Code | Meaning in this API |
| --- | --- |
| `200` | Successful read, update, return, or login |
| `201` | A user, book, borrow, reservation, or review was created |
| `204` | A delete/cancel operation succeeded and returns no body |
| `400` | The request conflicts with a business rule, such as borrowing twice |
| `401` | Login token is missing, invalid, or expired |
| `403` | The account lacks the required role or ownership |
| `404` | Requested user-facing resource does not exist |
| `409` | A duplicate ISBN was submitted |
| `422` | JSON is missing a required value or fails validation |

## 9. Database models and relationships

```text
User (users) ──< BorrowRecord (borrow_records) >── Book (books)
     │                                                │
     ├────────< Reservation (reservations) >──────────┤
     │                                                │
     └────────< Review (reviews) >────────────────────┘
```

| Model | Stores |
| --- | --- |
| `User` | Name, email, bcrypt password hash, role, creation time |
| `Book` | Book details plus total and currently available copies |
| `BorrowRecord` | Who borrowed which book, due date, return date, and status |
| `Reservation` | A student's place in a book's waiting queue and its status |
| `Review` | One user's rating (1–5) and optional comment for one book |

Foreign keys keep each borrow, reservation, and review connected to both its user and book. Response schemas include the related user or book where the frontend needs it.

## 10. Borrow and return logic

When a logged-in user borrows a book, the backend checks that:

1. The book exists.
2. A copy is available, unless a copy has already been held for that user's fulfilled reservation.
3. The user does not already have an active borrow of that book.

It then creates a borrow record, sets the due date to 14 days later, and reduces `available_copies` by one. On return, the record becomes `returned` and gets a `returned_at` time.

If nobody is waiting, return increases `available_copies` by one. If people are waiting, the returned copy is held for the oldest pending reservation instead, so it does not become generally available first.

## 11. Reservation logic

A reservation can only be created when `available_copies` is zero. A user cannot create another active reservation for the same book.

Reservations use these states:

| Status | Meaning |
| --- | --- |
| `pending` | The user is waiting in the first-come, first-served queue |
| `fulfilled` | A returned copy is held for that user; they can now borrow it |
| `cancelled` | A pending reservation was cancelled |

When the owner of a fulfilled reservation borrows the held copy, the queue record is removed because it has been claimed. The next time that copy is returned, the next pending reservation is fulfilled; if the queue is empty, the copy becomes available to everyone.

## 12. Reviews and ratings

An authenticated user can submit one review per book. A rating must be an integer from 1 to 5; the comment is optional. The API prevents duplicate reviews by the same user for the same book.

`GET /reviews/book/{book_id}` returns the reviews, including reviewer details. `GET /reviews/book/{book_id}/rating` returns the average rating and total review count.

The current implemented business rule requires authentication, a real book, a 1–5 rating, and no duplicate review. It does **not** currently check that the user has completed a borrow before reviewing; add that rule later only if your team decides it is required.

## 13. React frontend integration and CORS

### What CORS means

CORS stands for **Cross-Origin Resource Sharing**. In a browser, an origin is the combination of protocol, host, and port. For example, `http://localhost:5173` and `http://127.0.0.1:8000` are different origins.

Browsers normally block JavaScript on one origin from reading responses from another origin. This protects users from untrusted websites silently calling an API with their browser session. React therefore needs the backend to explicitly permit its development URL before browser `fetch` or Axios calls can read the API response.

`app/main.py` uses FastAPI's `CORSMiddleware`. By default it allows only these local React origins:

```text
http://localhost:3000
http://127.0.0.1:3000
http://localhost:5173
http://127.0.0.1:5173
```

It allows the needed HTTP methods and `Authorization`/`Content-Type` headers, but it does not use an insecure `*` origin and does not enable cross-origin cookies. For deployment, set `CORS_ORIGINS` in `.env` to the exact frontend URL or URLs, for example:

```dotenv
CORS_ORIGINS=https://book-bridge.example.edu
```

### Configure the frontend API base URL

For a Vite React project, create a frontend `.env` file:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Use it in frontend code:

```javascript
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

const response = await fetch(`${apiBaseUrl}/books/`);
const books = await response.json();
```

For protected endpoints, add the token:

```javascript
const response = await fetch(`${apiBaseUrl}/borrows/`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${accessToken}`,
  },
  body: JSON.stringify({ book_id: bookId }),
});
```

If the frontend uses Create React App instead of Vite, use the environment-variable name `REACT_APP_API_BASE_URL` instead.

## 14. Recent verification

The backend was tested against the live local PostgreSQL database and FastAPI server. The server started successfully, all five expected tables were present, `/docs` and `/openapi.json` returned successfully, allowed CORS preflight requests succeeded, and an untrusted origin was rejected.

A complete temporary end-to-end flow passed: registration, JWT login, librarian-authorized book creation, search, borrow/return quantity changes, reservation of an unavailable book, reviews, ratings, and reservation fulfillment. Temporary test accounts, books, and related records were removed after the tests.

## 15. Common problems

| Problem | What to check |
| --- | --- |
| Server fails on startup | Confirm `.env` exists, dependencies are installed, and PostgreSQL is running |
| Database connection error | Recheck `DATABASE_URL`, PostgreSQL host/port, database name, and credentials |
| `401 Could not validate credentials` | Log in again and send `Authorization: Bearer <token>`; JWTs expire after the configured time |
| Browser reports a CORS error | Ensure the frontend URL exactly appears in `CORS_ORIGINS`, then restart the API |
| React cannot reach the server | Check that its API base URL uses the correct host and port and that FastAPI is running |
