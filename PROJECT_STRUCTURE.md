# 快艇骰子游戏后端项目结构说明

## 项目概述

这是一个基于 FastAPI + MySQL + Redis + WebSocket 的快艇骰子游戏后端项目。

---

## 完整目录结构

```
yacht_dice/
├── app/                          # 主应用目录
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用入口文件
│   │
│   ├── api/                      # API 路由模块
│   │   ├── __init__.py
│   │   ├── health.py             # 健康检查接口
│   │   └── game.py               # 游戏相关接口（创建游戏、房间管理等）
│   │
│   ├── core/                     # 核心配置模块
│   │   ├── __init__.py
│   │   ├── config.py             # 应用配置管理（数据库、Redis、JWT等）
│   │   └── security.py           # 安全相关（密码加密、JWT令牌生成）
│   │
│   ├── db/                       # 数据库相关
│   │   ├── __init__.py
│   │   ├── session.py            # SQLAlchemy 数据库会话管理
│   │   └── redis_client.py       # Redis 客户端封装
│   │
│   ├── models/                   # 数据库模型
│   │   ├── __init__.py
│   │   ├── user.py               # 用户模型
│   │   └── game.py               # 游戏记录模型
│   │
│   ├── schemas/                  # Pydantic 数据验证模型
│   │   ├── __init__.py
│   │   ├── user.py               # 用户相关数据结构
│   │   └── game.py               # 游戏相关数据结构
│   │
│   ├── services/                 # 业务逻辑服务层（预留）
│   │   └── __init__.py
│   │
│   ├── game/                     # 游戏核心逻辑
│   │   ├── __init__.py
│   │   ├── dice.py               # 骰子管理类
│   │   ├── scoring.py            # 计分规则计算器
│   │   └── game_manager.py       # 游戏状态管理器
│   │
│   └── websocket/                # WebSocket 模块
│       ├── __init__.py
│       └── manager.py            # WebSocket 连接管理器
│
├── tests/                        # 测试目录（预留）
│   └── __init__.py
│
├── scripts/                      # 脚本目录（预留，如数据库迁移脚本）
│
├── logs/                         # 日志目录（预留）
│
├── requirements.txt              # Python 依赖包列表
├── PROJECT_STRUCTURE.md          # 本文档 - 项目结构说明
└── README.md                     # 项目说明文档
```

---

## 目录详细说明

### 1. `app/` - 主应用目录

#### `app/main.py`
- FastAPI 应用的入口文件
- 配置 CORS 中间件
- 注册 API 路由
- 启动服务器的入口点

#### `app/api/` - API 路由层
- `health.py`: 健康检查接口，用于监控服务状态
- `game.py`: 游戏相关的所有 API 接口：
  - 创建游戏
  - 获取游戏状态
  - 掷骰子
  - 提交分数
  - 创建/加入房间
  - WebSocket 连接端点

#### `app/core/` - 核心配置层
- `config.py`: 使用 Pydantic Settings 管理配置
  - 项目基本信息
  - 数据库连接配置（MySQL）
  - Redis 连接配置
  - JWT 安全配置
- `security.py`: 安全工具
  - 密码哈希验证
  - JWT 令牌生成

#### `app/db/` - 数据库层
- `session.py`: SQLAlchemy 数据库会话管理
  - 数据库引擎配置
  - SessionLocal 工厂
  - get_db 依赖注入函数
- `redis_client.py`: Redis 客户端单例封装
  - 基础的 set/get/delete 操作
  - Hash 结构操作
  - 过期时间设置

#### `app/models/` - 数据库 ORM 模型
- `user.py`: 用户表模型
  - id, username, nickname, email
  - hashed_password, avatar
  - is_active, created_at, updated_at
- `game.py`: 游戏记录表模型
  - game_id, game_mode
  - players, scores, winner
  - status, created_at, finished_at

#### `app/schemas/` - Pydantic 数据验证模型
- `user.py`: 用户相关的数据结构
  - UserBase, UserCreate, UserLogin
  - User（响应模型）, UserInDB
- `game.py`: 游戏相关的数据结构
  - 枚举：GameMode, RoomStatus
  - 请求模型：DiceRollRequest, ScoreSubmitRequest, CreateRoomRequest, JoinRoomRequest
  - 响应模型：RoomResponse, GameStateResponse, GameRecordResponse

#### `app/game/` - 游戏核心逻辑
- `dice.py`: DiceManager 类
  - 管理5个骰子的状态
  - 掷骰子（支持锁定指定骰子）
  - 重置骰子
- `scoring.py`: ScoreCalculator 类
  - 实现13个计分项的计分规则
  - 上半区加分计算
  - 总分数计算
- `game_manager.py`: GameManager 类
  - Player 类：玩家信息和分数记录
  - Game 类：游戏状态管理
  - 回合控制
  - 游戏流程管理

#### `app/websocket/` - WebSocket 通信
- `manager.py`: ConnectionManager 类
  - 管理房间内的 WebSocket 连接
  - 个人消息发送
  - 房间广播

### 2. `tests/` - 测试目录
- 预留用于存放单元测试和集成测试

### 3. `scripts/` - 脚本目录
- 预留用于存放数据库迁移脚本、初始化脚本等

### 4. `logs/` - 日志目录
- 预留用于存放应用日志文件

### 5. 根目录文件
- `requirements.txt`: 项目依赖列表
- `PROJECT_STRUCTURE.md`: 本文档
- `README.md`: 项目说明和快速开始指南

---

## 核心模块关系图

```
┌─────────────────────────────────────────────────────────┐
│                     FastAPI App (main.py)                │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼─────┐          ┌─────▼──────┐
    │  API     │          │  WebSocket  │
    │  Routes  │          │  Manager    │
    └────┬─────┘          └─────┬──────┘
         │                       │
    ┌────▼───────────────────────▼──────┐
    │           Game Manager             │
    │  (dice.py + scoring.py)            │
    └────┬───────────────────────────────┘
         │
    ┌────▼─────┐          ┌─────▼──────┐
    │  MySQL   │          │   Redis     │
    │  (User/  │          │  (Cache)    │
    │  Game)   │          │             │
    └──────────┘          └─────────────┘
```

---

## 技术栈说明

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.109.0 | Web 框架 |
| Uvicorn | 0.27.0 | ASGI 服务器 |
| SQLAlchemy | 2.0.25 | ORM 框架 |
| PyMySQL | 1.1.0 | MySQL 驱动 |
| Redis | 5.0.1 | Redis 客户端 |
| Pydantic | 2.5.3 | 数据验证 |
| websockets | 12.0 | WebSocket 支持 |

---

## 后续开发建议

1. **数据库迁移**：集成 Alembic 进行数据库版本管理
2. **用户认证**：完善 JWT 认证中间件
3. **游戏记录持久化**：将游戏记录保存到 MySQL
4. **AI 玩家**：实现人机对战的 AI 逻辑
5. **日志系统**：集成日志记录框架
6. **单元测试**：添加 pytest 测试用例
7. **Docker 支持**：添加 Dockerfile 和 docker-compose.yml
