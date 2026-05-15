# 快艇骰子游戏 - API 接口设计文档

> **注意**：本文档仅为接口设计，暂不修改代码。

---

## 📋 目录

- [一、接口模块划分](#一接口模块划分)
- [二、各模块接口详情](#二各模块接口详情)
- [三、WebSocket 实时通信](#三websocket-实时通信)
- [四、接口设计总结](#四接口设计总结)

---

## 一、接口模块划分

### 模块划分原则

根据项目的5个主要面板，将接口划分为以下模块：

| 模块 | 对应面板 | 说明 |
|------|---------|------|
| **首页模块** | 模式选择首页 | 规则查看、音效设置等 |
| **房间模块** | 联机房间页面 | 房间创建、加入、管理等 |
| **游戏模块** | 游戏对局页面 | 游戏创建、骰子操作、回合控制等 |
| **计分模块** | 计分展示面板 | 分数计算、历史记录等 |
| **结算模块** | 对局结算页面 | 结算信息、再来一局等 |

---

## 二、各模块接口详情

---

### 1. 首页模块 (Home)

**前缀：** `/api/v1/home`

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 获取游戏规则 | GET | `/rules` | 获取快艇骰子游戏规则说明 |
| 获取音效设置 | GET | `/settings/sound` | 获取当前音效开关状态 |
| 保存音效设置 | PUT | `/settings/sound` | 保存音效开关状态 |

---

#### 1.1 获取游戏规则

**接口：** `GET /api/v1/home/rules`

**请求参数：** 无

**响应示例：**
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "rules": "快艇骰子游戏规则...",
    "categories": [
      {
        "name": "ones",
        "description": "一点",
        "score": null
      }
    ]
  }
}
```

---

#### 1.2 获取音效设置

**接口：** `GET /api/v1/home/settings/sound`

**请求参数：** 无

**响应示例：**
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "sound_enabled": true
  }
}
```

---

#### 1.3 保存音效设置

**接口：** `PUT /api/v1/home/settings/sound`

**请求参数：**
```json
{
  "sound_enabled": true
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "保存成功",
  "data": {
    "sound_enabled": true
  }
}
```

---

### 2. 房间模块 (Room)

**前缀：** `/api/v1/room`

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 创建房间 | POST | `/create` | 创建新的联机房间 |
| 加入房间 | POST | `/join` | 加入指定房间 |
| 离开房间 | POST | `/leave` | 离开当前房间 |
| 获取房间信息 | GET | `/{room_code}` | 获取指定房间的详细信息 |
| 获取房间列表 | GET | `/list` | 获取所有等待中的房间列表（可选） |
| 房主开始游戏 | POST | `/{room_code}/start` | 房主开始游戏 |
| 房主解散房间 | DELETE | `/{room_code}` | 房主解散房间 |

---

#### 2.1 创建房间

**接口：** `POST /api/v1/room/create`

**请求参数：**
```json
{
  "player_name": "玩家1",
  "room_name": "我的房间",
  "max_players": 4,
  "game_mode": "online"
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "房间创建成功",
  "data": {
    "room_code": "ABC123",
    "room_name": "我的房间",
    "max_players": 4,
    "players": [
      {
        "player_id": "xxx",
        "name": "玩家1",
        "is_host": true
      }
    ],
    "status": "waiting",
    "host_id": "xxx"
  }
}
```

---

#### 2.2 加入房间

**接口：** `POST /api/v1/room/join`

**请求参数：**
```json
{
  "room_code": "ABC123",
  "player_name": "玩家2"
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "加入房间成功",
  "data": {
    "room": { ... },
    "player_id": "yyy"
  }
}
```

---

#### 2.3 离开房间

**接口：** `POST /api/v1/room/leave`

**请求参数：**
```json
{
  "room_code": "ABC123",
  "player_id": "yyy"
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "离开房间成功",
  "data": null
}
```

---

#### 2.4 获取房间信息

**接口：** `GET /api/v1/room/{room_code}`

**请求参数：** 无（路径参数 room_code）

**响应示例：**
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "room_code": "ABC123",
    "room_name": "我的房间",
    "max_players": 4,
    "players": [ ... ],
    "status": "waiting",
    "host_id": "xxx"
  }
}
```

---

#### 2.5 获取房间列表（可选）

**接口：** `GET /api/v1/room/list`

**请求参数：** 无

**响应示例：**
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "rooms": [
      {
        "room_code": "ABC123",
        "room_name": "我的房间",
        "player_count": 2,
        "max_players": 4,
        "status": "waiting"
      }
    ]
  }
}
```

---

#### 2.6 房主开始游戏

