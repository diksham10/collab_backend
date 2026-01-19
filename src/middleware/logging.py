import time
import logging
import traceback
from fastapi import Request, Response
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s  - %(message)s"
)
logger = logging.getLogger("app_logger")

#middleware functions

def mask(value: str) -> str:
    return "**MASKED**" if value else ""

async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    method = request.method
    url = str(request.url)
    client_ip = request.client.host

    try:
        response = await call_next(request)
        status_code = response.status_code
        logger.info(f"[REQUEST] {method} {url} status={status_code} client_ip={client_ip}")
        return response
    except Exception as e:
         # Extract last traceback frame (where the error actually occurred)
        tb = traceback.extract_tb(e.__traceback__)
        if tb:
            filename, lineno, func_name, _ = tb[-1]  # last frame
        else:
            filename, lineno = "unknown", 0

        logger.error(
            f"[ERROR] {method} {url} client_ip={client_ip} | error: {e} "
            f"({filename}, line={lineno})"
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    