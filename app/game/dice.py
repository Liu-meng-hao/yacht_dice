import random
from typing import List


class DiceManager:
    def __init__(self):
        self.num_dice = 5
        self.dice = [1] * self.num_dice
    
    def roll(self, locked_indices: List[int] = None) -> List[int]:
        locked_indices = locked_indices or []
        for i in range(self.num_dice):
            if i not in locked_indices:
                self.dice[i] = random.randint(1, 6)
        return self.dice.copy()
    
    def get_dice(self) -> List[int]:
        return self.dice.copy()
    
    def reset(self) -> List[int]:
        self.dice = [1] * self.num_dice
        return self.dice.copy()
