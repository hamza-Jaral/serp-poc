from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import serp
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

app = FastAPI(
    title="SERP POC",
    description="FastAPI project with SQLite database",
    version="1.0.0",
    docs_url="/",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the SERP API key from the environment variable
SERP_API_KEY = os.getenv("SERP_API_KEY")


app.include_router(serp.router, prefix="/api/v1")
