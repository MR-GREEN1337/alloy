# Alloy - The Cultural Due Diligence Platform

![alt text](https://img.shields.io/badge/Qloo_Hackathon-2025-blue.svg) ![alt text](https://img.shields.io/badge/License-MIT-yellow.svg)

Alloy is a financial-grade intelligence platform for M&A, VC, and corporate strategy firms. It de-risks multi-billion dollar acquisitions by replacing executive "gut feeling" with a data-driven **Cultural Compatibility Score**, powered by Qloo's Taste AI™. This project was built for the 2025 Qloo LLM Hackathon.

<br/>

![Application Screenshot](assets/alloy-screenshot.png)

<br/>

## 🌟 Core Features

*   **Data-Driven Compatibility Score**: Go beyond financials with a quantifiable metric of cultural alignment, calculated from millions of audience taste data points.
*   **AI-Powered Strategic Analysis**: An advanced ReAct agent using Google's Gemini orchestrates data gathering, synthesizes findings, and generates deep qualitative insights.
*   **Culture Clash Identification**: Proactively flags areas of stark cultural divergence and potential integration risks before they impact a deal.
*   **Untapped Growth & Synergy Discovery**: Pinpoints shared affinities and latent audience desires to reveal strategic opportunities for post-acquisition value creation.
*   **Interactive Reporting & AI Chat**: A rich, multi-module dashboard visualizes complex intelligence and allows for interactive follow-up questions with a report-aware AI analyst.
*   **Live Web Grounding**: Enriches analysis with real-time corporate profiles, news, and market data using the Tavily Search API.
*   **Secure & Professional Grade**: Features robust JWT-based authentication (including Google OAuth), isolated user data, and downloadable, executive-ready PDF reports.

## 🛠️ Tech Stack

| Area          | Technology                                                                                                  |
|---------------|-------------------------------------------------------------------------------------------------------------|
| **Backend**   | FastAPI, SQLModel (SQLAlchemy + Pydantic), PostgreSQL (Async), JWT, Passlib                                 |
| **Frontend**  | Next.js (App Router), React, TypeScript, Tailwind CSS, Shadcn UI, SWR, Framer Motion                        |
| **AI & Data** | Qloo Taste AI™, Google Gemini, Tavily Search API                                                            |
| **Database**  | PostgreSQL (managed with Docker Compose for local development)                                              |
| **Testing**   | Pytest with `pytest-asyncio` for asynchronous testing                                                       |
| **DevOps**    | Docker, Docker Compose                                                                                      |

## 🏗️ System Architecture

Alloy operates on a robust, decoupled two-part architecture designed for scalability and maintainability.

*   **FastAPI Backend (The Intelligence Engine)**: The core brain of the platform. It handles user authentication, orchestrates calls to external APIs (Qloo, Gemini, Tavily), runs the ReAct agent for analysis, and persists all data to the PostgreSQL database.
*   **Next.js Frontend (The Executive Dashboard)**: The user-facing command center. It provides a clean, professional interface for creating and viewing reports. It communicates with the backend via a REST API and presents complex analysis in an intuitive, interactive format.

[![](https://mermaid.ink/img/pako:eNp1VE2PmzAQ_SuWe-iFTUuAhBCpUiAfbbXdZhe2lRr24MCE0IKNbLNNivLfa0Na0aTrOWDPvHkevRnc4ISlgD2ccVLtUTSPKVJL1NvOEeNHAfy1QD5nP9Uuxh1Ar9lGx57Qzc075Dd3cJCD7wItOaMSaHqadki1jekVa1CwOn0TAn_-l9NXbOh9FK1DNFt_QAEpCtFeEDRLIqT2-ST50ePXK9BZH79GaFbLfQe_jIb3t21gvlkzITMO2jH3ny5x-gaNW2zuC8b08UXIcrNiLCsAraDMaf4ibrWJyHNeHFEIhCf7Puf_xVkcJHBKCqT1yRMQfYUWU7ScotU1QSdC-PkOPYCoGBXQdeaMbJV9UHjgQn0rxiV67AqcTbGBS-AlyVM1Co1OiLHcQwkx9tR2S4TaGT3_F8Jzsi10aR5quhtiXPG8JPwYsILxLvOVSbSdk3uYSI1LH7fb7XqgIqfQj5KJth5AQMJoenHX0NXWQykZZX5Z0E7bdUE-40qaPtJ1-1yQZnBLtlDo-cs4q5XyZ0bT7Bp0iulJKUlqycIjTbAneQ0GVthsj70dKYQ61VVKJMxzorpd_vVWhH5jrPyToo7Ya_ABe5YzcIdjy3Ld4WjsTEamY-CjctsDyzVH9nBk2WPHHNsnA_9qCd4OXGtkj0eW6zgTyzZty1A_t27suZp2BAJVv8SeqYKQ5pLxT90z0L4Gp99TxzAw?type=png)](https://mermaid.live/edit#pako:eNp1VE2PmzAQ_SuWe-iFTUuAhBCpUiAfbbXdZhe2lRr24MCE0IKNbLNNivLfa0Na0aTrOWDPvHkevRnc4ISlgD2ccVLtUTSPKVJL1NvOEeNHAfy1QD5nP9Uuxh1Ar9lGx57Qzc075Dd3cJCD7wItOaMSaHqadki1jekVa1CwOn0TAn_-l9NXbOh9FK1DNFt_QAEpCtFeEDRLIqT2-ST50ePXK9BZH79GaFbLfQe_jIb3t21gvlkzITMO2jH3ny5x-gaNW2zuC8b08UXIcrNiLCsAraDMaf4ibrWJyHNeHFEIhCf7Puf_xVkcJHBKCqT1yRMQfYUWU7ScotU1QSdC-PkOPYCoGBXQdeaMbJV9UHjgQn0rxiV67AqcTbGBS-AlyVM1Co1OiLHcQwkx9tR2S4TaGT3_F8Jzsi10aR5quhtiXPG8JPwYsILxLvOVSbSdk3uYSI1LH7fb7XqgIqfQj5KJth5AQMJoenHX0NXWQykZZX5Z0E7bdUE-40qaPtJ1-1yQZnBLtlDo-cs4q5XyZ0bT7Bp0iulJKUlqycIjTbAneQ0GVthsj70dKYQ61VVKJMxzorpd_vVWhH5jrPyToo7Ya_ABe5YzcIdjy3Ld4WjsTEamY-CjctsDyzVH9nBk2WPHHNsnA_9qCd4OXGtkj0eW6zgTyzZty1A_t27suZp2BAJVv8SeqYKQ5pLxT90z0L4Gp99TxzAw)

## 🚀 Getting Started: Local Development

Follow these steps to set up and run the Alloy platform on your local machine.

### 1. Prerequisites
*   Git
*   Python 3.10+ & Pip
*   Node.js 18+ & npm/yarn/pnpm
*   Docker & Docker Compose

### 2. Initial Setup

First, clone the repository and set up the necessary environment files.

```bash
# 1. Clone the repository
git clone https://github.com/mr-green1337/alloy.git
cd alloy

# 2. Set up backend environment file
cp backend/.env.example backend/.env

# 3. Set up frontend environment file
cp web/.env.local.example web/.env.local
```

### 3. Configure Environment Variables

You now need to add your secret keys and credentials to the newly created `.env` and `.env.local` files.

#### **Backend (`backend/.env`)**
Open `backend/.env` and fill in your details. You can generate a `SECRET_KEY` using `openssl rand -hex 32` in your terminal.

```ini
# Environment
ENVIRONMENT="development"
DEBUG=True
FAIL_FAST=False

# Security & JWT - Generate a strong secret key!
SECRET_KEY="YOUR_SUPER_SECRET_KEY_HERE"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# AI & Data APIs
QLOO_API_KEY="YOUR_QLOO_API_KEY"
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
TAVILY_API_KEY="YOUR_TAVILY_API_KEY"
SCRAPER_API_KEY="" # Optional but recommended

# Google OAuth (Optional)
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""

# Database - These are pre-configured for the local Docker setup
POSTGRES_DATABASE_URL="postgresql+asyncpg://alloy_user:alloy_password@localhost:5432/alloy_db"
POSTGRES_SCHEMA="public"
POSTGRES_USE_SSL=False

# CORS & Frontend
CORS_ORIGINS=["http://localhost:3000"]
```

#### **Frontend (`web/.env.local`)**
This file tells your Next.js app where to find the backend API. For local development, this is typically `http://localhost:8000`.

```
NEXT_PUBLIC_API_URL=http://localhost:8000```

### 4. Run The Application

With configuration complete, you can launch the entire stack.

#### **Step 1: Start the Database**
In the root `alloy` directory, start the PostgreSQL database using Docker Compose.

```bash
docker-compose up -d
```

This will run a Postgres container in the background.

#### **Step 2: Start the Backend**
Open a **new terminal window**, navigate to the `backend` directory, create a virtual environment, and start the FastAPI server.

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate
# On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Run the development server
uvicorn src.main:app --reload
```
The backend is now running on `http://localhost:8000`.

#### **Step 3: Start the Frontend**
Open a **third terminal window**, navigate to the `web` directory, install dependencies, and start the Next.js development server.

```bash
cd web

# Install dependencies
npm install

# Run the development server
npm run dev
```
The frontend is now available at `http://localhost:3000`. You can open this URL in your browser to use the application.

### 5. Running Tests

To run the backend test suite, ensure your virtual environment is active in the `backend` directory, then run pytest:
```bash
# In the backend/ directory with venv active
pytest
```

## 🙏 Acknowledgments

*   **Qloo**: For providing the Taste AI™ API and hosting this fantastic hackathon.
*   **Tavily**: For their excellent and easy-to-use Search API.
*   **The open-source community**: For the incredible tools (FastAPI, Next.js, and many more) that made this project possible.