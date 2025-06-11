# Main entry point for the FastAPI application.
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI

app = FastAPI()

# Mount the static directory for serving profile photos and other static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Import and include API routers
from app.api.v1 import auth, profile, users
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(users.router)
