"""Bounded ACARS archive; sampled input, never an incident verification service."""
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from contextlib import contextmanager

RULES = [
    ('Possible safety / emergency', 100, 'MAYDAY|PAN PAN|EMERGENCY|SMOKE|FIRE|DEPRESSURIZATION|DEPRESSURISATION|DECOMPRESSION|DITCHING'),
    ('Medical', 80, 'MEDICAL|CPR|UNRESPONSIVE|DOCTOR|PARAMEDIC|ILL PASSENGER|SICK PASSENGER'),
    ('Diversion / return', 70, 'DIVERT|DIVERTING|DIVERSION|RETURN TO|RETURNING TO|AIR TURNBACK'),
    ('Technical', 50, 'ENGINE FAILURE|ENGINE FAIL|ENGINE SHUTDOWN|HYDRAULIC|FUEL LEAK|BIRD STRIKE|WINDSHIELD|BRAKE FAILURE|UNRELIABLE AIRSPEED'),
    ('Crew / disruption', 30, 'TIME OUT|TIMED OUT|TIMEOUT|DUTY LIMIT|CREW LIMIT|OUTAGE|GROUND STOP|UNRULY|SECURITY ISSUE'),
    ('Possibly funny / human', 20, 'LOL|HAHA|HAHAHA|JOKE|FUNNY|HAPPY BIRTHDAY|MERRY CHRISTMAS|HAPPY NEW YEAR|LOVE YOU|THANK YOU|THANKS|GOOD MORNING|GOOD NIGHT|HELLO|COFFEE|PIZZA|BEER|SANDWICH'),
    ('Conversational text', 12, 'PLEASE|CAN YOU|COULD YOU|WE HAVE|WE ARE|I HAVE|I AM|LET US KNOW|LET ME KNOW|SEE YOU|SORRY|CHEERS|REGARDS|REQUEST|PASSENGER|CREW'),
]
PATTERNS = [(name, weight, [(term, re.compile(r'(?<![A-Z0-9])' + r'\s+'.join(map(re.escape, term.split())) + r'(?![A-Z0-9])', re.I)) for term in terms.split('|')]) for name, weight, terms in RULES]
HEX = re.compile(r'^[0-9a-f]{6}$')


def scalar(v):
    return str(v) if isinstance(v, (str, int, float)) and not isinstance(v, bool) else ''


def obj(v):
    return v if isinstance(v, dict) else {}


def registration(v):
    return re.sub('[^A-Z0-9]', '', scalar(v).upper())[:16]


def classify(text):
    hits = [{'name': name, 'terms': [term for term, p in terms if p.search(text)], 'weight': weight} for name, weight, terms in PATTERNS]
    hits = [h for h in hits if h['terms']]
    if not hits and len(re.findall('[A-Za-z]{2,}', text)) >= 6 and sum(c.isalpha() or c.isspace() for c in text) / max(1, len(text)) >= .7:
        hits = [{'name': 'Possibly readable plain text', 'terms': [], 'weight': 5}]
    return max((h['weight'] for h in hits), default=0) + min(9, max(0, len(hits)-1)), hits


