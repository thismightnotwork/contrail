"""Single-process Contrail + ACARS service for Railway."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import os

import uvicorn
from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route

from .acars import Archive, HEX, registration
from .app import create_app
from .config import Settings


def create_combined():
    settings = Settings.from_env()
    base = create_app(settings)
    archive = Archive()
    @asynccontextmanager
    async def lifespan(app):
        async with base.router.lifespan_context(base):
            archive.start()
            try:
                yield
            finally:
                await asyncio.to_thread(archive.stop)

    async def query(request):
        q = request.query_params
        hex_ = q.get('hex','').lower()
        if hex_ and not HEX.fullmatch(hex_):
            return JSONResponse({'error':'Invalid ICAO24'},status_code=400)
        try:
            offset = max(0,min(int(q.get('offset','0')),archive.limit))
        except ValueError:
            return JSONResponse({'error':'Invalid offset'},status_code=400)
        result = await asyncio.to_thread(archive.query,hex_,registration(q.get('registration','')),q.get('view')=='top',offset)
        return JSONResponse(result,headers={'Cache-Control':'no-store','X-Data-Source':'Airframes sampled stream; not ADSB.lol aircraft data'})

    async def board(request):
        return FileResponse(Path(settings.static_dir)/'acars.html',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"})

    async def health(request):
        return JSONResponse({'ok':True,'mode':'contrail-acars','demo':settings.demo_mode})

    return Starlette(routes=[Route('/api/acars',query),Route('/acars',board),Route('/health',health),Mount('/',app=base)],lifespan=lifespan)


if __name__ == '__main__':
    uvicorn.run(create_combined(),host=os.environ.get('HOST','0.0.0.0'),port=int(os.environ.get('PORT','8000')),access_log=False)
