from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Any, Generic, TypeVar, Optional
import json


T = TypeVar('T')


def snake_to_camel(snake_str: str) -> str:
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def dict_to_camel(data: Any) -> Any:
    if isinstance(data, dict):
        return {snake_to_camel(k): dict_to_camel(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [dict_to_camel(item) for item in data]
    elif isinstance(data, BaseModel):
        return dict_to_camel(data.model_dump())
    else:
        return data


class ApiResponseModel(BaseModel, Generic[T]):
    code: int = Field(description="状态码", examples=[200])
    msg: str = Field(description="提示信息", examples=["成功"])
    data: Optional[T] = Field(default=None, description="响应数据")


class ApiResponse:
    @staticmethod
    def success(data: Any = None, msg: str = "成功", code: int = 200):
        response_data = {
            "code": code,
            "msg": msg,
            "data": dict_to_camel(data) if data is not None else None
        }
        return JSONResponse(
            content=response_data,
            media_type="application/json"
        )
    
    @staticmethod
    def error(msg: str = "失败", code: int = 400, data: Any = None):
        response_data = {
            "code": code,
            "msg": msg,
            "data": dict_to_camel(data) if data is not None else None
        }
        return JSONResponse(
            content=response_data,
            media_type="application/json"
        )
