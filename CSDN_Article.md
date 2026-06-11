# FastAPI 项目性能飞升 100x！Redis 缓存落地实战

## 📋 前言

我最近在开发一个游戏的后端，用的是 FastAPI。刚开始一切顺利，但上线测试后发现了一个大问题：

| 接口 | 响应时间 |
|------|---------|
| 房间列表 | 500-1000ms |
| 房间详情 | 100-300ms |
| WebSocket 广播 | 500-800ms |

这完全没法用啊！房间消息要 1 秒多才刷出来，体验太差了。

经过一番分析和优化，最后效果很显著：

| 接口 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 房间列表 | 500-1000ms | 1-5ms | **100-500x** |
| 房间详情 | 100-300ms | 1-5ms | **20-60x** |
| WebSocket 广播 (5人) | 500-800ms | 50-100ms | **5-10x** |

今天这篇文章，我就来详细讲讲我是怎么优化的。

---

## 🔍 问题分析

### 1. 为什么慢？

我分析了一下，主要两个问题：

1. **数据库查询频繁**
   - 每次进房间都要查房间信息
   - 每次刷房间列表都要 SELECT
   - 玩家准备状态变更也要写库 + 读库

2. **WebSocket 广播是同步的**
   ```python
   # 优化前的代码（大概长这样）
   for player in players:
       await send_message(player, message)  # 逐个等待发送
   ```
   - 10 个玩家就要等 10 次网络 IO
   - 累积延迟太严重

### 2. 技术选型

项目主要用 Redis 做缓存，但有个问题：**这项目是在 Windows 上开发的！**

我试过了几种方案：
- ❌ Memurai：安装太麻烦
- ❌ WSL2：网络配置麻烦
- ❌ Docker Desktop：太重了

所以我决定自己写一个轻量级的！

---

## 🚀 方案一：嵌入式 Redis 服务器

### 核心思路

用 Python 写一个简单的 Redis 服务器，支持我们需要的基础命令就行。

### 完整代码

```python
import socket
import threading
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class MiniRedisServer:
    def __init__(self, host: str = 'localhost', port: int = 6379):
        self.host = host
        self.port = port
        self._data: Dict[str, Dict[str, any]] = {}
        self._server_socket: Optional[socket.socket] = None
        self._running = False
        self._clients = []
    
    def start(self):
        # 先检测是否有 Redis 已经在运行
        try:
            import redis
            r = redis.Redis(host=self.host, port=self.port, socket_timeout=1)
            r.ping()
            logger.info(f"Redis 服务器已在运行，端口 {self.port}")
            return True
        except:
            pass
            
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(5)
        self._running = True
        
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()
        
        logger.info(f"✅ 轻量级 Redis 服务器已启动: {self.host}:{self.port}")
        return True
    
    # ... 省略部分实现代码，完整代码见 GitHub
    
    def _process_command(self, command: str):
        lines = [line.strip() for line in command.split('\r\n') if line.strip()]
        # 简单的 RESP 协议解析
        # 支持 SET/GET/SETEX/HSET/HGET/HGETALL/DEL
        # ... 具体实现 ...
```

### 使用效果

```
INFO: 正在启动嵌入式 Redis...
INFO: ✅ 轻量级 Redis 服务器已启动: localhost:6379
```

完美！不需要安装任何东西，纯 Python 实现！

---

## 🎯 方案二：智能缓存层

### 缓存设计

| 数据类型 | Key | 过期时间 | 说明 |
|---------|-----|---------|------|
| 房间信息 | `room:{code}` | 1h | 房间基本信息 |
| 房间玩家 | `room:players:{code}` | 1h | 房间玩家列表 |
| 房间列表 | `online_rooms` | 1min | 在线房间列表 |
| 游戏状态 | `game:state:{id}` | 2h | 实时游戏状态 |

### 完整缓存类

