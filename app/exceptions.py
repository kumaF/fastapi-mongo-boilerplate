from fastapi.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

async def http_exception_handler(request: Request, e: HTTPException):
    return JSONResponse(
        status_code = e.status_code,
        content = {
            'success': False,
            'detail': e.detail
        },
    )
