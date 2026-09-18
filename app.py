import asyncio
import json
import queue
import threading
import uuid

from flask import Flask, Response, jsonify, render_template, request

from osint.engine import detect_input_type, get_sources_for, run_lookup_stream

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = (
    os.path.join(BASE_DIR, "public", "static")
    if os.path.isdir(os.path.join(BASE_DIR, "public", "static"))
    else os.path.join(BASE_DIR, "static")
)

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=STATIC_DIR,
    static_url_path="/static",
)
JOBS: dict[str, queue.Queue] = {}


@app.route("/")
@app.route("/index")
@app.route("/index.html")
@app.route("/api/index")
@app.route("/api/index.py")
def home():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def search():
    data = request.get_json(force=True) or {}
    target = (data.get("target") or "").strip()
    requested = data.get("type") or None
    if not target:
        return jsonify({"error": "target required"}), 400

    detected = requested if requested and requested != "auto" else detect_input_type(target)
    sources = get_sources_for(detected)

    job_id = uuid.uuid4().hex
    q: queue.Queue = queue.Queue()
    JOBS[job_id] = q

    def runner():
        async def on_result(r):
            q.put(("result", r.to_dict()))

        try:
            asyncio.run(run_lookup_stream(target, on_result, input_type=detected))
        except Exception as e:
            q.put(("error", {"message": str(e)}))
        finally:
            q.put(("done", None))

    threading.Thread(target=runner, daemon=True).start()

    return jsonify(
        {
            "job_id": job_id,
            "target": target,
            "input_type": detected,
            "sources": [
                {"name": s.name, "description": s.description} for s in sources
            ],
        }
    )


@app.route("/api/stream/<job_id>")
def stream(job_id):
    q = JOBS.get(job_id)
    if not q:
        return jsonify({"error": "unknown job"}), 404

    def gen():
        while True:
            try:
                event, payload = q.get(timeout=30)
            except queue.Empty:
                yield "event: ping\ndata: {}\n\n"
                continue
            if event == "done":
                yield "event: done\ndata: {}\n\n"
                JOBS.pop(job_id, None)
                break
            yield f"event: {event}\ndata: {json.dumps(payload)}\n\n"

    return Response(
        gen(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
