"""
测试所有排行榜接口
"""

import sys
import os
import urllib.request
import urllib.parse
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1/leaderboard"


def test_highest_score():
    """测试单局最高分排行榜"""
    print("\n" + "="*60)
    print("测试 1: 单局历史最高得分排行榜")
    print("="*60)
    
    url = f"{BASE_URL}{API_PREFIX}/highest-score?limit=5"
    
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                result = data.get('data', {})
                leaderboard = result.get('leaderboard', [])
                
                print(f"\n状态码: {response.status}")
                print(f"总用户数: {result.get('total_count')}")
                print(f"排行榜数据 ({len(leaderboard)} 条):")
                print(f"\n{'Rank':<6}{'User':<15}{'Score':<10}")
                print("-"*60)
                for item in leaderboard:
                    print(f"{item.get('rank', '-'):<6}{item.get('nickname', '-'):<15}{item.get('score', '-'):<10}")
                print("\n✅ 成功!")
                return True
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        return False


def test_experience():
    """测试经验值排行榜"""
    print("\n" + "="*60)
    print("测试 2: 经验值排行榜")
    print("="*60)
    
    url = f"{BASE_URL}{API_PREFIX}/experience?limit=5"
    
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                result = data.get('data', {})
                leaderboard = result.get('leaderboard', [])
                
                print(f"\n状态码: {response.status}")
                print(f"总用户数: {result.get('total_count')}")
                print(f"排行榜数据 ({len(leaderboard)} 条):")
                print(f"\n{'Rank':<6}{'User':<15}{'Experience':<12}")
                print("-"*60)
                for item in leaderboard:
                    print(f"{item.get('rank', '-'):<6}{item.get('nickname', '-'):<15}{item.get('experience', '-'):<12}")
                print("\n✅ 成功!")
                return True
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        return False


def test_win_streak():
    """测试连胜排行榜"""
    print("\n" + "="*60)
    print("测试 3: 连胜排行榜")
    print("="*60)
    
    url = f"{BASE_URL}{API_PREFIX}/win-streak?limit=5"
    
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                result = data.get('data', {})
                leaderboard = result.get('leaderboard', [])
                
                print(f"\n状态码: {response.status}")
                print(f"总用户数: {result.get('total_count')}")
                print(f"排行榜数据 ({len(leaderboard)} 条):")
                print(f"\n{'Rank':<6}{'User':<15}{'Streak':<10}")
                print("-"*60)
                for item in leaderboard:
                    print(f"{item.get('rank', '-'):<6}{item.get('nickname', '-'):<15}{item.get('streak', '-'):<10}")
                print("\n✅ 成功!")
                return True
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        return False


def test_add_experience():
    """测试增加经验值接口"""
    print("\n" + "="*60)
    print("测试 4: 增加经验值接口")
    print("="*60)
    
    # 先获取一个用户ID
    test_user_id = 1
    test_score_item_id = 1
    
    url = f"{BASE_URL}{API_PREFIX}/add-experience?user_id={test_user_id}&score_item_id={test_score_item_id}"
    
    try:
        req = urllib.request.Request(url, method='POST')
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                
                print(f"\n状态码: {response.status}")
                result = data.get('data', {})
                print(f"用户ID: {result.get('user_id')}")
                print(f"增加经验值: {result.get('added_experience')}")
                print(f"总经验值: {result.get('total_experience')}")
                print("\n✅ 成功!")
                return True
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        return False


def test_update_win_streak():
    """测试更新连胜状态接口"""
    print("\n" + "="*60)
    print("测试 5: 更新连胜状态接口")
    print("="*60)
    
    test_user_id = 1
    is_win = True
    
    url = f"{BASE_URL}{API_PREFIX}/update-win-streak?user_id={test_user_id}&is_win={is_win}"
    
    try:
        req = urllib.request.Request(url, method='POST')
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                
                print(f"\n状态码: {response.status}")
                result = data.get('data', {})
                print(f"用户ID: {result.get('user_id')}")
                print(f"是否胜利: {result.get('is_win')}")
                print(f"当前连胜: {result.get('current_win_streak')}")
                print(f"最大连胜: {result.get('max_win_streak')}")
                print("\n✅ 成功!")
                return True
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("开始测试所有排行榜接口")
    print("="*60)
    
    tests = [
        test_highest_score,
        test_experience,
        test_win_streak,
        test_add_experience,
        test_update_win_streak
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        if test_func():
            passed += 1
        else:
            failed += 1
    
    print("\n" + "="*60)
    print(f"测试完成: {passed} 个成功, {failed} 个失败")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
