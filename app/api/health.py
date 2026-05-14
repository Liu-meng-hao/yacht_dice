from fastapi import APIRouter
from app.core.response import ApiResponse, ApiResponseModel
from typing import Dict

router = APIRouter(tags=["健康检查"])


@router.get(
    "/health", 
    summary="健康检查", 
    description="检查后端服务是否正常运行",
    responses={
        200: {
            "model": ApiResponseModel[Dict],
            "description": "成功响应"
        }
    }
)
async def health_check():
    return ApiResponse.success(
        data={"status": "ok"},
        msg="快艇骰子游戏后端服务运行正常"
    )
