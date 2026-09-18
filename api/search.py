import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from flask import Flask
from app import search

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
@app.route("/api/search", methods=["GET", "POST"])
@app.route("/search", methods=["GET", "POST"])
def handle_search():
    return search()
