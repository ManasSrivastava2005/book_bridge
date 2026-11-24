# 📚 Book Bridge



### Smart Digital Library Management Platform



Book Bridge is a full-stack digital library management platform designed to make library operations, book discovery, borrowing, learning resources and academic collaboration easier through a unified web application.



## ✨ Features



Based on the registered application modules:



\- \*\*Authentication:\*\* User registration, login and profile management.

\- \*\*Book Management:\*\* Book-related management and discovery APIs.

\- \*\*Borrowing \& Reservations:\*\* Borrowing records and reservation management.

\- \*\*Reviews \& Notifications:\*\* Book reviews and notification services.

\- \*\*Digital Resources:\*\* Digital learning resources, notes and question banks.

\- \*\*Reader:\*\* Reading-related functionality and reader state management.

\- \*\*Study Rooms:\*\* Study rooms, members and messaging.

\- \*\*Learning \& Academic Tools:\*\* Curriculum, quizzes, syllabus uploads, academic tasks and student exam modules.

\- \*\*Reading Activity:\*\* Reading sessions, daily reading records and activity tracking.

\- \*\*Contributions \& Gamification:\*\* Contributions, badges, XP transactions and leaderboard functionality.

\- \*\*AI \& Summarization:\*\* Book summarization services with local model support.

\- \*\*QR Scanner:\*\* QR-code scanning functionality.



\*The availability of individual features depends on the user's role and application configuration.\*



## 🛠️ Technology Stack



| Category | Technologies |

|---|---|

| Frontend | React 18, Vite 6, TypeScript |

| Styling | Tailwind CSS 3, PostCSS |

| Backend | Python 3.14, FastAPI |

| API Server | Uvicorn |

| Database | PostgreSQL 18 |

| ORM | SQLAlchemy |

| Authentication | JWT, bcrypt |

| Frontend Routing | React Router |

| HTTP Client | Axios |

| Machine Learning | PyTorch (CPU), Transformers |

| AI / Summarization | Google GenAI SDK, OpenAI SDK dependencies |

| Version Control | Git \& GitHub |



## 📂 Project Structure



```text

book\_bridge/

│

├── app/

│   ├── ml/

│   ├── models/

│   ├── routers/

│   ├── schemas/

│   ├── services/

│   ├── config.py

│   ├── database.py

│   ├── dependencies.py

│   └── main.py

│

├── frontend/

│   ├── public/

│   ├── scripts/

│   ├── src/

│   ├── package.json

│   └── vite.config.ts

│

├── uploads/

├── requirements.txt

├── requirements-ml.txt

├── requirements-dev.txt

├── .env.example

├── .gitignore

└── README.md

```



## ⚙️ Installation and Setup



### 1. Prerequisites



Install the following:



\- Python 3.14

\- Node.js and npm

\- PostgreSQL

\- Git



### 2. Clone the Repository



```bash

git clone https://github.com/ManasSrivastava2005/book\_bridge.git



cd book\_bridge

```



### 3. Backend Setup



Create a Python virtual environment:



```bash

py -3.14 -m venv .venv

```



Activate it on Windows:



```cmd

.venv\\Scripts\\activate

```



Upgrade pip:



```bash

python -m pip install --upgrade pip

```



Install backend dependencies:



```bash

python -m pip install -r requirements.txt

```



Install the QR-code dependency if it is not already included:



```bash

python -m pip install "qrcode\[pil]"

```



### 4. Database Configuration



Install and start PostgreSQL.



Create a database named:



```sql

CREATE DATABASE book\_bridge;

```



Copy the example environment file:



```cmd

copy .env.example .env

```



Open `.env` and configure your database connection:



```env

DATABASE\_URL=postgresql+psycopg2://postgres:YOUR\_PASSWORD@localhost:5432/book\_bridge

```



Replace `YOUR\_PASSWORD` with your PostgreSQL password.



Configure the other environment variables according to `.env.example`.



\*\*Important:\*\* Never commit your actual `.env` file or expose database credentials and secret keys.



The application registers its SQLAlchemy models and creates missing tables during startup.



### 5. Start the Backend



From the project root, with the virtual environment activated:



```bash

python -m uvicorn app.main:app --reload

```



The backend runs at:



```text

http://127.0.0.1:8000

```



### 6. Frontend Setup



Open another terminal:



```cmd

cd frontend

```



Install the locked frontend dependencies:



```bash

npm ci

```



Start the development server:



```bash

npm run dev

```



The frontend runs at:



```text

http://localhost:5173

```



## 🌐 API Documentation



FastAPI automatically provides interactive API documentation.



| Resource | URL |

|---|---|

| API Homepage | http://127.0.0.1:8000/ |

| Health Check | http://127.0.0.1:8000/health |

| Swagger UI | http://127.0.0.1:8000/docs |

| OpenAPI Schema | http://127.0.0.1:8000/openapi.json |



## 🔐 Environment Variables



The project uses a `.env` file for local configuration.



Important variables include:



| Variable | Purpose |

|---|---|

| `DATABASE\_URL` | PostgreSQL connection |

| `JWT\_SECRET\_KEY` | JWT signing secret |

| `JWT\_EXPIRY\_MINUTES` | Token expiry |

| `OPENAI\_API\_KEY` | Retained cloud API configuration |

| `GEMINI\_API\_KEY` | Retained cloud API configuration |

| `LOCAL\_SUMMARY\_MODEL\_NAME` | Local summarization model |

| `LOCAL\_SUMMARY\_THREADS` | Local summarization threads |

| `CORS\_ORIGINS` | Allowed frontend origins |



Refer to `.env.example` for the complete configuration.



## 🧠 Local AI Summarization



The project configuration specifies:



```env

LOCAL\_SUMMARY\_MODEL\_NAME=google/flan-t5-base

LOCAL\_SUMMARY\_THREADS=4

```



The local summarization configuration uses Hugging Face Transformers and CPU-based PyTorch.



The model may need to be downloaded the first time the summarization feature is used.



## 🧪 Development



Useful frontend commands:



```bash

npm run dev

npm run build

npm run preview

```



Useful backend command:



```bash

python -m uvicorn app.main:app --reload

```



## 🔒 Security Notes



\- Keep `.env` private.

\- Never upload API keys, passwords or JWT secrets to GitHub.

\- Use strong and unique credentials.

\- Configure CORS appropriately before production deployment.

\- Review authentication and authorization before exposing the application publicly.



## 👨‍💻 Developer



\*\*Manas Srivastava\*\*



B.Tech Computer Science and Engineering  

Cloud Computing \& Automation



GitHub: \[@ManasSrivastava2005](https://github.com/ManasSrivastava2005)



## 📌 Repository



\[Book Bridge – GitHub Repository](https://github.com/ManasSrivastava2005/book\_bridge)



\---



\*Built to make digital libraries smarter, learning more accessible, and academic collaboration easier.\* 🚀

