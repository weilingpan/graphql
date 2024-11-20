import dataclasses

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from handler.utils import get_user_data

router = APIRouter(tags=['User'], prefix="/users")

@router.get("/api/v1/users/{user_id}", summary="Get User by ID")
async def get_user(user_id: int):
    try:
        user = get_user_data(user_id)
        return JSONResponse(content=dataclasses.asdict(user))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))