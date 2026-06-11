"""
测试排行榜API接口
"""

import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1/leaderboard"


def test_highest_score():
    """测试单局最高分排行榜接口"""
    print("=" * 60)
    print("测试单局历史最高得分排行榜")
    print("=" * 60)
    
    url = f"{BASE_URL}{API_PREFIX}/highest-score"
    
    print(f"\n请求: GET {url}")
    
    try:
        response = requests.get(url, params={"limit": 5}, timeout=5)
        
        print(f"\n状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n响应:")
            print(f"  code: {data.get('code')}")
            print(f"  msg: {data.get('msg')}")
            
            result = data.get('data', {})
            print(f"  total_count: {result.get('total_count')}")
            
            leaderboard = result.get('leaderboard', [])
            print(f"\n排行榜数据 ({len(leaderboard)} 条):")
            print(f"\n{'Rank':<6}{'User':<15}{'Score':<10}{'Achieve Time'}")
            print("-" * 60)
            
            for item in leaderboard:
                print(
                    f"{item.get('rank', '-'):<6}"
                    f"{item.get('nickname', '-'):<15}"
                    f"{item.get('score', '-'):<10}"
                    f"{item.get('achieve_time', '-')}"
                )
            
            print("\n" + "=" * 60)
            print("✅ 接口测试成功！")
            print("=" * 60)
            return True
        else:
            print(f"\n❌ 请求失败: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ 连接失败！请先启动服务器:")
        print("   python -m app.main 或 python app/main.py")
        return False
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_highest_score()
