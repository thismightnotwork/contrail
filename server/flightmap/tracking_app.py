"""Expose cached ADS-B presence without adding upstream lookups."""
import os
import time
import uvicorn
from starlette.responses import JSONResponse
from starlette.routing import Route
from . import app as map_app
from .index import AircraftIndex
from .acars import registration
from .combined import create_combined

CURRENT = None
MAX_AGE = 120

class ObservedIndex(AircraftIndex):
    def __init__(self):
        super().__init__()
        global CURRENT
        CURRENT = self


def presence(rows, now):
    live = []
    for aircraft, fetched_at in rows:
        age = max(0, now - fetched_at) + max(0, aircraft.position_age_s)
        if age <= MAX_AGE:
            live.append({'hex': aircraft.hex_str, 'registration': registration(aircraft.registration), 'positionTime': fetched_at-aircraft.position_age_s})
    return live


async def tracking(request):
    now = time.time()
    return JSONResponse({'ready': CURRENT is not None, 'generatedAt': now, 'maxAgeSeconds': MAX_AGE, 'aircraft': presence(CURRENT.values(), now) if CURRENT is not None else [], 'scope': 'Current server tile-cache coverage, not a worldwide presence check. Historical means not recently seen here, not confirmed landed.'}, headers={'Cache-Control': 'no-store'})


def create_app():
    # Inject a compatible index at the existing map factory's construction seam.
    map_app.AircraftIndex = ObservedIndex
    app = create_combined()
    app.router.routes.insert(0, Route('/api/acars-tracking', tracking))
    return app


if __name__ == '__main__':
    uvicorn.run(create_app(), host=os.environ.get('HOST','0.0.0.0'), port=int(os.environ.get('PORT','8000')), access_log=False)
