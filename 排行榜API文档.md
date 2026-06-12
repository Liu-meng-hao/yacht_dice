# 排行榜 API 文档

## 基础信息

- **Base URL**: `/api/v1/leaderboard`
- **认证方式**: 
  - 查询接口（GET）：无需认证
  - 管理接口（POST）：需要 Bearer Token 认证
    - 请求头格式：`Authorization: Bearer YOUR_TOKEN`
- **响应格式**: JSON

---

## 认证说明

### 需要认证的接口

以下接口必须在请求头中携带有效的 Bearer Token：
- `POST /add-experience`
- `POST /update-win-streak`
- `POST /game-settle`

### 认证请求头示例

```http
POST /api/v1/leaderboard/add-experience HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 未认证响应示例

```json
{
  "code": 401,
  "msg": "Not authenticated",
  "data": null
}
```

或

```json
{
  "code": 401,
  "msg": "无效的令牌",
  "data": null
}
```

---

## 通用响应格式

所有接口统一返回以下格式：

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {}
}
```

### 状态码说明

| code | 说明 |
|------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未登录或 Token 无效 |
| 404 | 资源不存在 |

---

## 枚举值说明

### 游戏模式 (game_mode)

| 值 | 说明 | 系数 |
|----|------|------|
| 1 | 本地模式 | 1.0 |
| 2 | 人机对战 | 1.2 |
| 3 | 联机对战 | 1.5 |

### 游戏状态 (game_status)

| 值 | 说明 |
|----|------|
| 1 | 准备中 |
| 2 | 进行中 |
| 3 | 已结束 |
| 4 | 已退出 |

### 安全限制

| 限制项 | 值 | 说明 |
|--------|-----|------|
| MAX_EXPERIENCE | 1,000,000,000 | 最大经验值 |
| MAX_WIN_STREAK | 1,000 | 最大连胜数 |
| MIN_PLAYERS | 2 | 最少玩家数 |
| MAX_PLAYERS | 4 | 最多玩家数 |

---

## 接口列表

### 1. 获取单局历史最高得分排行榜

**接口**：`GET /highest-score`

**说明**：获取玩家单局游戏最高分排行榜，包含 Redis 缓存（5分钟）

**请求参数**：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| limit | int | 否 | 10 | 返回数量，范围 1-100 |

**响应示例**：

```json
{
  "code": 200,
  "msg": "获取排行榜成功",
  "data": {
    "leaderboard": [
      {
        "rank": 1,
        "user_id": 1,
        "nickname": "玩家A",
        "avatar": "https://example.com/avatar.jpg",
        "score": 250,
        "achieve_time": "2024-01-15T10:30:00"
      },
      {
        "rank": 2,
        "user_id": 2,
        "nickname": "玩家B",
        "avatar": null,
        "score": 220,
        "achieve_time": "2024-01-14T15:20:00"
      }
    ],
    "total_count": 100
  }
}
```

**响应字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| data.leaderboard | array | 排行榜列表 |
| data.leaderboard[].rank | int | 排名 |
| data.leaderboard[].user_id | int | 用户ID |
| data.leaderboard[].nickname | string\|null | 昵称 |
| data.leaderboard[].avatar | string\|null | 头像URL |
| data.leaderboard[].score | int | 最高得分 |
| data.leaderboard[].achieve_time | string\|null | 达成时间（ISO格式） |
| data.total_count | int | 总玩家数 |

---

### 2. 获取经验值排行榜

**接口**：`GET /experience`

**说明**：获取玩家经验值排行榜，包含 Redis 缓存（5分钟）

**请求参数**：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| limit | int | 否 | 10 | 返回数量，范围 1-100 |

**响应示例**：

```json
{
  "code": 200,
  "msg": "获取排行榜成功",
  "data": {
    "leaderboard": [
      {
        "rank": 1,
        "user_id": 1,
        "nickname": "玩家A",
        "avatar": "https://example.com/avatar.jpg",
        "experience": 10000,
        "achieve_time": "2024-01-15T10:30:00"
      }
    ],
    "total_count": 100
  }
}
```

**响应字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| data.leaderboard | array | 排行榜列表 |
| data.leaderboard[].rank | int | 排名 |
| data.leaderboard[].user_id | int | 用户ID |
| data.leaderboard[].nickname | string\|null | 昵称 |
| data.leaderboard[].avatar | string\|null | 头像URL |
| data.leaderboard[].experience | int | 总经验值 |
| data.leaderboard[].achieve_time | string\|null | 最后游戏时间（ISO格式） |
| data.total_count | int | 总玩家数 |

---

### 3. 获取连胜排行榜

**接口**：`GET /win-streak`

**说明**：获取玩家连胜排行榜，包含 Redis 缓存（5分钟）

