"""SQLite storage. One lock keeps the MQTT writer and web readers simple.

All SQL values use parameters, never string interpolation. Retention runs during
ingestion and once a minute while idle; deleted pages are reused by SQLite.
"""
from collections import defaultdict, deque
import json
from pathlib import Path
import re
import sqlite3
import threading
import time

from common import MessageProblem, RESERVED, number, parse_reading, valid_name, valid_sensor


class Store:
    def __init__(self, path, max_rows=100000, retention_seconds=86400):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.max_rows, self.retention_seconds = max_rows, retention_seconds
        self.version = 0
        self.connected = False
        self.last_any = None
        self.collisions = defaultdict(lambda: deque(maxlen=5))
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA busy_timeout=5000;
            PRAGMA max_page_count=131072;
            CREATE TABLE IF NOT EXISTS projects (
                name TEXT PRIMARY KEY, started REAL, first_data REAL, last_seen REAL,
                device TEXT, sensor TEXT, board TEXT
            );
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY, project TEXT, device TEXT, sensor TEXT,
                value REAL, ts REAL, received REAL, simulated INTEGER, retained INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS readings_series ON readings(project,device,sensor,received);
            CREATE INDEX IF NOT EXISTS readings_age ON readings(received);
            CREATE TABLE IF NOT EXISTS problems (
                id INTEGER PRIMARY KEY, project TEXT, topic TEXT, problem TEXT, fix TEXT, received REAL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY, project TEXT, topic TEXT, payload TEXT, kind TEXT, received REAL
            );
            CREATE INDEX IF NOT EXISTS messages_project ON messages(project,id);
            CREATE TABLE IF NOT EXISTS benchmarks (
                id TEXT PRIMARY KEY, started REAL, status TEXT, cloud_host TEXT, result TEXT
            );
        """)
        self.prune()

    def close(self):
        self.db.close()

    def rows(self, sql, args=()):
        with self.lock:
            return [dict(row) for row in self.db.execute(sql, args).fetchall()]

    def prune(self, now=None):
        now = time.time() if now is None else now
        with self.lock, self.db:
            self.db.execute("DELETE FROM readings WHERE received < ?", (now - self.retention_seconds,))
            self.db.execute("DELETE FROM readings WHERE id IN (SELECT id FROM readings ORDER BY id DESC LIMIT -1 OFFSET ?)", (self.max_rows,))
            self.db.execute("DELETE FROM problems WHERE id NOT IN (SELECT id FROM problems ORDER BY id DESC LIMIT 500)")
            self.db.execute("DELETE FROM messages WHERE id NOT IN (SELECT id FROM messages ORDER BY id DESC LIMIT 10000)")
            self.db.execute("DELETE FROM messages WHERE received < ?", (now - self.retention_seconds,))
            self.db.execute("DELETE FROM benchmarks WHERE id NOT IN (SELECT id FROM benchmarks ORDER BY started DESC LIMIT 100)")

    def _ensure_project(self, name):
        if self.db.execute("SELECT 1 FROM projects WHERE name=?", (name,)).fetchone():
            return
        if self.db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] >= 1000:
            raise MessageProblem("The lab has reached its 1000-project limit.", "Use an existing project or ask the lab maintainer to archive the database.")
        self.db.execute("INSERT INTO projects(name) VALUES (?)", (name,))

    def create_project(self, name, device, sensor, board):
        if not valid_name(name) or not valid_name(device) or not valid_sensor(sensor) or name in RESERVED:
            raise ValueError("Names need 1-48 lowercase letters, digits or hyphens; start with a letter/digit. alerts, summary and status are reserved.")
        if board not in ("esp32", "uno"):
            raise ValueError("Choose ESP32 over WiFi or Arduino Uno over USB serial.")
        with self.lock, self.db:
            self._ensure_project(name)
            # Reopening a wizard does not erase an already-recorded metric.
            self.db.execute("UPDATE projects SET started=?, device=?, sensor=?, board=? WHERE name=? AND started IS NULL",
                            (time.time(), device, sensor, board, name))
            self.version += 1
        return self.project(name)

    def problem(self, project, topic, problem, fix, now=None):
        with self.lock, self.db:
            self.db.execute("INSERT INTO problems(project,topic,problem,fix,received) VALUES (?,?,?,?,?)",
                            (project, topic[:240], problem, fix, time.time() if now is None else now))
            self.db.execute("DELETE FROM problems WHERE id NOT IN (SELECT id FROM problems ORDER BY id DESC LIMIT 500)")
            self.version += 1

    def _message(self, project, topic, data, kind, now):
        self.db.execute("INSERT INTO messages(project,topic,payload,kind,received) VALUES (?,?,?,?,?)",
                        (project, topic[:240], json.dumps(data), kind, now))

    def ingest(self, topic, payload, retained=False, now=None):
        now = time.time() if now is None else now
        if topic.startswith("$SYS/"):
            self.broker_notice(payload, now)
            return
        if not topic.startswith("lab/") and topic != "lab":
            return
        self.last_any = now
        parts = topic.split("/")
        project = parts[1] if len(parts) > 1 and valid_name(parts[1]) and parts[1] not in RESERVED else None
        if len(parts) > 1 and parts[1] in ("alerts", "summary"):
            self._event(topic, payload, now)
            return
        try:
            project, data = parse_reading(topic, payload)
            with self.lock, self.db:
                self._ensure_project(project)
                self.db.execute("INSERT INTO readings(project,device,sensor,value,ts,received,simulated,retained) VALUES (?,?,?,?,?,?,?,?)",
                                (project, data["device"], data["sensor"], float(data["value"]), float(data.get("ts", now)), now, int(data.get("simulated", False)), int(retained)))
                # Retained readings are historical; they must not mark a device online
                # or complete a new student's first-live-data measurement.
                if not retained:
                    self.db.execute("UPDATE projects SET last_seen=? WHERE name=?", (now, project))
                    self.db.execute("UPDATE projects SET first_data=? WHERE name=? AND started IS NOT NULL AND first_data IS NULL AND started<=?", (now, project, now))
                self._message(project, topic, dict(data, retained=retained), "reading", now)
                self.version += 1
                self.prune(now)
        except MessageProblem as error:
            self.problem(project, topic, str(error), error.fix, now)

    def _event(self, topic, payload, now):
        try:
            if len(payload) > 4096:
                raise ValueError()
            data = json.loads(payload)
            parts = topic.split("/")
            if (not isinstance(data, dict) or len(parts) != 4 or not valid_name(data.get("project"))
                    or data["project"] in RESERVED or data.get("device") != parts[2]
                    or data.get("sensor") != parts[3] or not valid_name(parts[2]) or not valid_sensor(parts[3])):
                raise ValueError()
            kind = parts[1]
            fields = ("value", "limit") if kind == "alerts" else ("avg", "min", "max", "count")
            if not all(number(data.get(key)) for key in fields):
                raise ValueError()
            if kind == "alerts" and data.get("direction") not in ("above", "below"):
                raise ValueError()
            if "ts" in data and (not number(data["ts"]) or data["ts"] < 0):
                raise ValueError()
            if "simulated" in data and type(data["simulated"]) is not bool:
                raise ValueError()
            allowed = ("project", "device", "sensor", "value", "ts", "simulated", "direction", "limit", "avg", "min", "max", "count")
            clean = {key: data[key] for key in allowed if key in data}
            # Reject non-contract types rather than storing arbitrary nested objects.
            if any(isinstance(value, (dict, list)) for value in clean.values()):
                raise ValueError()
            with self.lock, self.db:
                self._ensure_project(data["project"])
                self._message(data["project"], topic, clean, kind, now)
                self.version += 1
                self.prune(now)
        except (ValueError, UnicodeError, TypeError):
            self.problem(None, topic, "Invalid platform alert or summary.", "Publish readings under your project; reserved topics are written by the edge service.", now)

    def broker_notice(self, payload, now):
        # Only retain a validated client ID and counts, never the broker log text.
        text = payload.decode("utf-8", errors="replace")[:1000]
        # Mosquitto 2.0 and 2.1 use different wording for the same takeover.
        match = re.search(r"Client ([a-z0-9][a-z0-9-]{0,47}) (?:already connected|(?:\[[^\]]{1,100}\] )?disconnected: session taken over)", text)
        if not match:
            return
        device = match.group(1)
        if len(self.collisions) >= 1000 and device not in self.collisions:
            self.collisions.pop(next(iter(self.collisions)))
        recent = self.collisions[device]
        recent.append(now)
        if len([stamp for stamp in recent if now - stamp <= 60]) >= 2:
            projects = self.rows("SELECT DISTINCT project FROM readings WHERE device=?", (device,))
            for project in projects or [{"project": None}]:
                self.problem(project["project"], "$SYS/broker/log", f"Repeated connections are replacing device ID {device}.",
                             "Two clients may share DEVICE_ID. Give each board/simulator a unique MQTT client ID. Reconnects alone cannot prove two physical boards.", now)

    def projects(self, now=None):
        now = time.time() if now is None else now
        result = self.rows("""SELECT p.*, COUNT(DISTINCT r.device) AS devices,
            COALESCE(SUM(CASE WHEN r.received>=? AND r.retained=0 THEN 1 ELSE 0 END),0)/15.0 AS rate
            FROM projects p LEFT JOIN readings r ON p.name=r.project GROUP BY p.name ORDER BY p.name""", (now - 15,))
        for item in result:
            item["online"] = item["last_seen"] is not None and now - item["last_seen"] < 15
            item["first_data_seconds"] = None if item["first_data"] is None else max(0, item["first_data"] - item["started"])
        return result

    def project(self, name):
        return next((item for item in self.projects() if item["name"] == name), None)

    def project_detail(self, name):
        project = self.project(name)
        if project is None:
            return None
        # Take a window per sensor, so a fast sensor cannot hide a slower one.
        readings = self.rows("""SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY device,sensor ORDER BY id DESC) AS position
            FROM readings WHERE project=?) WHERE position<=120 ORDER BY id DESC""", (name,))
        series = {}
        for row in reversed(readings):
            key = row["device"] + "/" + row["sensor"]
            series.setdefault(key, []).append(row)
        devices = self.rows("SELECT device, MAX(CASE WHEN retained=0 THEN received END) AS last_seen FROM readings WHERE project=? GROUP BY device", (name,))
        messages = self.rows("SELECT * FROM messages WHERE project=? ORDER BY id DESC LIMIT 20", (name,))
        events = self.rows("SELECT * FROM messages WHERE project=? AND kind!='reading' ORDER BY id DESC LIMIT 40", (name,))
        problems = self.rows("SELECT * FROM problems WHERE project=? OR project IS NULL ORDER BY id DESC LIMIT 30", (name,))
        return {"project": project, "series": {key: rows[-120:] for key, rows in series.items()},
                "devices": devices, "messages": messages, "events": events, "problems": problems}

    def overview(self):
        return {"projects": self.projects(), "broker_connected": self.connected, "last_any": self.last_any,
                "problems": self.rows("SELECT * FROM problems ORDER BY id DESC LIMIT 30"), "version": self.version}

    def benchmark_save(self, run_id, started, host, status, result=None):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO benchmarks VALUES (?,?,?,?,?)",
                            (run_id, started, status, host, json.dumps(result) if result else None))
            self.prune()
            self.version += 1

    def benchmarks(self):
        rows = self.rows("SELECT * FROM benchmarks ORDER BY started DESC LIMIT 100")
        for row in rows:
            row["result"] = json.loads(row["result"]) if row["result"] else None
        return rows
