import os
import sys

# Ensure project root is in sys.path for importing app and osint modules
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app


class VercelPathFix:
    """WSGI middleware to restore original request path from Vercel edge reverse proxy headers."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # Vercel supplies original client path in x-vercel-forwarded-path or x-forwarded-uri
        forwarded_path = (
            environ.get("HTTP_X_VERCEL_FORWARDED_PATH")
            or environ.get("HTTP_X_FORWARDED_URI")
            or environ.get("HTTP_X_MATCHED_PATH")
        )
        if forwarded_path:
            environ["PATH_INFO"] = forwarded_path.split("?")[0]
        elif environ.get("PATH_INFO") in ("/api/index", "/api/index.py"):
            environ["PATH_INFO"] = "/"
        return self.wsgi_app(environ, start_response)


# Wrap Flask application with the path fix middleware
app.wsgi_app = VercelPathFix(app.wsgi_app)
