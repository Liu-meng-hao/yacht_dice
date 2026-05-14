# 快艇骰子游戏后端

基于 FastAPI + MySQL + Redis + WebSocket 的快艇骰子游戏后端服务。

## 技术栈

- **后端框架**: FastAPI 0.109.0
- **数据库**: MySQL
- **缓存**: Redis
- **实时通信**: WebSocket
- **ORM**: SQLAlchemy 2.0.25
- **数据验证**: Pydantic 2.5.3

## 功能特性

- 三种游戏模式：本地多人、人机对战、在线联机
- 房间创建与加入
- WebSocket 实时同步游戏状态
- 完整的骰子计分规则
- 回合自动流转

## 项目结构

详细的项目结构说明请查看 [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)。

## 快速开始

### 1. 环境要求

- Python 3.9+
- MySQL 5.7+
- Redis 5.0+

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境

编辑 `app/core/config.py` 或创建 `.env` 文件配置数据库和 Redis 连接：

```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=yacht_dice

REDIS_HOST=localhost
REDIS_PORT=6379
```

### 4. 创建数据库

在 MySQL 中创建数据库：

```sql
CREATE DATABASE yacht_dice CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. 启动服务

```bash
python -m app.main
```

或者使用 uvicorn：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 访问 API 文档

启动成功后，访问以下地址查看 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 接口说明

### 健康检查

- `GET /api/v1/health` - 检查服务状态

### 游戏相关

- `POST /api/v1/game/create` - 创建游戏
- `GET /api/v1/game/{game_id}` - 获取游戏状态
- `POST /api/v1/game/{game_id}/roll` - 掷骰子
- `POST /api/v1/game/{game_id}/score` - 提交分数

### 房间相关

- `POST /api/v1/game/rooms/create` - 创建房间
- `POST /api/v1/game/rooms/join` - 加入房间
- `GET /api/v1/game/rooms/{room_code}` - 获取房间信息

### WebSocket

- `WS /api/v1/game/ws/{room_code}/{player_id}` - WebSocket 连接

## 开发者

快艇骰子游戏开发团队

## 许可证

MIT License