**请求参数**：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| limit | int | 否 | 10 | 返回数量，范围 1-100 |

**响应示例**：

```json
{
  "code": 200,
  "msg": "获取排行榜成功",
  "data": {
    "leaderboard": [
      {
        "rank": 1,
        "user_id": 1,
        "nickname": "玩家A",
        "avatar": "https://example.com/avatar.jpg",
        "streak": 10,
        "achieve_time": "2024-01-15T10:30:00"
      }
    ],
    "total_count": 100
  }
}
```

**响应字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| data.leaderboard | array | 排行榜列表 |
| data.leaderboard[].rank | int | 排名 |
| data.leaderboard[].user_id | int | 用户ID |
| data.leaderboard[].nickname | string\|null | 昵称 |
| data.leaderboard[].avatar | string\|null | 头像URL |
| data.leaderboard[].streak | int | 最高连胜数 |
| data.leaderboard[].achieve_time | string\|null | 最高连胜达成时间（ISO格式） |
| data.total_count | int | 总玩家数 |

---

### 4. 获取总对局次数排行榜

**接口**：`GET /ranking-games`

**说明**：获取按照有效总对局次数（人机/联机）降序排列的排行榜，包含 Redis 缓存（5分钟）

**请求参数**：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| limit | int | 否 | 10 | 返回数量，范围 1-100 |

**响应示例**：

```json
{
  "code": 200,
  "msg": "获取排行榜成功",
  "data": {
    "leaderboard": [
      {
        "rank": 1,
        "user_id": 1,
        "nickname": "玩家A",
        "avatar": "https://example.com/avatar.jpg",
        "total_games": 50,
        "last_play_time": "2024-01-15T10:30:00"
      }
    ],
    "total_count": 100
  }
}
```

**响应字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| data.leaderboard | array | 排行榜列表 |
| data.leaderboard[].rank | int | 排名 |
| data.leaderboard[].user_id | int | 用户ID |
| data.leaderboard[].nickname | string\|null | 昵称 |
| data.leaderboard[].avatar | string\|null | 头像URL |
| data.leaderboard[].total_games | int | 有效总对局数 |
| data.leaderboard[].last_play_time | string\|null | 最后游戏时间（ISO格式） |
| data.total_count | int | 总玩家数 |

---

### 5. 获取胜率排行榜

**接口**：`GET /win-rate`

**说明**：获取胜率排行榜（要求总对局数 >= 10，仅统计非本地模式），包含 Redis 缓存（5分钟）

**请求参数**：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| limit | int | 否 | 10 | 返回数量，范围 1-100 |

**响应示例**：

```json
{
  "code": 200,
  "msg": "获取排行榜成功",
  "data": {
    "leaderboard": [
      {
        "rank": 1,
        "user_id": 1,
        "nickname": "玩家A",
        "avatar": "https://example.com/avatar.jpg",
        "total_games": 50,
        "total_wins": 40,
        "win_rate": 80.0,
        "last_play_time": "2024-01-15T10:30:00"
      }
    ],
    "total_count": 80
  }
}
```

**响应字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| data.leaderboard | array | 排行榜列表 |
| data.leaderboard[].rank | int | 排名 |
| data.leaderboard[].user_id | int | 用户ID |
| data.leaderboard[].nickname | string\|null | 昵称 |
| data.leaderboard[].avatar | string\|null | 头像URL |
| data.leaderboard[].total_games | int | 有效总对局数 |
| data.leaderboard[].total_wins | int | 有效总胜场数 |
| data.leaderboard[].win_rate | float | 胜率百分比 |
| data.leaderboard[].last_play_time | string\|null | 最后游戏时间（ISO格式） |
| data.total_count | int | 符合条件的玩家总数 |

---

### 6. 增加玩家经验值

**接口**：`POST /add-experience`

**说明**：根据计分项或直接指定增加玩家经验值

**认证要求**：需要 Token 认证

**请求参数**：

