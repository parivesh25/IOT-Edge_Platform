"""Flask routes and the MQTT listener. Run one process so live state is shared."""
import csv
import io
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
from urllib.parse import urlsplit

from flask import Flask, Response, abort, jsonify, render_template, request
import paho.mqtt.client as mqtt

from common import MessageProblem, valid_name
from dashboard.benchmark import Benchmarks
from dashboard.sketches import sketch
from dashboard.store import Store
from rules import read_rules, rules_path, for_project, save_rule


def csv_response(rows, fields, filename):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def create_app(store=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 8192
    store = store or Store(os.getenv("DATABASE_PATH", "data/readings.db"))
    app.extensions["store"] = store
    benchmarks = Benchmarks(store, os.getenv("BROKER_HOST", "localhost"), int(os.getenv("BROKER_PORT", "1883")))
    slots = threading.BoundedSemaphore(8)
    rule_lock = threading.Lock()

    @app.get('/api/projects/<name>/rules')
    def get_rules(name):
        if not valid_name(name) or store.project(name) is None:
            abort(404)
        return jsonify(rules=for_project(name, read_rules(rules_path())))

    @app.post('/api/projects/<name>/rules')
    def update_rules(name):
        if not valid_name(name) or store.project(name) is None:
            abort(404)
        body = request.get_json()
        if not isinstance(body, dict):
            raise ValueError('Send sensor, direction and limit fields.')
        with rule_lock:
            save_rule(name, body.get('sensor'), body.get('direction'), body.get('limit'))
        return jsonify(status='saved')

    @app.get('/lab')
    def lab_page():
        return render_template('index.html', page='home', project='')

    @app.before_request
    def same_origin_writes():
        # No logins in this lab version. Still reject browser cross-site writes.
        if request.method == "POST":
            origin = request.headers.get("Origin")
            if origin and urlsplit(origin).netloc != request.host:
                abort(403)
            if not request.is_json:
                abort(415)

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(ValueError)
    def bad_input(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(sqlite3.Error)
    def storage_error(error):
        return jsonify(error="Local storage is unavailable or full. Ask the lab maintainer to check the data volume."), 503

    @app.get("/")
    def home():
        return render_template("index.html", page="home", project="")

    @app.get("/projects/<name>")
    def project_page(name):
        if not valid_name(name) or store.project(name) is None:
            abort(404)
        return render_template("index.html", page="project", project=name)

    @app.get("/new")
    def new_page():
        return render_template("index.html", page="new", project="")

    @app.get("/benchmark")
    def benchmark_page():
        return render_template("index.html", page="benchmark", project="")

    @app.get("/api/overview")
    def overview():
        return jsonify(store.overview())

    @app.get("/api/config")
    def config():
        return jsonify(lan_ip=os.getenv("LAN_IP", ""), cloud_broker=os.getenv("CLOUD_BROKER", "test.mosquitto.org"))

    @app.get("/api/projects/<name>")
    def project_data(name):
        detail = store.project_detail(name) if valid_name(name) else None
        if detail is None:
            abort(404)
        return jsonify(detail)

    @app.post("/api/projects")
    def create_project():
        body = request.get_json()
        if not isinstance(body, dict):
            raise ValueError("Send project, device, sensor and board fields.")
        try:
            project = store.create_project(body.get("project"), body.get("device"), body.get("sensor"), body.get("board"))
        except MessageProblem as error:
            raise ValueError(str(error)) from None
        return jsonify(project=project, sketch=sketch(project)), 201

    @app.get("/api/projects/<name>/sketch")
    def generated_sketch(name):
        project = store.project(name) if valid_name(name) else None
        if project is None or project["started"] is None:
            abort(404)
        return jsonify(project=project, sketch=sketch(project))

    @app.get("/api/projects/<name>/readings.csv")
    def readings_csv(name):
        if not valid_name(name):
            abort(404)
        rows = store.rows("SELECT * FROM readings WHERE project=? ORDER BY id", (name,))
        return csv_response(rows, ["project", "device", "sensor", "value", "ts", "received", "simulated"], name + "-readings.csv")

    @app.get("/api/metrics.csv")
    def metrics_csv():
        return csv_response(store.projects(), ["name", "started", "first_data", "first_data_seconds", "devices", "last_seen"], "first-data.csv")

    @app.get("/api/benchmarks")
    def benchmark_history():
        return jsonify(runs=store.benchmarks())

    @app.post("/api/benchmarks")
    def run_benchmark():
        body = request.get_json()
        if not isinstance(body, dict):
            raise ValueError("Send an optional cloud_host field.")
        return jsonify(id=benchmarks.start(body.get("cloud_host", os.getenv("CLOUD_BROKER", "test.mosquitto.org")))), 202

    @app.get("/api/benchmarks.csv")
    def benchmarks_csv():
        rows = []
        for run in store.benchmarks():
            for location, result in (run["result"] or {}).items():
                rows.append(dict(result, id=run["id"], started=run["started"], cloud_host=run["cloud_host"], location=location))
        return csv_response(rows, ["id", "started", "cloud_host", "location", "status", "samples", "lost", "mean", "min", "max", "stddev"], "benchmarks.csv")

    @app.get("/events")
    def events():
        if not slots.acquire(blocking=False):
            return jsonify(error="Eight live viewers are already connected. This page will use polling."), 503

        def stream():
            last = None
            try:
                while True:
                    if store.version != last:
                        last = store.version
                        yield "event: update\ndata: " + json.dumps({"version": last}) + "\n\n"
                    else:
                        yield ": heartbeat\n\n"
                    time.sleep(1)
            finally:
                slots.release()
        return Response(stream(), mimetype="text/event-stream", headers={"X-Accel-Buffering": "no"})

    @app.get("/healthz")
    def health():
        store.rows("SELECT 1")
        return jsonify(status="ok" if store.connected else "waiting for broker"), 200 if store.connected else 503

    return app


def start_listener(store):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="lab-dashboard")

    def on_connect(client, userdata, flags, reason, properties):
        store.connected = not reason.is_failure
        store.version += 1
        if store.connected:
            # lab/# also receives malformed topic shapes for the Problems panel.
            client.subscribe([("lab/#", 0), ("$SYS/broker/log/#", 0)])

    def on_disconnect(client, userdata, flags, reason, properties):
        store.connected = False
        store.version += 1

    def on_message(client, userdata, message):
        try:
            store.ingest(message.topic, message.payload, retained=message.retain)
        except (sqlite3.Error, ValueError, OverflowError):
            # Keep MQTT alive on disk/full or malformed inputs, without logging payloads.
            store.connected = False

    client.on_connect, client.on_disconnect, client.on_message = on_connect, on_disconnect, on_message
    client.reconnect_delay_set(1, 10)
    client.connect_async(os.getenv("BROKER_HOST", "localhost"), int(os.getenv("BROKER_PORT", "1883")))
    client.loop_start()

    def cleanup():
        while True:
            time.sleep(60)
            try:
                store.prune()
            except sqlite3.Error:
                store.connected = False
    threading.Thread(target=cleanup, daemon=True).start()
    return client


def main():
    from waitress import serve
    app = create_app()
    client = start_listener(app.extensions["store"])
    try:
        serve(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")), threads=16, channel_timeout=30)
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
