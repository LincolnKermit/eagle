import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from flask import Flask
from app import stream

app = Flask(__name__)


@app.route("/", methods=["GET"])
@app.route("/<job_id>", methods=["GET"])
@app.route("/api/stream", methods=["GET"])
@app.route("/api/stream/<job_id>", methods=["GET"])
@app.route("/stream", methods=["GET"])
@app.route("/stream/<job_id>", methods=["GET"])
def handle_stream(job_id=None):
    return stream(job_id)
