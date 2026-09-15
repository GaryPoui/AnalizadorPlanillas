"""Passenger entry point for hosting the FastAPI application on cPanel."""

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(API_DIR))

from a2wsgi import ASGIMiddleware
from main import app

application = ASGIMiddleware(app)
