"""
proxy_server.py
===============
RecruitFlow Single-URL Reverse Proxy Server.

Unifies Streamlit Frontend (Port 8501) and FastAPI Backend (Port 8000) under
a single entry point on Port 10000 (or $PORT).

Routing Architecture:
  - /api/*           -> FastAPI Backend (http://127.0.0.1:8000/*)
  - /docs            -> FastAPI Swagger UI
  - /redoc           -> FastAPI ReDoc UI
  - /openapi.json    -> FastAPI OpenAPI Schema
  - /health          -> FastAPI Health Check
  - /_stcore/stream  -> Streamlit WebSocket (ws://127.0.0.1:8501/_stcore/stream)
  - /stream          -> Streamlit WebSocket (ws://127.0.0.1:8501/stream)
  - /* (all other)   -> Streamlit Frontend (http://127.0.0.1:8501/*)
"""

import asyncio
import logging
import os
import sys
import urllib3
import websockets
from starlette.datastructures import Headers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Proxy] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("recruitflow.proxy")

# Configuration
PROXY_PORT = int(os.getenv("PORT", os.getenv("PROXY_PORT", "10000")))
PROXY_HOST = os.getenv("PROXY_HOST", "0.0.0.0")
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_HOST = os.getenv("FRONTEND_HOST", "127.0.0.1")
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "8501"))

BACKEND_HTTP = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
FRONTEND_HTTP = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"
FRONTEND_WS = f"ws://{FRONTEND_HOST}:{FRONTEND_PORT}"

# Connection pool for HTTP forwarding
http_pool = urllib3.PoolManager(
    timeout=urllib3.Timeout(connect=10.0, read=120.0),
    maxsize=50,
)

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


async def forward_websocket(scope, receive, send):
    """Bidirectional WebSocket forwarding between client and Streamlit frontend."""
    path = scope.get("path", "")
    query_string = scope.get("query_string", b"").decode("latin-1")
    target_url = f"{FRONTEND_WS}{path}"
    if query_string:
        target_url = f"{target_url}?{query_string}"

    headers = dict(scope.get("headers", []))
    target_headers = {}
    for k, v in headers.items():
        k_str = k.decode("latin-1").lower()
        if k_str not in HOP_BY_HOP and k_str != "host":
            target_headers[k_str] = v.decode("latin-1")

    # Accept the client WebSocket connection
    await send({"type": "websocket.accept"})

    try:
        async with websockets.connect(
            target_url,
            additional_headers=target_headers,
            ping_interval=20,
            ping_timeout=20,
            max_size=50 * 1024 * 1024,
        ) as upstream_ws:

            async def client_to_upstream():
                while True:
                    message = await receive()
                    msg_type = message.get("type")
                    if msg_type == "websocket.receive":
                        if "text" in message and message["text"] is not None:
                            await upstream_ws.send(message["text"])
                        elif "bytes" in message and message["bytes"] is not None:
                            await upstream_ws.send(message["bytes"])
                    elif msg_type == "websocket.disconnect":
                        await upstream_ws.close()
                        break

            async def upstream_to_client():
                while True:
                    try:
                        data = await upstream_ws.recv()
                        if isinstance(data, str):
                            await send({"type": "websocket.send", "text": data})
                        else:
                            await send({"type": "websocket.send", "bytes": data})
                    except websockets.exceptions.ConnectionClosed:
                        await send({"type": "websocket.close", "code": 1000})
                        break

            await asyncio.gather(client_to_upstream(), upstream_to_client())

    except Exception as exc:
        logger.debug("WebSocket connection finished/closed: %s", exc)
        try:
            await send({"type": "websocket.close", "code": 1000})
        except Exception:
            pass


def determine_target_url(path: str, query_string: str) -> str:
    """Determine upstream URL based on path routing rules."""
    query_suffix = f"?{query_string}" if query_string else ""

    # 1. FastAPI Documentation, Schemas & Health
    if (
        path in ("/docs", "/redoc", "/openapi.json", "/health")
        or path.startswith(("/docs/", "/redoc/", "/openapi.json"))
    ):
        return f"{BACKEND_HTTP}{path}{query_suffix}"

    # 2. FastAPI REST Endpoints (/api/...)
    if path.startswith("/api/"):
        stripped = path[4:]  # retains leading slash e.g. /candidates/
        return f"{BACKEND_HTTP}{stripped}{query_suffix}"
    if path == "/api":
        return f"{BACKEND_HTTP}/{query_suffix}"

    # 3. Everything else -> Streamlit Frontend
    return f"{FRONTEND_HTTP}{path}{query_suffix}"


