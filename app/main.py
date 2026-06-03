from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.middleware import RequestLogMiddleware
from app.api import health, home, room, game, websocket, score, settlement, auth, leaderboard

setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="快艇骰子游戏后端API服务"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(RequestLogMiddleware)

app.include_router(health.router, prefix=settings.API_V1_STR, tags=["健康检查"])
app.include_router(home.router, prefix=f"{settings.API_V1_STR}/home", tags=["首页"])
app.include_router(room.router, prefix=f"{settings.API_V1_STR}/room", tags=["房间"])
app.include_router(game.router, prefix=f"{settings.API_V1_STR}/game", tags=["游戏"])
# 注意：websocket.router 中的房间 WS 端点路径是 /room/ws/...
# 挂载到 /game 前缀下会变成 /api/v1/game/room/ws/...，路径不正确
# 所以只保留游戏 WS 的 router 挂载，房间 WS 通过 add_api_websocket_route 直接注册
# app.include_router(websocket.router, prefix=f"{settings.API_V1_STR}/game", tags=["实时通信"])
app.include_router(score.router, prefix=f"{settings.API_V1_STR}/score", tags=["计分"])
app.include_router(settlement.router, prefix=f"{settings.API_V1_STR}/settlement", tags=["结算"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["认证"])
app.include_router(leaderboard.router, prefix=f"{settings.API_V1_STR}/leaderboard", tags=["排行榜"])

app.router.add_api_websocket_route(
    path=f"{settings.API_V1_STR}/game/ws/{{game_id}}/{{player_id}}",
    endpoint=websocket.websocket_endpoint
)

app.router.add_api_websocket_route(
    path=f"{settings.API_V1_STR}/room/ws/{{room_code}}/{{player_id}}",
    endpoint=websocket.room_websocket_endpoint
)

_original_openapi = app.openapi

def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description="快艇骰子游戏后端API服务",
        routes=app.routes,
    )
    
    # 添加游戏 WebSocket 文档
    game_ws_path = f"{settings.API_V1_STR}/game/ws/{{game_id}}/{{player_id}}"
    if game_ws_path not in openapi_schema["paths"]:
        openapi_schema["paths"][game_ws_path] = {
            "get": {
                "summary": "游戏 WebSocket 连接",
                "description": "建立 WebSocket 连接用于实时游戏状态同步",
                "tags": ["实时通信"],
                "operationId": "game_websocket_connect",
                "parameters": [
                    {
                        "name": "game_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "description": "游戏ID"}
                    },
                    {
                        "name": "player_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "description": "玩家ID"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "WebSocket 连接成功"
                    }
                }
            }
        }
    
    # 添加房间 WebSocket 文档
    room_ws_path = f"{settings.API_V1_STR}/room/ws/{{room_code}}/{{player_id}}"
    if room_ws_path not in openapi_schema["paths"]:
        openapi_schema["paths"][room_ws_path] = {
            "get": {
                "summary": "房间 WebSocket 连接",
                "description": "建立 WebSocket 连接用于房间状态实时同步，包括玩家加入、离开、准备状态变化等",
                "tags": ["实时通信"],
                "operationId": "room_websocket_connect",
                "parameters": [
                    {
                        "name": "room_code",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "description": "房间编码（6位字母数字）"}
                    },
                    {
                        "name": "player_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "description": "玩家ID"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "WebSocket 连接成功"
                    },
                    "403": {
                        "description": "玩家不在该房间中，连接被拒绝"
                    }
                }
            }
        }
    
    if "实时通信" not in [t["name"] for t in openapi_schema.get("tags", [])]:
        openapi_schema.setdefault("tags", []).append({
            "name": "实时通信",
            "description": "WebSocket 实时通信接口，用于多人游戏状态同步"
        })
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = _custom_openapi

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
