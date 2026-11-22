import os
import sys

# Ensure root directory is accessible for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app


class VercelPathMiddleware:
    """
    WSGI Middleware for Vercel Serverless Functions.
    Resolves the original request path from Vercel edge proxy headers
    and normalizes all Vercel function rewrite prefixes.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # 1. Check all possible Vercel forwarding headers
        path = (
            environ.get("HTTP_X_MATCHED_PATH") or 
            environ.get("HTTP_X_FORWARDED_PATH") or 
            environ.get("HTTP_X_ORIGINAL_URI") or
            environ.get("PATH_INFO", "")
        )
        
        # 2. Normalize and strip internal Vercel function prefixes
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