async def forward_http(scope, receive, send):
    """Streamlined HTTP reverse proxy forwarding to upstream services."""
    method = scope["method"]
    path = scope.get("path", "/")
    query_string = scope.get("query_string", b"").decode("latin-1")

    # Read incoming request body
    body_chunks = []
    more_body = True
    while more_body:
        message = await receive()
        body_chunks.append(message.get("body", b""))
        more_body = message.get("more_body", False)
    body = b"".join(body_chunks)

    # Determine target URL
    target_url = determine_target_url(path, query_string)

    # Prepare forwarded headers
    in_headers = dict(scope.get("headers", []))
    forward_headers = {}
    for k, v in in_headers.items():
        k_str = k.decode("latin-1").lower()
        if k_str not in HOP_BY_HOP and k_str != "host":
            forward_headers[k_str] = v.decode("latin-1")

    client_ip = scope.get("client", ("127.0.0.1", 0))[0]
    forward_headers["X-Forwarded-For"] = client_ip
    forward_headers["X-Forwarded-Proto"] = scope.get("scheme", "http")
    forward_headers["Host"] = (
        f"{BACKEND_HOST}:{BACKEND_PORT}" if "/api" in path or path in ("/docs", "/redoc", "/health", "/openapi.json")
        else f"{FRONTEND_HOST}:{FRONTEND_PORT}"
    )

    try:
        # Run blocking pool request in worker thread to maintain asyncio responsiveness
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: http_pool.request(
                method,
                target_url,
                headers=forward_headers,
                body=body if body else None,
                preload_content=False,
                redirect=False,
            ),
        )

        # Prepare outgoing headers (filter hop-by-hop)
        out_headers = []
        for header_name, header_value in resp.headers.items():
            if header_name.lower() not in HOP_BY_HOP:
                out_headers.append(
                    (header_name.lower().encode("latin-1"), str(header_value).encode("latin-1"))
                )

        await send({
            "type": "http.response.start",
            "status": resp.status,
            "headers": out_headers,
        })

        # Stream response body chunks
        while True:
            chunk = await loop.run_in_executor(None, lambda: resp.read(65536))
            if not chunk:
                break
            await send({
                "type": "http.response.body",
                "body": chunk,
                "more_body": True,
            })

        await send({
            "type": "http.response.body",
            "body": b"",
            "more_body": False,
        })
        resp.release_conn()

    except Exception as exc:
        logger.error("Proxy error forwarding %s %s -> %s: %s", method, path, target_url, exc)
        await send({
            "type": "http.response.start",
            "status": 502,
            "headers": [(b"content-type", b"application/json")],
        })
        err_msg = f'{{"error": "Bad Gateway", "detail": "Could not connect to upstream service: {exc}"}}'
        await send({
            "type": "http.response.body",
            "body": err_msg.encode("utf-8"),
            "more_body": False,
        })


async def app(scope, receive, send):
    """Master ASGI application router."""
    scope_type = scope.get("type")
    path = scope.get("path", "")

    if scope_type == "websocket":
        if path.startswith("/_stcore/stream") or path.startswith("/stream"):
            await forward_websocket(scope, receive, send)
        else:
            await send({"type": "websocket.close", "code": 4040})
    elif scope_type == "http":
        await forward_http(scope, receive, send)
    elif scope_type == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                logger.info(
                    "RecruitFlow Reverse Proxy active on port %s (Backend: %s, Frontend: %s)",
                    PROXY_PORT,
                    BACKEND_HTTP,
                    FRONTEND_HTTP,
                )
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                http_pool.clear()
                await send({"type": "lifespan.shutdown.complete"})
                break


if __name__ == "__main__":
    import uvicorn

    print("==================================================================")
    print("       RecruitFlow Single-URL Unified Reverse Proxy Server        ")
    print(f"       Public URL : http://localhost:{PROXY_PORT}               ")
    print(f"       Frontend   : /          -> Streamlit (Port {FRONTEND_PORT})")
    print(f"       Backend    : /api/      -> FastAPI   (Port {BACKEND_PORT}) ")
    print(f"       Swagger    : /docs      -> FastAPI   (Port {BACKEND_PORT}) ")
    print(f"       Health     : /health    -> FastAPI   (Port {BACKEND_PORT}) ")
    print("==================================================================")
    uvicorn.run("proxy_server:app", host=PROXY_HOST, port=PROXY_PORT, log_level="info")

