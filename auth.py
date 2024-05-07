from fastapi.security.api_key import APIKeyHeader
from fastapi import Security, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED

from store import api_key_store  # NEW!

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


async def api_key_auth(api_key: str = Security(api_key_header)):
    if api_key_store.does_api_key_exist(api_key) is False:  # NEW!
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED,
                            detail="Missing or invalid API key")
