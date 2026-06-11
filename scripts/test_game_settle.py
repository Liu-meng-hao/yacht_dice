"""
测试游戏结算接口
"""
import sys
import os
import urllib.request
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1/leaderboard"


def test_2_player_game():
    """测试2人联机对局"""
    print("\n" + "="*60)
    print("测试场景1: 2人联机对局")
    print("="*60)
    
    url = f"{BASE_URL}{API_PREFIX}/game-settle"
    data = {
        "game_id": 1001,
        "game_mode": 3,  # 联机对战
        "players": [
            {
                "user_id": 1,
                "rank": 1,
                "total_score": 250
            },
            {
                "user_id": 2,
                "rank": 2,
                "total_score": 180
            }
        ]
    }
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                print(f"\n✅ 成功!")
                
                for player_result in result['data']['results']:
                    print(f"\n--- 玩家{player_result['user_id']} (第{player_result['rank']}名) ---")
                    print(f"   排名奖励:     +{player_result['rank_reward']}")
                    print(f"   得分加成:     +{player_result['score_bonus']}")
                    print(f"   连胜加成:     ×{1 + player_result['streak_bonus']:.2f}")
                    print(f"   模式系数:     ×{player_result['mode_multiplier']}")
                    print(f"   本局获得:     +{player_result['total_experience']}")
                    print(f"   经验变化:     {player_result['old_experience']} → {player_result['new_experience']}")
                    
                    if player_result['win_streak_updated']:
                        print(f"   连胜变化:     {player_result['old_streak']} → {player_result['new_streak']}")
                
                return True
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_player_game():
    """测试4人人机对局"""
    print("\n" + "="*60)
    print("测试场景2: 4人人机对局")
    print("="*60)
    
    url = f"{BASE_URL}{API_PREFIX}/game-settle"
    data = {
        "game_id": 1002,
        "game_mode": 2,  # 人机对战
        "players": [
            {
                "user_id": 1,
                "rank": 1,
                "total_score": 300
            },
            {
                "user_id": 2,
                "rank": 2,
                "total_score": 250
            },
            {
                "user_id": 3,
                "rank": 3,
                "total_score": 200
            },
            {
                "user_id": 4,
                "rank": 4,
                "total_score": 150
            }
        ]
    }
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                print(f"\n✅ 成功!")
                
                for player_result in result['data']['results']:
                    print(f"\n--- 玩家{player_result['user_id']} (第{player_result['rank']}名) ---")
                    print(f"   排名奖励:     +{player_result['rank_reward']}")
                    print(f"   得分加成:     +{player_result['score_bonus']}")
                    print(f"   连胜加成:     ×{1 + player_result['streak_bonus']:.2f}")
                    print(f"   模式系数:     ×{player_result['mode_multiplier']}")
                    print(f"   本局获得:     +{player_result['total_experience']}")
                    print(f"   经验变化:     {player_result['old_experience']} → {player_result['new_experience']}")
                
                return True
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*60)
    print("游戏结算接口完整测试")
    print("="*60)
    
    tests = [
        test_2_player_game,
        test_4_player_game
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
    main()
