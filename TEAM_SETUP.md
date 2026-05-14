# 团队开发配置指南

## 📋 目录
1. [Git 配置](#git-配置)
2. [两种开发模式](#两种开发模式)
3. [模式 A：局域网共享数据库](#模式-a局域网共享数据库-推荐)
4. [模式 B：各自本地数据库](#模式-b各自本地数据库)
5. [MySQL 配置远程访问](#mysql-配置远程访问)

---

## Git 配置

### ⚠️ .env 文件规则
- `.env` - 个人本地配置，**不提交**
- `.env.shared` - 共享配置，**可以提交**（如果使用共享数据库）

---

## 两种开发模式

### 模式 A：局域网共享数据库（推荐）
所有人连接同一个数据库（主机电脑上的数据库），数据实时同步。

**优点：**
- 数据实时共享
- 便于联调测试
- 只需要维护一个数据库

### 模式 B：各自本地数据库
每个人使用自己本地的数据库，互不干扰。

**优点：**
- 完全独立，不影响他人
- 不需要配置网络

---

## 模式 A：局域网共享数据库（推荐）

### 🔧 步骤 1：主机配置（数据库所在电脑）

#### 1.1 获取主机局域网 IP
在主机电脑上打开命令行：
```bash
# Windows
ipconfig
# 找到 "IPv4 地址"，例如: 192.168.1.100
```

#### 1.2 配置 MySQL 允许远程访问
**重要！** 需要配置 MySQL 允许局域网访问。

详见：[MySQL 配置远程访问](#mysql-配置远程访问)

#### 1.3 创建共享配置文件
复制模板：
```bash
cp .env.shared.example .env.shared
```

编辑 `.env.shared`，填入主机的局域网 IP：
```env
MYSQL_HOST=192.168.1.100    # 改成主机的实际IP
MYSQL_USER=yacht_user
MYSQL_PASSWORD=团队共享密码
MYSQL_DB=yacht_dice

REDIS_HOST=192.168.1.100    # 如果Redis也在主机上
```

#### 1.4 提交共享配置（可选）
如果团队都使用共享配置，可以提交 `.env.shared`：
```bash
# 先编辑 .gitignore，注释掉 .env.shared
git add .env.shared
git commit -m "添加共享数据库配置"
git push
```

---

### 👥 步骤 2：其他团队成员配置

#### 2.1 克隆项目
```bash
git clone <仓库地址>
cd yacht_dice
```

#### 2.2 安装依赖
```bash
pip install -r requirements.txt
```

#### 2.3 使用共享配置
```bash
# 方式 1：复制 .env.shared 为 .env
cp .env.shared .env

# 方式 2：通过环境变量指定
ENV_FILE=.env.shared python -m app.main
```

#### 2.4 启动项目
```bash
python -m app.main
```

---

## 模式 B：各自本地数据库

### 步骤 1：每个人创建自己的配置
```bash
cp .env.example .env
```

### 步骤 2：编辑 .env
填入自己的本地 MySQL 配置：
```env
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=你自己的密码
MYSQL_DB=yacht_dice
```

### 步骤 3：创建本地数据库
```sql
CREATE DATABASE yacht_dice CHARACTER SET utf8mb4;
```

### 步骤 4：启动项目
```bash
python -m app.main
```

---

## MySQL 配置远程访问

### 📌 在主机电脑上操作

#### 1. 登录 MySQL
```bash
mysql -u root -p
```

#### 2. 创建专用数据库用户（推荐）
```sql
-- 创建用户（允许从任何IP连接）
CREATE USER 'yacht_user'@'%' IDENTIFIED BY 'your_password';

-- 授予权限
GRANT ALL PRIVILEGES ON yacht_dice.* TO 'yacht_user'@'%';

-- 刷新权限
FLUSH PRIVILEGES;
```

#### 3. 或允许 root 用户远程连接（不推荐）
```sql
ALTER USER 'root'@'%' IDENTIFIED WITH mysql_native_password BY '123456';
FLUSH PRIVILEGES;
```

#### 4. 配置 MySQL 绑定地址
编辑 MySQL 配置文件（Windows: `my.ini`）：
```ini
[mysqld]
bind-address = 0.0.0.0
```

#### 5. 重启 MySQL 服务
```bash
net stop MySQL80
net start MySQL80
```

#### 6. 配置防火墙
开放 3306 端口给局域网：
```bash
# Windows 防火墙
netsh advfirewall firewall add rule name="MySQL" dir=in action=allow protocol=TCP localport=3306
```

---

## 验证连接

### 测试数据库连接
```python
python -c "
from app.db.session import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('✅ 数据库连接成功！')
"
```

### 测试 Redis 连接
```python
python -c "
from app.db.redis_client import redis_client
print('✅ Redis 连接成功！' if redis_client.get_client().ping() else '❌ Redis 连接失败')
"
```

---

## 快速参考

| 任务 | 命令 |
|------|------|
| 使用共享配置启动 | `ENV_FILE=.env.shared python -m app.main` |
| 使用本地配置启动 | `python -m app.main` |
| 测试数据库连接 | 见上文 |
| 测试 Redis 连接 | 见上文 |
