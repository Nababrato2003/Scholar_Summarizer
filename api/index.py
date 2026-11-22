import os
import sys
from urllib.parse import parse_qs

# Ensure root directory is accessible for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app


class VercelPathMiddleware:
    """
    WSGI Middleware for Vercel Serverless Functions.
    Accurately restores original requested paths from Vercel's regex capture ($1).
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        qs = parse_qs(environ.get("QUERY_STRING", ""))
        custom_path = qs.get("__path", [None])[0]
        if custom_path is not None:
            environ["PATH_INFO"] = "/" + custom_path.lstrip("/")
        return self.wsgi_app(environ, start_response)


app.wsgi_app = VercelPathMiddleware(app.wsgi_app)
