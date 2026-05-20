from typing import List, Dict, Optional, Any
from datetime import datetime
import json
from sqlalchemy import text
from app.db.session import SessionLocal
from app.models.game import Game as GameModel
from app.models.game_player import GamePlayer
from app.models.game_round import GameRound
from app.models.player_score_detail import PlayerScoreDetail
from app.models.score_item import ScoreItem
from app.models.user import User
from app.game.dice import DiceManager
from app.game.scoring import ScoreCalculator


class GameData:
    """游戏数据类，封装数据库操作"""
    
    def __init__(self, db_game_id: int):
        self.db_game_id = db_game_id
        self.db = SessionLocal()
        self._load_data()
    
    def _load_data(self):
        """从数据库加载数据"""
        print("========== LOAD GAME ==========")
        print("db_game_id:", self.db_game_id)
        print("db url:", self.db.bind.url)

        self.db_game = self.db.query(GameModel).filter(
            GameModel.id == self.db_game_id
        ).first()

        print("db_game:", self.db_game)

        self.db_players = self.db.query(GamePlayer).filter(
            GamePlayer.game_id == self.db_game_id
        ).order_by(GamePlayer.player_order).all()

        print("db_players:", self.db_players)

        self.db_round = self.db.query(GameRound).filter(
            GameRound.game_id == self.db_game_id
        ).first()

        print("db_round:", self.db_round)

        self.score_items = {
            si.item_name: si
            for si in self.db.query(ScoreItem).all()
        }

        print("score_items count:", len(self.score_items))
        print("========== LOAD GAME ==========")

        print("db url:", self.db.bind.url)

        current_db = self.db.execute(
            text("SELECT DATABASE()")
        ).scalar()

        print("current database:", current_db)

        result = self.db.execute(
            text("SELECT * FROM game")
        ).fetchall()

        print("raw game table:", result)

        self.db_game = self.db.query(GameModel).filter(
            GameModel.id == self.db_game_id
        ).first()

        print("db_game:", self.db_game)
    
    def get_current_player(self) -> Optional[GamePlayer]:
        """获取当前玩家"""
        if not self.db_round or not self.db_round.current_player_id:
            return None
        return next((p for p in self.db_players if p.user_id == self.db_round.current_player_id), None)
    
    def get_player_scores(self, user_id: int) -> Dict[str, Optional[int]]:
        """获取玩家的所有得分"""
        details = self.db.query(PlayerScoreDetail).filter(
            PlayerScoreDetail.game_id == self.db_game_id,
            PlayerScoreDetail.player_id == user_id
        ).all()
        
        scores = {cat: None for cat in ScoreCalculator.CATEGORIES}
        for detail in details:
            score_item = next((si for si in self.score_items.values() if si.id == detail.score_item_id), None)
            if score_item:
                scores[score_item.item_name] = detail.score_value
        return scores
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（API 响应用）"""
        mode_map = {1: "local", 2: "ai", 3: "online"}
        status_map = {1: "waiting", 2: "playing", 3: "finished", 4: "quit"}
        
        dice_data = json.loads(self.db_round.dice_data) if self.db_round and self.db_round.dice_data else [1, 1, 1, 1, 1]
        
        players = []
        for p in self.db_players:
            user = self.db.query(User).filter(User.id == p.user_id).first()
            scores = self.get_player_scores(p.user_id)
            user_name = user.nickname if user and user.nickname else f"Player{p.player_order}"
            players.append({
                "player_id": str(p.user_id),
                "name": user_name,
                "is_ai": bool(p.is_ai),
                "scores": scores,
                "total_score": p.total_score
            })
        
        current_player = self.get_current_player()
        
        return {
            "game_id": str(self.db_game.id),
            "game_mode": mode_map.get(self.db_game.game_mode, "local"),
            "current_player": str(current_player.user_id) if current_player else None,
            "players": players,
            "dice": dice_data,
            "dice_locked": [False] * 5,
            "rolls_left": self.db_round.reroll_count if self.db_round else 0,
            "status": status_map.get(self.db_game.game_status, "waiting"),
            "created_at": self.db_game.start_time.isoformat() if self.db_game.start_time else None,
            "finished_at": self.db_game.end_time.isoformat() if self.db_game.end_time else None
        }
    
    def commit(self):
        """提交事务"""
        self.db.commit()
        self._load_data()
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()


class GameManager:
    
    @classmethod
    def create_game(cls, game_mode: str, player_names: List[str]) -> GameData:
        """创建新游戏"""
        db = SessionLocal()
        try:
            mode_map = {"local": 1, "ai": 2, "online": 3}
            game_mode_db = mode_map.get(game_mode, 1)
            
            users = []
            for i, name in enumerate(player_names):
                is_ai = (game_mode == "ai" and i > 0)
                client_id = f"game-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i}"
                
                db_user = User(
                    client_id=client_id,
                    nickname=name,
                    user_type=2 if is_ai else 1,
                    ai_difficulty=2 if is_ai else None
                )
                db.add(db_user)
                db.flush()
                users.append((db_user, is_ai))
            
            db_game = GameModel(
                game_mode=game_mode_db,
                player_count=len(users),
                total_rounds=13,
                game_status=1,
                create_time=datetime.now()
            )
            db.add(db_game)
            db.flush()
            
            for idx, (user, is_ai) in enumerate(users):
                db_player = GamePlayer(
                    game_id=db_game.id,
                    user_id=user.id,
                    is_owner=1 if idx == 0 else 0,
                    player_order=idx + 1,
                    total_score=0,
                    upper_score=0,
                    lower_score=0,
                    bonus_score=0,
                    is_ai=1 if is_ai else 0
                )
                db.add(db_player)
            
            first_player_id = users[0][0].id
            db_round = GameRound(
                game_id=db_game.id,
                round_number=1,
                current_player_id=first_player_id,
                dice_data=json.dumps([1, 1, 1, 1, 1]),
                reroll_count=3,
                round_status=2,
                start_time=datetime.now()
            )
            db.add(db_round)
            
            db.commit()
            game_id = db_game.id
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
        
        return GameData(game_id)
    
    @classmethod
    def get_game(cls, game_id: str):
        try:
            print("game_id raw:", game_id)
            db_game_id = int(game_id)
            print("db_game_id:", db_game_id)
            game_data = GameData(db_game_id)
            print("game_data.db_game:", game_data.db_game)
            if not game_data.db_game:
                print("游戏不存在")
                game_data.close()
                return None

            return game_data     
        except Exception as e:
            print("get_game error:", e)
            import traceback
            traceback.print_exc()
            return None
    
    @classmethod
    def start_game(cls, game_data: GameData):
        """开始游戏"""
        game_data.db_game.game_status = 2
        game_data.db_game.start_time = datetime.now()
        game_data.commit()
    
    @classmethod
    def roll_dice(cls, game_data: GameData, user_id: int, locked_indices: List[int] = None) -> List[int]:
        """掷骰子"""
        current_player = game_data.get_current_player()
        if not current_player or current_player.user_id != user_id:
            raise Exception("Not your turn")
        
        if game_data.db_round.reroll_count <= 0:
            raise Exception("No rolls left")
        
        dice_manager = DiceManager()
        current_dice = json.loads(game_data.db_round.dice_data) if game_data.db_round.dice_data else [1, 1, 1, 1, 1]
        dice_manager.dice = current_dice
        
        locked = [False] * 5
        if locked_indices:
            for idx in locked_indices:
                if 0 <= idx < 5:
                    locked[idx] = True
        
        new_dice = dice_manager.roll([i for i, l in enumerate(locked) if l])
        
        game_data.db_round.dice_data = json.dumps(new_dice)
        game_data.db_round.reroll_count -= 1
        game_data.commit()
        
        return new_dice
    
    @classmethod
    def submit_score(cls, game_data: GameData, user_id: int, category: str) -> int:
        """提交分数"""
        current_player = game_data.get_current_player()
        if not current_player or current_player.user_id != user_id:
            raise Exception("Not your turn")
        
        score_item = game_data.score_items.get(category)
        if not score_item:
            raise Exception("Invalid category")
        
        existing = game_data.db.query(PlayerScoreDetail).filter(
            PlayerScoreDetail.game_id == game_data.db_game_id,
            PlayerScoreDetail.player_id == user_id,
            PlayerScoreDetail.score_item_id == score_item.id
        ).first()
        if existing:
            raise Exception("Category already scored")
        
        dice = json.loads(game_data.db_round.dice_data) if game_data.db_round.dice_data else [1, 1, 1, 1, 1]
        score = ScoreCalculator.calculate_score(dice, category)
        
        db_score = PlayerScoreDetail(
            game_id=game_data.db_game_id,
            player_id=user_id,
            score_item_id=score_item.id,
            round_number=game_data.db_round.round_number,
            score_value=score,
            submit_time=datetime.now()
        )
        game_data.db.add(db_score)
        
        player = next(p for p in game_data.db_players if p.user_id == user_id)
        all_scores = game_data.get_player_scores(user_id)
        all_scores[category] = score
        player.total_score = ScoreCalculator.calculate_total_score(all_scores)
        player.upper_score = ScoreCalculator.calculate_upper_score(all_scores)
        player.lower_score = ScoreCalculator.calculate_lower_score(all_scores)
        player.bonus_score = ScoreCalculator.calculate_bonus(all_scores)
        
        cls._next_turn(game_data)
        
        game_data.commit()
        return score
    
    @classmethod
    def _next_turn(cls, game_data: GameData):
        """下一回合"""
        players = game_data.db_players
        current_idx = next((i for i, p in enumerate(players) if p.user_id == game_data.db_round.current_player_id), 0)
        next_idx = (current_idx + 1) % len(players)
        
        if next_idx == 0:
            game_data.db_round.round_number += 1
        
        game_data.db_round.current_player_id = players[next_idx].user_id
        game_data.db_round.dice_data = json.dumps([1, 1, 1, 1, 1])
        game_data.db_round.reroll_count = 3
        
        if cls._is_game_finished(game_data):
            game_data.db_game.game_status = 3
            game_data.db_game.end_time = datetime.now()
            winner = max(players, key=lambda p: p.total_score)
            game_data.db_game.winner_id = winner.user_id
            game_data.db_round.round_status = 3
            game_data.db_round.end_time = datetime.now()
    
    @classmethod
    def _is_game_finished(cls, game_data: GameData) -> bool:
        """检查游戏是否结束"""
        score_item_count = len(game_data.score_items)
        for player in game_data.db_players:
            count = game_data.db.query(PlayerScoreDetail).filter(
                PlayerScoreDetail.game_id == game_data.db_game_id,
                PlayerScoreDetail.player_id == player.user_id
            ).count()
            if count < score_item_count:
                return False
        return True
    
    @classmethod
    def remove_game(cls, game_id: str):
        """移除游戏（软删除）"""
        try:
            db_game_id = int(game_id)
            db = SessionLocal()
            db_game = db.query(GameModel).filter(GameModel.id == db_game_id).first()
            if db_game:
                db_game.game_status = 4
                db_game.is_deleted = 1
                db.commit()
            db.close()
        except:
            pass