**接口：** `POST /api/v1/room/{room_code}/start`

**请求参数：**
```json
{
  "player_id": "xxx"
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "游戏开始",
  "data": {
    "game_id": "zzz",
    "room_code": "ABC123"
  }
}
```

---

#### 2.7 房主解散房间

**接口：** `DELETE /api/v1/room/{room_code}`

**请求参数：**
```json
{
  "player_id": "xxx"
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "房间已解散",
  "data": null
}
```

---

### 3. 游戏模块 (Game)

**前缀：** `/api/v1/game`

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 创建游戏 | POST | `/create` | 创建新的游戏对局 |
| 获取游戏状态 | GET | `/{game_id}` | 获取游戏当前状态 |
| 掷骰子 | POST | `/{game_id}/roll` | 掷骰子（可选锁定部分骰子） |
| 重置骰子 | POST | `/{game_id}/dice/reset` | 重置所有骰子（解锁） |
| 切换骰子锁定 | POST | `/{game_id}/dice/toggle` | 切换指定骰子的锁定状态 |
| 提交分数 | POST | `/{game_id}/score` | 提交分数到指定计分项 |
| 退出游戏 | POST | `/{game_id}/quit` | 中途退出游戏 |

---

#### 3.1 创建游戏

**接口：** `POST /api/v1/game/create`

**请求参数：**
```json
{
  "game_mode": "local",
  "player_names": ["玩家1", "玩家2"]
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "游戏创建成功",
  "data": {
    "game_id": "zzz",
    "game_mode": "local",
    "current_player": "xxx",
    "players": [ ... ],
    "dice": [1, 1, 1, 1, 1],
    "rolls_left": 3,
    "status": "playing"
  }
}
```

---

#### 3.2 获取游戏状态

**接口：** `GET /api/v1/game/{game_id}`

**请求参数：** 无（路径参数 game_id）

**响应示例：**
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "game_id": "zzz",
    "game_mode": "local",
    "current_player": "xxx",
    "players": [ ... ],
    "dice": [1, 2, 3, 4, 5],
    "dice_locked": [false, false, false, false, false],
    "rolls_left": 2,
    "status": "playing"
  }
}
```

---

#### 3.3 掷骰子

**接口：** `POST /api/v1/game/{game_id}/roll`

**请求参数：**
```json
{
  "player_id": "xxx",
  "locked_dice": [0, 2]
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "掷骰子成功",
  "data": {
    "dice": [1, 5, 3, 6, 2],
    "dice_locked": [true, false, true, false, false],
    "rolls_left": 1
  }
}
```

---

#### 3.4 重置骰子（解锁所有）

**接口：** `POST /api/v1/game/{game_id}/dice/reset`

**请求参数：**
```json
{
  "player_id": "xxx"
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "骰子已重置",
  "data": {
    "dice": [1, 2, 3, 4, 5],
    "dice_locked": [false, false, false, false, false],
    "rolls_left": 3
  }
}
```

---

#### 3.5 切换骰子锁定状态

**接口：** `POST /api/v1/game/{game_id}/dice/toggle`

**请求参数：**
```json
{
  "player_id": "xxx",
  "dice_index": 2
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "切换成功",
  "data": {
    "dice_locked": [false, false, true, false, false]
  }
}
```

---

#### 3.6 提交分数

**接口：** `POST /api/v1/game/{game_id}/score`

**请求参数：**
```json
{
  "player_id": "xxx",
  "category": "ones"
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "分数提交成功",
  "data": {
    "category": "ones",
    "score": 3,
    "game_state": { ... },
    "next_player": "yyy",
    "is_game_finished": false
  }
}
```

---

#### 3.7 退出游戏

**接口：** `POST /api/v1/game/{game_id}/quit`

**请求参数：**
```json
{
  "player_id": "xxx"
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "已退出游戏",
  "data": null
}
```

---

### 4. 计分模块 (Score)

**前缀：** `/api/v1/score`

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 获取可能得分 | GET | `/possible/{game_id}` | 计算当前骰子在所有计分项的可能得分 |
| 获取历史记录 | GET | `/history` | 获取当前玩家的历史游戏记录 |
| 获取排行榜 | GET | `/leaderboard` | 获取排行榜（可选） |

---

#### 4.1 获取可能得分

**接口：** `GET /api/v1/score/possible/{game_id}`

**请求参数：** 无（路径参数 game_id）

**响应示例：**
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "possible_scores": {
      "ones": 3,
      "twos": 0,
      "threes": 3,
      "fours": 4,
      "fives": 0,
      "sixes": 0,
      "threeOfAKind": 10,
      "fourOfAKind": null,
      "fullHouse": null,
      "smallStraight": null,
      "largeStraight": null,
      "yahtzee": null,
      "chance": 10
    }
  }
}
```