class Archive:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get('ARCHIVE_DB_PATH') or str(Path(os.environ.get('DATA_DIR', '/data')) / 'acars.sqlite3'))
        self.days = max(1, min(90, int(os.environ.get('ACARS_RETENTION_DAYS', '7'))))
        self.limit = max(500, min(1000000, int(os.environ.get('ACARS_MAX_MESSAGES', '20000'))))
        self.bytes_limit = max(8, min(4096, int(os.environ.get('ACARS_MAX_PAYLOAD_MB', '128')))) * 1024 * 1024
        self.lock = threading.RLock()
        self.client = None
        self.thread = None
        self.stopped = threading.Event()
        self.status = dict(state='Starting', error='', received=0, accepted=0, duplicates=0, other=0, blank=0, lastSource='', lastEventKeys=[], lastReceived=None)
        with self.db() as c:
            c.executescript('CREATE TABLE IF NOT EXISTS acars (key TEXT PRIMARY KEY, received REAL NOT NULL, hex TEXT NOT NULL, reg TEXT NOT NULL, score INTEGER NOT NULL, size INTEGER NOT NULL, payload TEXT NOT NULL); CREATE INDEX IF NOT EXISTS acars_time ON acars(received DESC); CREATE INDEX IF NOT EXISTS acars_hex ON acars(hex,received DESC); CREATE INDEX IF NOT EXISTS acars_reg ON acars(reg,received DESC); CREATE INDEX IF NOT EXISTS acars_score ON acars(score DESC,received DESC);')
            self.prune(c)

    @contextmanager
    def db(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(str(self.path), timeout=20)
        try:
            with c:
                yield c
        finally:
            c.close()

    def prune(self, c):
        c.execute('DELETE FROM acars WHERE received < ?', (time.time()-self.days*86400,))
        c.execute('DELETE FROM acars WHERE key NOT IN (SELECT key FROM acars ORDER BY received DESC LIMIT ?)', (self.limit,))
        # A payload budget in addition to a count cap; SQLite adds index/page overhead.
        c.execute('DELETE FROM acars WHERE key IN (SELECT key FROM (SELECT key, SUM(size) OVER (ORDER BY received DESC, key) AS total FROM acars) WHERE total > ?)', (self.bytes_limit,))

    def receive(self, raw):
        with self.lock:
            self.status['received'] += 1
            if not isinstance(raw, dict):
                self.status['other'] += 1
                return
            a, f, station = obj(raw.get('airframe')), obj(raw.get('flight')), obj(raw.get('station'))
            source = scalar(raw.get('source_type') or raw.get('sourceType') or station.get('source_type') or station.get('sourceType')).strip().lower()
            self.status.update(lastSource=source, lastEventKeys=list(raw)[:50])
            if source != 'acars':
                self.status['other'] += 1
                return
            text = (scalar(raw.get('text')).strip() or scalar(raw.get('data')).strip())[:20000]
            if not text:
                self.status['blank'] += 1
                return
            encoded = json.dumps(raw, ensure_ascii=False)
            oversized = len(encoded.encode()) > 65536
            hex_ = scalar(a.get('icao_hex') or a.get('icaoHex') or a.get('hex') or raw.get('icao_hex')).lower().removeprefix('0x')
            if not HEX.fullmatch(hex_):
                hex_ = ''
            tail = scalar(raw.get('tail') or a.get('registration') or a.get('tail'))
            reg = registration(tail)
            flight = scalar(raw.get('flightNumber') or f.get('flight_number') or f.get('flightNumber') or f.get('callsign') or raw.get('flight'))
            score, hits = classify(text)
            fingerprint = json.dumps([hex_, reg, raw.get('airframe_id'), flight, raw.get('label'), raw.get('message_number',raw.get('messageNumber')), text])
            key = hashlib.sha256(fingerprint.encode()).hexdigest()
            now = time.time()
            m = dict(key=key, hex=hex_, tail=tail, flight=flight, text=text, score=score, hits=hits, received=now, sourceTime=raw.get('timestamp') or raw.get('created_at') or raw.get('createdAt'), direction=scalar(raw.get('link_direction')) or 'unknown', raw=raw)
            if oversized:
                m['raw'] = dict(raw_metadata_omitted='Payload exceeded 64 KiB; normalised text and identity retained.')
            payload = json.dumps(m, ensure_ascii=False)
            with self.db() as c:
                previous = c.execute('SELECT received FROM acars WHERE key=?', (key,)).fetchone()
                if previous and now-previous[0] < 600:
                    self.status['duplicates'] += 1
                    return
                c.execute('INSERT OR REPLACE INTO acars VALUES (?,?,?,?,?,?,?)', (key,now,hex_,reg,score,len(payload.encode()),payload))
                self.prune(c)
            self.status['accepted'] += 1
            self.status['lastReceived'] = now

    def query(self, hex_='', reg='', top=False, offset=0):
        with self.lock, self.db() as c:
            self.prune(c)
            where, params = '', []
            if not top:
                if hex_ and reg:
                    where, params = "WHERE hex=? OR (hex='' AND reg=?)", [hex_,reg]
                elif hex_:
                    where, params = 'WHERE hex=?', [hex_]
                elif reg:
                    where, params = 'WHERE reg=?', [reg]
                else:
                    where = 'WHERE 0'
            total = c.execute('SELECT COUNT(*) FROM acars '+where, params).fetchone()[0]
            order = 'score DESC, received DESC' if top else 'received DESC'
            limit = 500 if top else 100
            rows = [json.loads(row[0]) for row in c.execute('SELECT payload FROM acars '+where+' ORDER BY '+order+' LIMIT ? OFFSET ?', params+[limit,offset])]
            saved = c.execute('SELECT COUNT(*) FROM acars').fetchone()[0]
            return dict(messages=rows, total=min(total,500) if top else total, offset=offset, limit=limit, saved=saved, status=dict(self.status), sampled=True, retentionDays=self.days, maxMessages=self.limit, maxPayloadMB=self.bytes_limit//1048576, database=str(self.path), match='ICAO24; registration fallback only when the message has no conflicting ICAO24. No callsign-only matching.')

    def start(self):
        self.thread = threading.Thread(target=self.collect, daemon=True, name='acars-stream')
        self.thread.start()

    def stop(self):
        self.stopped.set()
        if self.client and self.client.connected:
            self.client.disconnect()

    def collect(self):
        import socketio
        client = self.client = socketio.Client(reconnection=True, reconnection_delay=15, reconnection_delay_max=60)
        def status(**values):
            with self.lock:
                self.status.update(values)
        @client.event
        def connect():
            status(state='Connected - subscribing', error='')
            client.emit('messages:sniff')
        @client.on('messages:sniff:started')
        def started(*args):
            status(state='Live - sampled stream', error='')
        @client.on('message')
        def incoming(raw):
            try:
                self.receive(raw)
            except Exception:
                logging.exception('ACARS message processing failed')
                status(error='Message processing error; see server logs.')
        @client.event
        def disconnect(*args):
            if not self.stopped.is_set():
                status(state='Disconnected / reconnecting')
        @client.on('auth:error')
        @client.on('feed:error')
        @client.on('error')
        def refused(*args):
            self.stopped.set()
            status(state='Stream stopped', error='Stream refused access or reported an error. Check access before restarting.')
            client.disconnect()
        try:
            client.connect('https://ws.airframes.io', transports=['websocket'], wait_timeout=20)
            client.wait()
            if not self.stopped.is_set():
                status(state='Stream stopped', error='Server ended the stream; check diagnostics before restarting.')
        except Exception:
            logging.exception('ACARS stream connection failed')
            if not self.stopped.is_set():
                status(state='Connection failed', error='Check stream access and server logs, then restart. No API key is used.')
