import uuid
from typing import List, Dict, Optional, Any
from app.game.dice import DiceManager
from app.game.scoring import ScoreCalculator
from datetime import datetime


class Player:
    def __init__(self, player_id: str, name: str, is_ai: bool = False):
        self.player_id = player_id
        self.name = name
        self.is_ai = is_ai
        self.scores: Dict[str, Optional[int]] = {cat: None for cat in ScoreCalculator.CATEGORIES}
        self.total_score: int = 0


class Game:
    def __init__(self, game_id: str, game_mode: str, players: List[Player]):
        self.game_id = game_id
        self.game_mode = game_mode
        self.players = players
        self.current_player_index = 0
        self.dice_manager = DiceManager()
        self.rolls_left = 3
        self.status = "waiting"
        self.created_at = datetime.utcnow()
        self.finished_at: Optional[datetime] = None
    
    def start(self):
        self.status = "playing"
        self.rolls_left = 3
        self.dice_manager.reset()
    
    def get_current_player(self) -> Optional[Player]:
        if self.players:
            return self.players[self.current_player_index]
        return None
    
    def roll_dice(self, locked_indices: List[int] = None) -> List[int]:
        if self.rolls_left <= 0:
            raise Exception("No rolls left")
        dice = self.dice_manager.roll(locked_indices)
        self.rolls_left -= 1
        return dice
    
    def submit_score(self, player_id: str, category: str) -> int:
        player = next((p for p in self.players if p.player_id == player_id), None)
        if not player:
            raise Exception("Player not found")
        if player != self.get_current_player():
            raise Exception("Not your turn")
        if player.scores[category] is not None:
            raise Exception("Category already scored")
        
        score = ScoreCalculator.calculate_score(self.dice_manager.get_dice(), category)
        player.scores[category] = score
        player.total_score = ScoreCalculator.calculate_total_score(player.scores)
        
        self._next_turn()
        return score
    
    def _next_turn(self):
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self.rolls_left = 3
        self.dice_manager.reset()
        
        if self._is_game_finished():
            self.status = "finished"
            self.finished_at = datetime.utcnow()
    
    def _is_game_finished(self) -> bool:
        return all(
            all(score is not None for score in player.scores.values())
            for player in self.players
        )
    
    def get_winner(self) -> Optional[Player]:
        if self.status != "finished":
            return None
        return max(self.players, key=lambda p: p.total_score)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "game_mode": self.game_mode,
            "current_player": self.get_current_player().player_id if self.get_current_player() else None,
            "players": [
                {
                    "player_id": p.player_id,
                    "name": p.name,
                    "is_ai": p.is_ai,
                    "scores": p.scores,
                    "total_score": p.total_score
                }
                for p in self.players
            ],
            "dice": self.dice_manager.get_dice(),
            "rolls_left": self.rolls_left,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None
        }


class GameManager:
    _games: Dict[str, Game] = {}
    
    @classmethod
    def create_game(cls, game_mode: str, player_names: List[str]) -> Game:
        game_id = str(uuid.uuid4())
        players = [
            Player(str(uuid.uuid4()), name, is_ai=(game_mode == "ai" and i > 0))
            for i, name in enumerate(player_names)
        ]
        game = Game(game_id, game_mode, players)
        cls._games[game_id] = game
        return game
    
    @classmethod
    def get_game(cls, game_id: str) -> Optional[Game]:
        return cls._games.get(game_id)
    
    @classmethod
    def remove_game(cls, game_id: str):
        if game_id in cls._games:
            del cls._games[game_id]
