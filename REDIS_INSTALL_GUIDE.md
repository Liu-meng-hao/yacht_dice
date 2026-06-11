# Redis 安装与配置指南

## 注意

**好消息！** 现在项目已经支持在没有 Redis 的情况下运行！

- 如果没有安装 Redis，系统会自动使用内存缓存
- 如果安装了 Redis，系统会自动使用 Redis，性能更好
- 两种模式下功能完全一致

---

## Windows 系统安装 Redis

### 方案一：使用 Memurai（推荐）

Memurai 是 Redis 在 Windows 上的官方兼容版本。

1. **下载 Memurai**
   - 访问：https://www.memurai.com/get-memurai
   - 下载 Memurai Developer（免费）

2. **安装**
   - 运行安装程序，按照默认配置安装

3. **启动服务**
   - 安装后会自动作为 Windows 服务运行
   - 或者手动启动：`memurai.exe`

4. **验证安装**
   ```bash
   memurai-cli ping
   # 应该返回：PONG
   ```

### 方案二：使用 Docker（如果你有 Docker）

```bash
# 拉取 Redis 镜像
docker pull redis

# 启动 Redis 容器
docker run -d -p 6379:6379 --name yacht-dice-redis redis
```

### 方案三：使用 WSL2

如果你有 WSL2（Windows Subsystem for Linux）：

```bash
# 进入 WSL
wsl

# 更新包管理器
sudo apt update

# 安装 Redis
sudo apt install redis-server

# 启动 Redis
sudo service redis-server start

# 验证
redis-cli ping
```

---

## 配置项目

安装 Redis 后，确保 `.env` 文件中的配置正确：

```env
# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
```

---

## 验证 Redis 是否工作

启动项目后，查看日志输出：

- 如果看到：`Redis 连接成功，使用 Redis 缓存` ✓
- 如果看到：`Redis 不可用，使用内存缓存`（这也没问题，只是性能稍低）

---

## Redis 带来的好处

1. **更好的性能**：Redis 是专业的缓存数据库
2. **数据持久化**：重启后缓存数据不会丢失
3. **支持多实例**：将来可以扩展到多服务器部署
4. **Pub/Sub 功能**：支持更复杂的实时通信场景

---

## 常见问题

### Q: 我不想安装 Redis，可以吗？
A: 完全可以！系统会自动使用内存缓存，功能完全一样。

### Q: 内存缓存和 Redis 有什么区别？
A: 主要区别：
- 内存缓存：重启后数据丢失，单实例
- Redis：数据持久化，支持多实例

### Q: 我安装了 Redis，但是连不上怎么办？
A: 检查：
1. Redis 是否正在运行
2. 端口 6379 是否被占用
3. `.env` 文件中的配置是否正确

### Q: 如何停止 Redis？
A:
- Windows 服务：在服务管理器中停止
- Docker：`docker stop yacht-dice-redis`
- WSL：`sudo service redis-server stop`
