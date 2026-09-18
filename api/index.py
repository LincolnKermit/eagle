import os
import sys
from urllib.parse import parse_qs, urlencode

# Ensure project root is in sys.path for importing app and osint modules
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app


class VercelPathFix:
    """WSGI middleware to restore original request path from Vercel rewrite parameter or headers."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        qs = environ.get("QUERY_STRING", "")
        params = parse_qs(qs, keep_blank_values=True)

        if "__path__" in params:
            raw_path = params.pop("__path__")[0]
            while raw_path.startswith("//"):
                raw_path = raw_path[1:]
            if not raw_path.startswith("/"):
                raw_path = "/" + raw_path
            environ["PATH_INFO"] = raw_path
            environ["QUERY_STRING"] = urlencode(params, doseq=True)
        else:
            # Check edge headers
            forwarded = (
                environ.get("HTTP_X_VERCEL_FORWARDED_PATH")
                or environ.get("HTTP_X_FORWARDED_URI")
                or environ.get("HTTP_X_MATCHED_PATH")
            )
            if forwarded:
                environ["PATH_INFO"] = forwarded.split("?")[0]
            elif environ.get("PATH_INFO") in ("/api/index", "/api/index.py"):
                environ["PATH_INFO"] = "/"

        return self.wsgi_app(environ, start_response)


# Wrap Flask application with the path fix middleware
app.wsgi_app = VercelPathFix(app.wsgi_app)
