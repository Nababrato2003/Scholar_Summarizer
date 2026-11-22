import os
import sys

# Ensure root directory is accessible for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app


class VercelPathMiddleware:
    """
    WSGI Middleware for Vercel Serverless Functions.
    Strips internal Vercel function prefixes while preserving
    all application route paths (/auth/status, /analyze, etc.).
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        for prefix in ["/api/index.py", "/api/index", "/api", "/index.py", "/index"]:
            if path == prefix:
                path = "/"
                break
            elif path.startswith(prefix + "/"):
                path = path[len(prefix):]
                break

        environ["PATH_INFO"] = path if path else "/"
        return self.wsgi_app(environ, start_response)


app.wsgi_app = VercelPathMiddleware(app.wsgi_app)
