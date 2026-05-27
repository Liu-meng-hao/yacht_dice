from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import health, home, room, game, websocket, score, settlement, auth


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="快艇骰子游戏后端API服务"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.API_V1_STR, tags=["健康检查"])
app.include_router(home.router, prefix=f"{settings.API_V1_STR}/home", tags=["首页"])
app.include_router(room.router, prefix=f"{settings.API_V1_STR}/room", tags=["房间"])
app.include_router(game.router, prefix=f"{settings.API_V1_STR}/game", tags=["游戏"])
app.include_router(websocket.router, prefix=f"{settings.API_V1_STR}/game", tags=["实时通信"])
app.include_router(score.router, prefix=f"{settings.API_V1_STR}/score", tags=["计分"])
app.include_router(settlement.router, prefix=f"{settings.API_V1_STR}/settlement", tags=["结算"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["认证"])


@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "message": "欢迎使用快艇骰子游戏后端API"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.WEBSOCKET_PORT,
        reload=True
    )
