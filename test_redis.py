"""
测试 Redis 连接和功能
"""
import sys
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


async def test_redis():
    """测试 Redis 连接"""
    print("=" * 60)
    print("测试 Redis 系统")
    print("=" * 60)
    
    # 测试 1: 导入模块
    print("\n1. 导入模块...")
    try:
        from app.db.embedded_redis import start_embedded_redis
        from app.db.redis_client import get_redis_client
        print("   ✅ 模块导入成功")
    except Exception as e:
        print(f"   ❌ 导入失败: {e}")
        return False
    
    # 测试 2: 启动嵌入式 Redis
    print("\n2. 启动嵌入式 Redis...")
    try:
        started = start_embedded_redis()
        if started:
            print("   ✅ 嵌入式 Redis 启动成功")
        else:
            print("   ⚠️  可能已在运行，继续测试")
    except Exception as e:
        print(f"   ❌ 启动失败: {e}")
        return False
    
    # 测试 3: 获取 Redis 客户端
    print("\n3. 连接到 Redis...")
    try:
        redis_client = get_redis_client()
        
        # 同步测试
        sync_redis = redis_client.get_client()
        print("   正在同步 PING...")
        ping_result = sync_redis.ping()
        print(f"   ✅ 同步 PING: {ping_result}")
        
        # 异步测试
        print("\n4. 异步测试...")
        async_redis = redis_client.get_async_client()
        print("   正在异步 PING...")
        await async_redis.ping()
        print("   ✅ 异步 PING 成功")
        
        # 测试 SET/GET
        print("\n5. 测试 SET/GET...")
        await async_redis.set("test_key", "test_value", ex=60)
        value = await async_redis.get("test_key")
        print(f"   ✅ SET/GET: {value}")
        
        # 测试 HSET/HGET
        print("\n6. 测试 HSET/HGET...")
        await async_redis.hset("test_hash", "field1", "value1")
        h_value = await async_redis.hget("test_hash", "field1")
        print(f"   ✅ HSET/HGET: {h_value}")
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！Redis 系统正常！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        import traceback
        print("\n详细错误:")
        print(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = asyncio.run(test_redis())
    sys.exit(0 if success else 1)
