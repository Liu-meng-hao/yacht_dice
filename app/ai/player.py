"""
AI玩家模块
实现AI的投骰、锁骰、计分策略
"""
import random
import json
from typing import List, Dict, Optional, Tuple
from app.game.dice import DiceManager
from app.game.scoring import ScoreCalculator


class AIPlayer:
    """AI玩家类，实现游戏策略"""
    
    def __init__(self, difficulty: int = 2):
        """
        初始化AI玩家
        
        Args:
            difficulty: 难度等级（1-简单，2-中等，3-困难）
        """
        self.difficulty = difficulty
        self.dice_manager = DiceManager()
    
    def decide_action(self, dice: List[int], rolls_left: int, available_categories: List[str]) -> Tuple[str, List[bool], Optional[str]]:
        """
        决定AI的下一步行动
        
        Args:
            dice: 当前骰子点数
            rolls_left: 剩余投骰次数
            available_categories: 可用的计分项列表
        
        Returns:
            (action, locked_dice, category): 
                action: 'roll' or 'score'
                locked_dice: 要锁定的骰子列表
                category: 要计分的项目（仅当action='score'时）
        """
        if self.difficulty == 1:
            return self._easy_strategy(dice, rolls_left, available_categories)
        elif self.difficulty == 3:
            return self._hard_strategy(dice, rolls_left, available_categories)
        else:
            return self._medium_strategy(dice, rolls_left, available_categories)
    
    def _easy_strategy(self, dice: List[int], rolls_left: int, available_categories: List[str]) -> Tuple[str, List[bool], Optional[str]]:
        """简单策略：随机决定"""
        # 如果没有剩余投骰次数，必须计分
        if rolls_left <= 0:
            return self._choose_random_category(dice, available_categories)
        
        # 50%概率继续投骰，50%概率计分
        if random.random() < 0.5 and available_categories:
            return self._choose_random_category(dice, available_categories)
        else:
            # 随机锁定一些骰子
            locked = [random.random() < 0.3 for _ in range(5)]
            return ('roll', locked, None)
    
    def _medium_strategy(self, dice: List[int], rolls_left: int, available_categories: List[str]) -> Tuple[str, List[bool], Optional[str]]:
        """中等策略：简单的启发式策略"""
        # 如果没有剩余投骰次数，必须计分
        if rolls_left <= 0:
            return self._choose_best_category(dice, available_categories)
        
        # 计算当前各个计分项的可能得分
        current_scores = {cat: ScoreCalculator.calculate_score(dice, cat) for cat in available_categories}
        
        # 寻找可能的高分组合
        if self._is_potential_yahtzee(dice):
            return ('roll', self._lock_for_yahtzee(dice), None)
        
        if self._is_potential_straight(dice):
            return ('roll', self._lock_for_straight(dice), None)
        
        if self._is_potential_full_house(dice):
            return ('roll', self._lock_for_full_house(dice), None)
        
        # 检查是否有足够好的分数可以提交
        best_score = max(current_scores.values()) if current_scores else 0
        if best_score >= 20 and rolls_left == 1:
            return self._choose_best_category(dice, available_categories)
        
        # 否则继续投骰，锁定高分骰子
        return ('roll', self._lock_high_dice(dice), None)
    
    def _hard_strategy(self, dice: List[int], rolls_left: int, available_categories: List[str]) -> Tuple[str, List[bool], Optional[str]]:
        """困难策略：更优化的策略"""
        # 如果没有剩余投骰次数，必须计分
        if rolls_left <= 0:
            return self._choose_best_category(dice, available_categories)
        
        current_scores = {cat: ScoreCalculator.calculate_score(dice, cat) for cat in available_categories}
        
        # 优先追求Yahtzee
        if self._is_potential_yahtzee(dice) and 'yahtzee' in available_categories:
            return ('roll', self._lock_for_yahtzee(dice), None)
        
        # 追求大顺子
        if self._is_potential_large_straight(dice) and 'largeStraight' in available_categories:
            return ('roll', self._lock_for_straight(dice), None)
        
        # 追求小顺子
        if self._is_potential_small_straight(dice) and 'smallStraight' in available_categories:
            return ('roll', self._lock_for_straight(dice), None)
        
        # 追求Full House
        if self._is_potential_full_house(dice) and 'fullHouse' in available_categories:
            return ('roll', self._lock_for_full_house(dice), None)
        
        # 检查上半区是否需要高分
        upper_categories = ['ones', 'twos', 'threes', 'fours', 'fives', 'sixes']
        available_upper = [cat for cat in upper_categories if cat in available_categories]
        
        if available_upper:
            best_upper = max(available_upper, key=lambda cat: ScoreCalculator.calculate_score(dice, cat))
            upper_score = ScoreCalculator.calculate_score(dice, best_upper)
            # 如果上半区得分不错，可以考虑提交
            if upper_score >= 3 * (int(best_upper[-1]) if best_upper[-1].isdigit() else 0) and rolls_left == 1:
                return ('score', [False]*5, best_upper)
        
        # 如果有很好的分数，提前提交
        best_score = max(current_scores.values()) if current_scores else 0
        if best_score >= 25:
            return self._choose_best_category(dice, available_categories)
        
        # 继续优化骰子
        return ('roll', self._lock_optimal_dice(dice, available_categories), None)
    
    def _choose_random_category(self, dice: List[int], available_categories: List[str]) -> Tuple[str, List[bool], Optional[str]]:
        """随机选择一个计分项"""
        if not available_categories:
            raise Exception("No available categories")
        category = random.choice(available_categories)
        return ('score', [False]*5, category)
    
    def _choose_best_category(self, dice: List[int], available_categories: List[str]) -> Tuple[str, List[bool], Optional[str]]:
        """选择得分最高的计分项"""
        if not available_categories:
            raise Exception("No available categories")
        
        scores = {cat: ScoreCalculator.calculate_score(dice, cat) for cat in available_categories}
        best_category = max(scores.items(), key=lambda x: x[1])[0]
        return ('score', [False]*5, best_category)
    
    def _is_potential_yahtzee(self, dice: List[int]) -> bool:
        """判断是否有可能凑成Yahtzee"""
        counts = {}
        for d in dice:
            counts[d] = counts.get(d, 0) + 1
        return max(counts.values()) >= 4
    
    def _is_potential_straight(self, dice: List[int]) -> bool:
        """判断是否有可能凑成顺子"""
        unique = set(dice)
        return len(unique) >= 4
    
    def _is_potential_large_straight(self, dice: List[int]) -> bool:
        """判断是否有可能凑成大顺子"""
        unique = set(dice)
        return len(unique) >= 4
    
    def _is_potential_small_straight(self, dice: List[int]) -> bool:
        """判断是否有可能凑成小顺子"""
        unique = set(dice)
        return len(unique) >= 3
    
    def _is_potential_full_house(self, dice: List[int]) -> bool:
        """判断是否有可能凑成Full House"""
        counts = {}
        for d in dice:
            counts[d] = counts.get(d, 0) + 1
        values = sorted(counts.values(), reverse=True)
        return values[0] >= 3 or (values[0] >= 2 and len(values) >= 2)
    
    def _lock_for_yahtzee(self, dice: List[int]) -> List[bool]:
        """为了凑Yahtzee锁定骰子"""
        counts = {}
        for d in dice:
            counts[d] = counts.get(d, 0) + 1
        target = max(counts.items(), key=lambda x: x[1])[0]
        return [d == target for d in dice]
    
    def _lock_for_straight(self, dice: List[int]) -> List[bool]:
        """为了凑顺子锁定骰子"""
        # 锁定所有不重复的骰子
        seen = set()
        locked = []
        for d in dice:
            if d not in seen:
                seen.add(d)
                locked.append(True)
            else:
                locked.append(False)
        return locked
    
    def _lock_for_full_house(self, dice: List[int]) -> List[bool]:
        """为了凑Full House锁定骰子"""
        counts = {}
        for d in dice:
            counts[d] = counts.get(d, 0) + 1
        
        # 找出出现次数最多的两个数字
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        keep = set()
        if sorted_counts:
            keep.add(sorted_counts[0][0])
        if len(sorted_counts) > 1:
            keep.add(sorted_counts[1][0])
        
        return [d in keep for d in dice]
    
    def _lock_high_dice(self, dice: List[int]) -> List[bool]:
        """锁定高分骰子（4,5,6）"""
        return [d >= 4 for d in dice]
    
    def _lock_optimal_dice(self, dice: List[int], available_categories: List[str]) -> List[bool]:
        """优化的骰子锁定策略"""
        counts = {}
        for d in dice:
            counts[d] = counts.get(d, 0) + 1
        
        # 锁定出现次数多的骰子
        locked = [False] * 5
        for num, count in counts.items():
            if count >= 2:
                for i, d in enumerate(dice):
                    if d == num:
                        locked[i] = True
        
        # 如果没有多个相同的，锁定高分骰子
        if not any(locked):
            locked = self._lock_high_dice(dice)
        
        return locked
