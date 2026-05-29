from typing import List, Dict, Optional
from collections import Counter


class ScoreCalculator:
    CATEGORIES = [
        "ones", "twos", "threes", "fours", "fives", "sixes",
        "threeOfAKind", "fourOfAKind", "fullHouse",
        "smallStraight", "largeStraight", "yahtzee", "chance"
    ]
    
    @staticmethod
    def calculate_score(dice: List[int], category: str) -> Optional[int]:
        dice = sorted(dice)
        counts = Counter(dice)
        
        if category in ["ones", "twos", "threes", "fours", "fives", "sixes"]:
            number_map = {"ones": 1, "twos": 2, "threes": 3, "fours": 4, "fives": 5, "sixes": 6}
            target = number_map[category]
            return counts.get(target, 0) * target
        
        elif category in ["three_of_a_kind", "threeOfAKind"]:
            if any(count >= 3 for count in counts.values()):
                return sum(dice)
            return 0
        
        elif category in ["four_of_a_kind", "fourOfAKind"]:
            if any(count >= 4 for count in counts.values()):
                return sum(dice)
            return 0
        
        elif category in ["full_house", "fullHouse"]:
            sorted_counts = sorted(counts.values())
            if sorted_counts == [2, 3]:
                return 25
            return 0
        
        elif category in ["small_straight", "smallStraight"]:
            if ScoreCalculator._has_straight(dice, 4):
                return 30
            return 0
        
        elif category in ["large_straight", "largeStraight"]:
            if ScoreCalculator._has_straight(dice, 5):
                return 40
            return 0
        
        elif category == "yahtzee":
            if any(count == 5 for count in counts.values()):
                return 50
            return 0
        
        elif category == "chance":
            return sum(dice)
        
        return None
    
    @staticmethod
    def _has_straight(dice: List[int], length: int) -> bool:
        unique = sorted(list(set(dice)))
        for i in range(len(unique) - length + 1):
            consecutive = True
            for j in range(length - 1):
                if unique[i + j + 1] - unique[i + j] != 1:
                    consecutive = False
                    break
            if consecutive:
                return True
        return False
    
    @staticmethod
    def calculate_upper_bonus(scores: Dict[str, Optional[int]]) -> int:
        upper_sum = sum(
            scores.get(cat, 0) or 0 
            for cat in ["ones", "twos", "threes", "fours", "fives", "sixes"]
        )
        return 35 if upper_sum >= 63 else 0
    
    @staticmethod
    def calculate_upper_score(scores: Dict[str, Optional[int]]) -> int:
        return sum(
            scores.get(cat, 0) or 0
            for cat in ["ones", "twos", "threes", "fours", "fives", "sixes"]
        )
    
    @staticmethod
    def calculate_lower_score(scores: Dict[str, Optional[int]]) -> int:
        return sum(
            scores.get(cat, 0) or 0
            for cat in ["threeOfAKind", "fourOfAKind", "fullHouse", 
                "smallStraight", "largeStraight", "yahtzee", "chance"]
        )
    
    @staticmethod
    def calculate_bonus(scores: Dict[str, Optional[int]]) -> int:
        return ScoreCalculator.calculate_upper_bonus(scores)
    
    @staticmethod
    def calculate_total_score(scores: Dict[str, Optional[int]]) -> int:
        total = sum(
            (scores.get(cat, 0) or 0) 
            for cat in ScoreCalculator.CATEGORIES
        )
        total += ScoreCalculator.calculate_upper_bonus(scores)
        return total