```json
{
  "user_id": 1,
  "score_item_id": 10,
  "experience_value": 100
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | int | 是 | 玩家ID |
| score_item_id | int | 否 | 计分项ID（二选一） |
| experience_value | int | 否 | 直接指定要增加的经验值（二选一） |

**注意**：`score_item_id` 和 `experience_value` 必须提供其中一个

**响应示例**：

```json
{
  "code": 200,
  "msg": "经验值增加成功",
  "data": {
    "user_id": 1,
    "added_experience": 100,
    "total_experience": 10100
  }
}
```

**错误示例**：

```json
{
  "code": 400,
  "msg": "经验值不能为负数",
  "data": null
}
```

```json
{
  "code": 404,
  "msg": "用户不存在",
  "data": null
}
```

```json
{
  "code": 400,
  "msg": "必须提供score_item_id或experience_value",
  "data": null
}
```

```json
{
  "code": 401,
  "msg": "Not authenticated",
  "data": null
}
```

---

### 7. 更新玩家连胜状态

**接口**：`POST /update-win-streak`

**说明**：游戏结束时更新玩家的连胜状态

**认证要求**：需要 Token 认证

**请求参数**：

```json
{
  "user_id": 1,
  "is_win": true
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | int | 是 | 玩家ID |
| is_win | bool | 是 | 是否胜利 |

**响应示例**：

```json
{
  "code": 200,
  "msg": "连胜状态更新成功",
  "data": {
    "user_id": 1,
    "is_win": true,
    "current_win_streak": 5,
    "max_win_streak": 10
  }
}
```

**错误示例**：

```json
{
  "code": 404,
  "msg": "用户不存在",
  "data": null
}
```

```json
{
  "code": 401,
  "msg": "Not authenticated",
  "data": null
}
```

---

### 8. 更新总对局次数

**接口**：`POST /update-games`

**说明**：游戏结束时，更新胜利玩家的 total_games 字段和 last_play_time（排除本地模式）

**认证要求**：需要 Token 认证

**请求参数**：

```json
{
  "winner_id": 1,
  "game_mode": "online",
  "last_play_time": "2024-01-15T10:30:00"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| winner_id | int | 是 | 胜利玩家ID |
| game_mode | string | 是 | 游戏模式：local（本地）、ai（AI对战）、online（联机对战） |
| last_play_time | string | 否 | 最后获胜时间（ISO格式字符串） |

**响应示例**：

```json
{
  "code": 200,
  "msg": "总对局次数更新成功",
  "data": {
    "user_id": 1,
    "total_games": 51,
    "last_play_time": "2024-01-15T10:30:00",
    "message": "总对局次数更新成功"
  }
}
```

---

### 9. 游戏结束结算

**接口**：`POST /game-settle`

**说明**：游戏结束时统一结算所有玩家经验和连胜

**认证要求**：需要 Token 认证

**请求参数**：

```json
{
  "game_id": 1001,
  "game_mode": 3,
  "players": [
    {
      "user_id": 1,
      "rank": 1,
      "total_score": 250
    },
    {
      "user_id": 2,
      "rank": 2,
      "total_score": 200
    }
  ]
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| game_id | int | 是 | 游戏ID |
| game_mode | int | 是 | 游戏模式（1-本地，2-人机，3-联机） |
| players | array | 是 | 所有玩家结算信息列表 |
| players[].user_id | int | 是 | 玩家ID |
| players[].rank | int | 是 | 排名，从1开始 |
| players[].total_score | int | 是 | 总得分 |

**前置验证**：
1. 游戏必须存在且未删除
2. 游戏状态必须是"已结束"（game_status == 3）
3. 请求的 game_mode 必须与数据库一致
4. 玩家数必须在 2-4 之间
5. 所有玩家必须真的参与了该游戏
6. rank 必须在合法范围内且不重复

**经验值计算公式**：

```
额外经验 = (排名奖励 + 得分加成) × (1 + 连胜加成) × 模式系数
```

**排名奖励表**：

| 玩家数 | 第1名 | 第2名 | 第3名 | 第4名 |
|--------|-------|-------|-------|-------|
| 2人 | 30 | 10 | - | - |
| 3人 | 50 | 25 | 10 | - |
| 4人 | 80 | 40 | 20 | 10 |

**其他加成**：
- 得分加成：每 10 分 + 1 经验
- 连胜加成：连胜数 × 5%，最多 50%
- 本地模式：所有额外奖励为 0

**响应示例**：

```json
{
  "code": 200,
  "msg": "游戏结算成功",
  "data": {
    "game_id": 1001,
    "results": [
      {
        "user_id": 1,
        "rank": 1,
        "base_experience": 0,
        "rank_reward": 30,
        "score_bonus": 25,
        "streak_bonus": 0.2,
        "mode_multiplier": 1.5,
        "total_experience": 99,
        "old_experience": 10000,
        "new_experience": 10099,
        "win_streak_updated": true,
        "old_streak": 4,
        "new_streak": 5
      },
      {
        "user_id": 2,
        "rank": 2,
        "base_experience": 0,
        "rank_reward": 10,
        "score_bonus": 20,
        "streak_bonus": 0,
        "mode_multiplier": 1.5,
        "total_experience": 45,
        "old_experience": 5000,
        "new_experience": 5045,
        "win_streak_updated": true,
        "old_streak": 3,
        "new_streak": 0
      }
    ]
  }
}
```

**响应字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| data.game_id | int | 游戏ID |
| data.results | array | 各玩家结算结果 |
| data.results[].user_id | int | 玩家ID |
| data.results[].rank | int | 排名 |
| data.results[].base_experience | int | 基础经验（预留字段，当前为0） |
| data.results[].rank_reward | int | 排名奖励 |
| data.results[].score_bonus | int | 得分加成 |
| data.results[].streak_bonus | float | 连胜加成系数 |
| data.results[].mode_multiplier | float | 模式系数 |
| data.results[].total_experience | int | 本次获得总经验 |
| data.results[].old_experience | int | 结算前经验值 |
| data.results[].new_experience | int | 结算后经验值 |
| data.results[].win_streak_updated | bool | 连胜是否已更新 |
| data.results[].old_streak | int | 结算前连胜数 |
| data.results[].new_streak | int | 结算后连胜数 |

**错误示例**：

```json
{
  "code": 400,
  "msg": "玩家数必须在 2-4 之间",
  "data": null
}
```

```json
{
  "code": 404,
  "msg": "游戏不存在",
  "data": null
}
```

```json
{
  "code": 400,
  "msg": "游戏未结束，无法结算",
  "data": null
}
```

```json
{
  "code": 400,
  "msg": "rank 必须在 1-2 之间",
  "data": null
}
```

```json
{
  "code": 400,
  "msg": "rank 不能重复",
  "data": null
}
```

```json
{
  "code": 400,
  "msg": "玩家 3 未参与该游戏",
  "data": null
}
```

```json
{
  "code": 401,
  "msg": "Not authenticated",
  "data": null
}
```

---

## 附录：完整的排行榜数据模型

### HighestScoreItem（单局最高分排行项）

```typescript
{
  rank: number;
  user_id: number;
  nickname?: string;
  avatar?: string;
  score: number;
  achieve_time?: string; // ISO格式时间
}
```

### ExperienceItem（经验值排行项）

```typescript
{
  rank: number;
  user_id: number;
  nickname?: string;
  avatar?: string;
  experience: number;
  achieve_time?: string; // ISO格式时间
}
```

### WinStreakItem（连胜排行项）

```typescript
{
  rank: number;
  user_id: number;
  nickname?: string;
  avatar?: string;
  streak: number;
  achieve_time?: string; // ISO格式时间
}
```

### TotalGamesLeaderboardItem（总对局数排行项）

```typescript
{
  rank: number;
  user_id: number;
  nickname?: string;
  avatar?: string;
  total_games: number;
  last_play_time?: string; // ISO格式时间
}
```

### WinRateItem（胜率排行项）

```typescript
{
  rank: number;
  user_id: number;
  nickname?: string;
  avatar?: string;
  total_games: number;
  total_wins: number;
  win_rate: number;
  last_play_time?: string; // ISO格式时间
}
```

### GameSettlePlayerResult（玩家结算结果）

```typescript
{
  user_id: number;
  rank: number;
  base_experience: number;
  rank_reward: number;
  score_bonus: number;
  streak_bonus: number;
  mode_multiplier: number;
  total_experience: number;
  old_experience: number;
  new_experience: number;
  win_streak_updated: boolean;
  old_streak: number;
  new_streak: number;
}
```

---

## 使用示例

### JavaScript/TypeScript 示例

```typescript
// 1. 获取经验值排行榜
async function getExperienceLeaderboard(limit = 10) {
  const response = await fetch(`/api/v1/leaderboard/experience?limit=${limit}`);
  return await response.json();
}

// 2. 游戏结算
async function gameSettle(gameId: number, gameMode: number, players: any[]) {
  const response = await fetch('/api/v1/leaderboard/game-settle', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      game_id: gameId,
      game_mode: gameMode,
      players: players
    })
  });
  return await response.json();
}
```

### curl 示例

```bash
# 获取经验排行榜
curl -X GET "http://localhost:8000/api/v1/leaderboard/experience?limit=10"

# 游戏结算（需要Token）
curl -X POST "http://localhost:8000/api/v1/leaderboard/game-settle" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "game_id": 1001,
    "game_mode": 3,
    "players": [
      {"user_id": 1, "rank": 1, "total_score": 250},
      {"user_id": 2, "rank": 2, "total_score": 200}
    ]
  }'
```

---

## 注意事项

1. **缓存机制**：三个查询接口都有 5 分钟的 Redis 缓存，数据更新不会立即反映在排行榜上
2. **幂等性**：game-settle 接口没有幂等性保护，请勿重复调用
3. **本地模式**：本地模式游戏结算不会获得任何经验奖励，也不会更新连胜
4. **上限限制**：经验值和连胜数都有上限，达到上限后不再增加
5. **玩家范围**：排行榜只统计真实玩家（user_type == 1），不包含 AI

---

## 文档更新日志

| 日期 | 更新内容 |
|------|----------|
| 2026-06-11 | 添加了完整的认证说明，包括：<br>• 详细的认证方式说明<br>• 认证请求头示例<br>• 在所有管理接口添加了 401 错误示例 |
