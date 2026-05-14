# 项目配置检查清单

## 📋 检查清单

### ✅ 已完成
- [x] 项目目录结构创建
- [x] FastAPI 核心代码
- [x] 游戏逻辑代码
- [x] WebSocket 模块
- [x] requirements.txt 依赖列表
- [x] .env 本地配置
- [x] .env.shared 共享配置
- [x] .gitignore 配置
- [x] 项目文档（README, PROJECT_STRUCTURE, TEAM_SETUP）

---

### ⏳ 待完成（按优先级排序）

#### 🎯 P0 - 必须完成（启动项目前）
- [ ] **MySQL 数据库创建** - 创建 `yacht_dice` 数据库
- [ ] **MySQL 用户创建**（可选但推荐）- 创建 `yacht_user` 用户
- [ ] **启动项目测试** - 运行 `python -m app.main` 测试

#### 🎯 P1 - 团队协作需要
- [ ] **MySQL 远程访问配置** - 允许局域网连接
- [ ] **防火墙配置** - 开放 3306 端口
- [ ] **团队成员连接测试** - 其他电脑测试连接

#### 🎯 P2 - 可选优化
- [ ] Redis 安装与配置
- [ ] Alembic 数据库迁移配置
- [ ] 日志系统配置
- [ ] 单元测试编写

---

## 🔧 快速操作指南

### 1. 创建数据库（MySQL）

```sql
-- 登录 MySQL
mysql -u root -p

-- 创建数据库
CREATE DATABASE yacht_dice CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建专用用户（推荐）
CREATE USER 'yacht_user'@'%' IDENTIFIED BY '123456';
GRANT ALL PRIVILEGES ON yacht_dice.* TO 'yacht_user'@'%';
FLUSH PRIVILEGES;

-- 退出
EXIT;
```

### 2. 测试启动项目

```bash
# 方式 1：使用本地配置
python -m app.main

# 方式 2：使用共享配置
ENV_FILE=.env.shared python -m app.main
```

启动成功后访问：http://localhost:8000/docs

---

## 📊 你的当前配置

### 本地配置 (.env)
```
MYSQL_HOST: localhost
MYSQL_PORT: 3306
MYSQL_USER: root
MYSQL_PASSWORD: 123456
MYSQL_DB: yacht_dice
```

### 共享配置 (.env.shared)
```
MYSQL_HOST: 192.168.21.15
MYSQL_PORT: 3306
MYSQL_USER: yacht_user
MYSQL_PASSWORD: 123456
MYSQL_DB: yacht_dice
```

---

## ❓ 常见问题

### Q: 我只想先测试一下，不配置数据库可以吗？
A: 可以！游戏逻辑不依赖数据库也能运行（存在内存中），直接启动即可。

### Q: 如何确认数据库是否创建成功？
A: 运行以下命令测试：
```python
python -c "
from app.db.session import engine
from sqlalchemy import text
try:
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
        print('✅ 数据库连接成功！')
except Exception as e:
    print(f'❌ 连接失败: {e}')
"
```

### Q: 团队成员如何连接我的数据库？
A: 详见 TEAM_SETUP.md 的 "MySQL 配置远程访问" 章节。
