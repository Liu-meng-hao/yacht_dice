# WebSocket 实时通信改进建议

## 一、当前实现分析

### 1.1 架构概览

当前 WebSocket 实时通信模块包含两个核心文件：

| 文件路径 | 职责 |
|---------|------|
| `app/api/game.py` | WebSocket 端点定义（第 268-280 行） |
| `app/websocket/manager.py` | 连接管理器实现 |

### 1.2 现有功能

- **连接管理**：支持房间级别的连接管理
- **消息广播**：支持向同房间所有玩家发送消息
- **单播支持**：支持向指定玩家发送消息

---

## 二、存在的问题

### 2.1 消息处理问题

| 问题 | 位置 | 风险等级 |
|------|------|---------|
| 消息格式未验证 | `game.py:276-277` | **高危** |
| 无消息类型区分 | `game.py:277` | 中危 |
| 广播无异常捕获 | `manager.py:39-42` | **高危** |

### 2.2 连接管理问题

| 问题 | 位置 | 风险等级 |
|------|------|---------|
| 无心跳检测机制 | `manager.py` | **高危** |
| 无身份认证 | `game.py:268-273` | **高危** |
| 无连接数限制 | `manager.py` | 中危 |

### 2.3 架构设计问题

| 问题 | 影响 |
|------|------|
| WebSocket 端点与 REST API 混合 | 违反单一职责原则 |
| 缺乏消息持久化 | 历史消息无法追溯 |
| 缺乏日志记录 | 问题难以追踪 |

---

## 三、改进建议

### 3.1 消息格式验证

**问题**：当前直接转发原始文本，缺乏验证

**解决方案**：添加消息结构验证

```python
from pydantic import BaseModel, ValidationError
from enum import Enum

class MessageType(str, Enum):
    CHAT = "chat"
    GAME_ACTION = "game_action"
    SYSTEM = "system"

class GameMessage(BaseModel):
    type: MessageType
    content: dict
    timestamp: str

# 使用示例
async def handle_message(websocket, data):
    try:
        message = GameMessage.parse_raw(data)
    except ValidationError as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Invalid message format"
        }))
        return
```

### 3.2 安全的广播机制

**问题**：单连接失败会导致整个广播中断

**解决方案**：添加异常捕获和无效连接清理

```python
async def broadcast(self, room_id: str, message: dict):
    if room_id not in self.active_connections:
        return
    
    message_str = json.dumps(message)
    dead_connections = []
    
    for connection in self.active_connections[room_id]:
        try:
            await connection.send_text(message_str)
        except Exception as e:
            dead_connections.append(connection)
    
    # 清理无效连接
    for conn in dead_connections:
        self.active_connections[room_id].remove(conn)
```

### 3.3 心跳检测机制

**问题**：无法检测客户端异常断开

**解决方案**：实现 ping/pong 心跳检测

```python
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.player_connections: Dict[str, Dict[str, WebSocket]] = {}
        self.connection_timestamps: Dict[str, Dict[WebSocket, float]] = {}
    
    async def check_connections(self):
        """定时检查无效连接"""
        while True:
            await asyncio.sleep(30)
            now = time.time()
            
            for room_id in list(self.active_connections.keys()):
                dead_connections = []
                
                for conn in self.active_connections[room_id]:
                    last_ping = self.connection_timestamps.get(room_id, {}).get(conn, 0)
                    if now - last_ping > 60:  # 超过60秒无响应
                        dead_connections.append(conn)
                
                for conn in dead_connections:
                    self.active_connections[room_id].remove(conn)
                    if conn in self.connection_timestamps.get(room_id, {}):
                        del self.connection_timestamps[room_id][conn]
    
    async def send_ping(self, room_id: str, websocket: WebSocket):
        """发送心跳包"""
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_text(json.dumps({"type": "ping"}))
                self.connection_timestamps[room_id][websocket] = time.time()
            except Exception:
                break
```

### 3.4 身份认证机制

**问题**：任何人可通过伪造 player_id 冒充其他玩家

**解决方案**：添加 Token 验证

```python
async def websocket_endpoint(websocket: WebSocket, game_id: str, player_id: str):
    # 获取查询参数中的 token
    query_params = websocket.query_params
    token = query_params.get("token")
    
    # 验证 Token
    if not validate_token(token, player_id, game_id):
        await websocket.close(code=1008)  # 策略性关闭
        return
    
    await manager.connect(game_id, player_id, websocket)
    # ... 后续逻辑
```

### 3.5 代码结构优化

**建议**：将 WebSocket 端点分离到独立文件

**目录结构**：
```
app/
├── api/
│   ├── game.py          # REST API
│   ├── websocket.py     # WebSocket 端点（新增）
│   └── __init__.py
└── websocket/
    ├── manager.py       # 连接管理器
    └── __init__.py
```

**分离后的 `app/api/websocket.py`**：
```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket.manager import manager
import json
from datetime import datetime

router = APIRouter(tags=["实时通信"])

@router.websocket("/ws/{game_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, player_id: str):
    """WebSocket 游戏实时通信端点"""
    await manager.connect(game_id, player_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            
            # 消息格式验证
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON"
                }))
                continue
            
            # 添加元数据
            message["player_id"] = player_id
            message["timestamp"] = datetime.now().isoformat()
            
            # 安全广播
            await manager.broadcast(game_id, message)
            
    except WebSocketDisconnect:
        manager.disconnect(game_id, player_id, websocket)
    except Exception as e:
        manager.disconnect(game_id, player_id, websocket)
```

---

## 四、优先级排序

| 优先级 | 改进项 | 预期收益 |
|-------|-------|---------|
| **P0** | 消息格式验证 | 防止恶意数据攻击 |
| **P0** | 广播异常捕获 | 保证广播稳定性 |
| **P0** | 心跳检测机制 | 及时清理无效连接 |
| **P1** | 身份认证 | 防止身份冒充 |
| **P1** | 代码结构分离 | 提高可维护性 |
| **P2** | 消息持久化 | 支持历史消息追溯 |
| **P2** | 连接数限制 | 防止资源耗尽 |

---

## 五、总结

当前 WebSocket 实现提供了基础的实时通信能力，但在**安全性**、**稳定性**和**可维护性**方面存在不足。建议按照优先级逐步实施上述改进方案，以提升系统的健壮性和扩展性。
