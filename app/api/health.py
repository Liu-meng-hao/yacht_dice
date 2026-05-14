from fastapi import APIRouter

router = APIRouter(tags=["健康检查"])


@router.get("/health", summary="健康检查", description="检查后端服务是否正常运行")
async def health_check():
    return {"status": "ok", "message": "快艇骰子游戏后端服务运行正常"}
