import os
import sys

# Ensure root directory is accessible for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app


class VercelPathMiddleware:
    """
    WSGI Middleware for Vercel Serverless Functions.
    Resolves the original request path from Vercel edge proxy headers
    (X-Matched-Path / X-Forwarded-Path) so Flask routes match accurately.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched_path = (
            environ.get("HTTP_X_MATCHED_PATH") or 
            environ.get("HTTP_X_FORWARDED_PATH") or 
            environ.get("HTTP_X_ORIGINAL_URI")
        )
        if matched_path:
            environ["PATH_INFO"] = matched_path
        elif environ.get("PATH_INFO", "").startswith("/api/index"):
            remainder = environ["PATH_INFO"][len("/api/index"):]
            environ["PATH_INFO"] = remainder if remainder else "/"

        return self.wsgi_app(environ, start_response)


app.wsgi_app = VercelPathMiddleware(app.wsgi_app)
