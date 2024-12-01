import dataclasses

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, Union

from handler.utils import get_user_data

router = APIRouter(tags=['User'], prefix="/users")

class UserModel(BaseModel):
    id: int
    name: str
    age: int

# 定義標準化的回應結構
class SuccessResponse(BaseModel):
    status: str
    data: Union[UserModel, Dict[str, Any]]

class ErrorResponse(BaseModel):
    status: str
    message: str

@router.get(
        "/api/v1/users/{user_id}", 
        summary="Get User by ID",
        response_model=SuccessResponse,
        responses={
            404: {
                "model": ErrorResponse,
                "description": "User not found"
            },
        }
)
async def get_user(user_id: int):
    try:
        user = get_user_data(user_id)
        return JSONResponse(
                content={
                    "status": "success",
                    "data": {
                        "id": user[0].id,
                        "name": user[0].name,
                        "age": user[0].age
                    }
                },
                status_code=200,
            )
    except ValueError as e:
        return JSONResponse(
            content={
                "status": "error",
                "message": str(e)
            },
            status_code=404,
        )