---

#### 4.2 获取历史记录

**接口：** `GET /api/v1/score/history`

**请求参数：**
```json
{
  "player_id": "xxx",
  "limit": 10
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "history": [
      {
        "game_id": "zzz",
        "game_mode": "local",
        "played_at": "2026-05-14T10:00:00",
        "players": [ ... ],
        "winner": "玩家1",
        "final_scores": { ... }
      }
    ]
  }
}
```

---

#### 4.3 获取排行榜（可选）

**接口：** `GET /api/v1/score/leaderboard`

**请求参数：** 无

**响应示例：**
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "leaderboard": [
      {
        "rank": 1,
        "player_name": "玩家1",
        "total_games": 10,
        "wins": 8,
        "best_score": 350
      }
    ]
  }
}
```

---

### 5. 结算模块 (Settlement)

**前缀：** `/api/v1/settlement`

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 获取结算信息 | GET | `/{game_id}` | 获取游戏结算信息 |
| 再来一局 | POST | `/{game_id}/rematch` | 开始新一局游戏 |
| 返回首页 | POST | `/{game_id}/back` | 返回模式选择首页 |

---

#### 5.1 获取结算信息

**接口：** `GET /api/v1/settlement/{game_id}`

**请求参数：** 无（路径参数 game_id）

**响应示例：**
```json
{
  "code": 200,
  "msg": "获取成功",
  "data": {
    "game_id": "zzz",
    "finished_at": "2026-05-14T10:30:00",
    "players": [
      {
        "player_id": "xxx",
        "name": "玩家1",
        "final_score": 280,
        "rank": 1,
        "is_winner": true,
        "scores": { ... }
      },
      {
        "player_id": "yyy",
        "name": "玩家2",
        "final_score": 220,
        "rank": 2,
        "is_winner": false,
        "scores": { ... }
      }
    ]
  }
}
```

---

#### 5.2 再来一局

**接口：** `POST /api/v1/settlement/{game_id}/rematch`

**请求参数：**
```json
{
  "player_id": "xxx"
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "新游戏已创建",
  "data": {
    "new_game_id": "aaa",
    "game_state": { ... }
  }
}
```

---

#### 5.3 返回首页

**接口：** `POST /api/v1/settlement/{game_id}/back`

**请求参数：**
```json
{
  "player_id": "xxx"
}
```

**响应示例：**
```json
{
  "code": 200,
  "msg": "已返回首页",
  "data": null
}
```

---

## 三、WebSocket 实时通信

### 1. 房间 WebSocket

**连接地址：** `ws://localhost:8000/api/v1/room/ws/{room_code}/{player_id}`

**消息类型：**

| 消息类型 | 发送方 | 说明 |
|---------|--------|------|
| `player_joined` | 系统 | 有新玩家加入房间 |
| `player_left` | 系统 | 有玩家离开房间 |
| `game_started` | 系统 | 房主开始游戏 |
| `room_dissolved` | 系统 | 房间已解散 |
| `chat` | 玩家 | 房间内聊天（可选） |

---

### 2. 游戏 WebSocket

**连接地址：** `ws://localhost:8000/api/v1/game/ws/{game_id}/{player_id}`

**消息类型：**

| 消息类型 | 发送方 | 说明 |
|---------|--------|------|
| `dice_rolled` | 系统 | 骰子已掷出 |
| `score_submitted` | 系统 | 分数已提交 |
| `turn_changed` | 系统 | 回合切换 |
| `game_finished` | 系统 | 游戏结束 |
| `chat` | 玩家 | 游戏内聊天（可选） |

---

## 四、接口设计总结

### 模块对比

| 模块 | 接口数量 | 对应面板 |
|------|---------|---------|
| 首页模块 | 3 | 模式选择首页 |
| 房间模块 | 7 | 联机房间页面 |
| 游戏模块 | 7 | 游戏对局页面 |
| 计分模块 | 3 | 计分展示面板 |
| 结算模块 | 3 | 对局结算页面 |
| **总计** | **23** | - |

---

### 文件结构（设计）

```
app/api/
├── home.py              # 首页模块（新增）
├── room.py              # 房间模块（新增，从 game.py 拆分）
├── game.py              # 游戏模块（调整）
├── score.py             # 计分模块（新增）
├── settlement.py        # 结算模块（新增）
└── health.py            # 健康检查（保持）
```

---

### 下一步

1. 确认接口设计是否合理
2. 如需调整，修改本文档
3. 确认后，再开始修改代码

---

**文档结束**
