from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "快艇骰子游戏后端服务运行正常"}