```python
class RedisCache:
    def __init__(self):
        self._redis_client = None
    
    def _get_redis(self):
        if self._redis_client is None:
            self._redis_client = get_redis_client()
        return self._redis_client
    
    async def cache_room(self, room: OnlineRoom):
        key = f"room:{room.room_code}"
        room_data = {
            "id": room.id,
            "room_code": room.room_code,
            "room_name": room.room_name,
            "host_id": room.host_id,
            "max_player_count": room.max_player_count,
            "current_player_count": room.current_player_count,
            "room_status": room.room_status,
            "game_id": room.game_id,
            "game_mode": room.game_mode,
            "create_time": room.create_time.isoformat() if room.create_time else None,
            "is_deleted": room.is_deleted
        }
        
        redis = self._get_redis()
        async_redis = redis.get_async_client()
        
        if async_redis:
            await async_redis.setex(
                name=key,
                time=3600,  # 1 hour
                value=self._serialize(room_data)
            )
    
    # ... get_cached_room, invalidate_room 等等方法
```

### 使用缓存改造接口

```python
@router.get("/list")
async def get_room_list(db: Session = Depends(get_db)):
    # 先查缓存
    cached = await cache.get_cached_online_rooms()
    if cached is not None:
        return ApiResponse.success(data=cached)
    
    # 缓存未命中，查数据库
    rooms = db.query(OnlineRoom).filter(...).all()
    
    # 写缓存
    await cache.cache_online_rooms([...])
    
    return ApiResponse.success(data=...)
```

---

## ⚡ 方案三：WebSocket 广播优化

### 问题代码

```python
# 优化前：同步逐个发送
async def broadcast(self, room_code: str, message: dict):
    connections = self.get_room_connections(room_code)
    for conn in connections:
        try:
            await conn.send_json(message)  # 每次都等
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
```

### 优化代码

```python
# 优化后：用 asyncio.gather 并发
async def broadcast(self, room_code: str, message: dict):
    connections = self.get_room_connections(room_code)
    tasks = []
    
    for conn in connections:
        tasks.append(self._send_safe(conn, message))
    
    if tasks:
        await asyncio.gather(*tasks)  # 并发发送

async def _send_safe(self, connection, message):
    try:
        await connection.send_json(message)
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
```

---

## 📊 性能对比测试

### 测试环境

- CPU: 普通办公电脑
- 数据库: MySQL 5.7
- 测试工具: 手动 + 日志计时

### 房间列表测试

| 场景 | 优化前 | 优化后 |
|------|--------|--------|
| 空房间列表 | 500ms | 3ms |
| 10 个房间 | 800ms | 5ms |
| 20 个房间 | 1000ms | 5ms |

### 房间详情测试

| 操作 | 优化前 | 优化后 |
|------|--------|--------|
| 查询房间 | 150ms | 2ms |
| 玩家进入房间 | 200ms | 20ms（写缓存） |
| 玩家准备 | 100ms | 15ms（更新缓存） |

### WebSocket 广播测试

| 人数 | 优化前 | 优化后 |
|------|--------|--------|
| 5 人 | 500ms | 80ms |
| 10 人 | 1000ms | 150ms |
| 20 人 | 2000ms | 300ms |

---

## 🎁 完整解决方案

### 自动降级逻辑

```python
# redis_client.py
class RedisClient:
    def __init__(self):
        # 先试外部 Redis
        if not self._try_connect_external_redis():
            # 不行就启动嵌入式
            if _HAS_EMBEDDED:
                if start_embedded_redis():
                    self._try_connect_external_redis()
```

### 项目启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
python -m app.main

# 3. 看到这个就成功了
INFO: ✅ 轻量级 Redis 服务器已启动: localhost:6379
INFO: Uvicorn running on http://0.0.0.0:8000
```

---

## 📝 总结

这次优化给我几个感悟：

1. **缓存真的很重要** - 数据库是瓶颈，Redis 能救你
2. **异步并发是利器** - WebSocket 广播用 `asyncio.gather` 立马快 10 倍
3. **Windows 也能玩 Redis** - 不一定非要装 Memurai，自己写一个也能用
4. **不要过度设计** - 我们这个 mini Redis 只支持需要的命令，够用就行

---

## 🔗 相关链接

- 项目 GitHub: [yacht-dice](https://github.com/...)
- 完整代码: [GitHub repo](https://github.com/...)
- Redis 官方文档: [redis.io](https://redis.io)

---

**如果你觉得这篇文章对你有帮助，欢迎点赞、收藏、关注！你的支持是我创作的最大动力！❤️**
