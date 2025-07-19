# automatic refresh
# Allow deep thought for agent
# Visualizing "Clashes": The "Culture Clashes" and "Untapped Growth" sections are currently presented in tables. A more visual representation (e.g., a Venn diagram, a force-directed graph, or distinct "word clouds" for each brand's unique tastes) could make these insights even more impactful at a glance.
# Let AI decide what query to use for web search

## Use sophisticated scientific equation to calculate score

Alloy - The Cultural Due Diligence Platform

![alt text](https://img.shields.io/badge/Qloo_Hackathon-2025-blue.svg)


![alt text](https://img.shields.io/badge/License-MIT-yellow.svg)

Alloy is a financial-grade intelligence platform for M&A, VC, and corporate strategy firms. It de-risks multi-billion dollar acquisitions by replacing executive "gut feeling" with a data-driven Cultural Compatibility Score, powered by Qloo's Taste AI™.

🌟 Key Features

Data-Driven Compatibility Score: A quantifiable metric of cultural alignment based on millions of taste data points.

Interactive Reporting: A rich, multi-module dashboard to visualize complex cultural intelligence.

AI-Powered Analysis: A ReAct agent using Google's Gemini to orchestrate data gathering and synthesize findings.

Culture Clash Identification: Proactively flags areas of cultural divergence and potential integration risks.

Untapped Growth Discovery: Pinpoints shared affinities to reveal strategic opportunities for post-acquisition synergy.

Live Web Grounding: Enriches analysis with real-time information using the Tavily Search API.

Secure & Private: Robust JWT-based authentication (including Google OAuth) and isolated user data.

PDF Report Downloads: Export comprehensive, professionally formatted reports for offline sharing.

AI Analyst Chat: Ask follow-up questions about your generated report for deeper insights.

📸 Application Screenshot

![alt text](assets/alloy-screenshot.png)

🛠️ Tech Stack
Area	Technology
Backend	FastAPI, SQLModel (SQLAlchemy + Pydantic), PostgreSQL, asyncpg, JWT, Passlib
Frontend	Next.js (App Router), React, TypeScript, Tailwind CSS, Shadcn UI, SWR, Framer Motion
AI & Data	Qloo Taste AI™, Google Gemini, Tavily Search API
Database	PostgreSQL (managed with Docker Compose for local development)
Testing	Pytest with pytest-asyncio
🏗️ System Architecture

Alloy operates on a robust, decoupled two-part architecture:

FastAPI Backend (The Intelligence Engine): This is the core brain of the platform. It handles user authentication, orchestrates calls to external APIs (Qloo, Gemini, Tavily), runs the ReAct agent for data processing, and persists all data to the PostgreSQL database.

Next.js Frontend (The Executive Dashboard): This is the user-facing command center. It provides a clean, professional interface for creating and viewing reports. It communicates with the backend via a REST API, handles all rendering, and presents the complex analysis in an intuitive, interactive format.

Generated mermaid
graph TD
    subgraph "User's Browser"
        A[User] --> B{Next.js Frontend};
    end

    subgraph "Cloud/Server"
        B -- HTTPS API Calls --> C{FastAPI Backend};
        C -- JWT Auth --> C;
        C -- SQL --> D[PostgreSQL DB];
        C -- API --> E[Qloo API];
        C -- API --> F[Google Gemini];
        C -- API --> G[Tavily Search API];
    end

    subgraph "External Services"
        E; F; G;
    end

    C -- JSON Response --> B;
    B -- Renders Report UI --> A;

🚀 Getting Started: Local Development

Follow these steps to set up and run the Alloy platform on your local machine.

1. Prerequisites

Git

Python 3.10+

Node.js 18+

Docker & Docker Compose

2. Clone the Repository
```bash
git clone https://github.com/mr-green1337/alloy.git
cd alloy
```
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END
3. Backend Setup

First, set up the FastAPI server.

Generated bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate
# On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Create the environment file from the example
cp .env.example .env
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

Now, open the newly created backend/.env file and fill in your API keys and database URL.

backend/.env:

Generated ini
# Environment
ENVIRONMENT="development" # "development" or "production"
DEBUG=True
FAIL_FAST=False

# Security & JWT - Generate a strong secret key!
# You can generate one with: openssl rand -hex 32
SECRET_KEY="YOUR_SUPER_SECRET_KEY_HERE"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# AI & Data APIs
QLOO_API_KEY="YOUR_QLOO_API_KEY"
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
TAVILY_API_KEY="YOUR_TAVILY_API_KEY"
SCRAPER_API_KEY="YOUR_SCRAPERAPI_KEY" # Optional but recommended for favicon fetching

# Google OAuth (Optional)
GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT_ID"
GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_CLIENT_SECRET"

# Database
POSTGRES_DATABASE_URL="postgresql+asyncpg://alloy_user:alloy_password@localhost:5432/alloy_db"
POSTGRES_SCHEMA="public"
POSTGRES_USE_SSL=False # Use False for local Docker setup

# CORS & Frontend
# Add your frontend URL here
CORS_ORIGINS=["http://localhost:3000"]
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Ini
IGNORE_WHEN_COPYING_END
4. Frontend Setup

Next, set up the Next.js web application.

Generated bash
# Navigate to the web directory
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END