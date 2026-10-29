"""Optional bundled storefront assets; API-only local development still uses Vite."""

from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

WEB_ROOT = Path("/opt/askflow/web")


def mount(application):
    if not (WEB_ROOT / "index.html").is_file():
        return
    application.mount("/assets", StaticFiles(directory=WEB_ROOT / "assets"), name="mall-assets")

    async def page(path: str = ""):
        return FileResponse(WEB_ROOT / "index.html", headers={"Cache-Control": "no-cache"})

    application.add_api_route("/", page, include_in_schema=False)
    for prefix in ("/shop", "/admin", "/tickets", "/login"):
        application.add_api_route(prefix, page, include_in_schema=False)
        application.add_api_route(prefix + "/{path:path}", page, include_in_schema=False)
