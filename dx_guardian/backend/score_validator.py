"""
DX Guardian - 历史日志验证引擎
验证机会评分准确性：对比历史高分 Spot 和实际通联记录
"""
import json
from typing import Dict, List
from pathlib import Path


class ScoreValidator:
    """评分验证器"""

    def __init__(self, logs_dir: Path = None):
        if logs_dir is None:
            logs_dir = Path(__file__).parent / 'logs'
        self.logs_dir = logs_dir

    def load_all_logs(self) -> List[dict]:
        """加载所有日志记录"""
        logs_file = self.logs_dir / 'logs.json'
        if not logs_file.exists():
            return []
        try:
            with open(logs_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def get_worked_dxcc(self) -> dict:
        """获取所有已通联的 DXCC 集合 {dxcc: [callsigns]}"""
        worked = {}
        for log in self.load_all_logs():
            entries = log.get('entries', [])
            for entry in entries:
                dxcc = entry.get('dxcc', '').strip().upper()
                callsign = entry.get('callsign', '').strip()
                if dxcc and callsign:
                    if dxcc not in worked:
                        worked[dxcc] = []
                    worked[dxcc].append(callsign)
        return worked

    def get_all_worked_callsigns(self) -> set:
        """获取所有已通联呼号"""
        callsigns = set()
        for log in self.load_all_logs():
            entries = log.get('entries', [])
            for entry in entries:
                c = entry.get('callsign', '').strip()
                if c:
                    callsigns.add(c.upper())
        return callsigns

    def validate_prediction(self, scored_spots: List[dict], worked_callsigns: set) -> dict:
        """
        验证评分预测准确性

        Args:
            scored_spots: 历史评分过的 Spot 列表 [{callsign, dxcc, score, was_worked}]
            worked_callsigns: 实际已通联的呼号集合

        Returns:
            {
                'total_scored': 总评分数,
                'predicted_work': 预测应通联(≥60分),
                'predicted_skip': 预测不通联(<60分),
                'true_positives': 预测通联且实际通联,
                'false_positives': 预测通联但实际未通联,
                'true_negatives': 预测不通联且实际未通联,
                'false_negatives': 预测不通联但实际通联了,
                'accuracy': 准确率,
                'precision': 精确率,
                'recall': 召回率,
                'score_distribution': {分数段: {worked, missed, rate}},
            }
        """
        tp = fp = tn = fn = 0
        predicted_work = 0
        predicted_skip = 0

        score_dist = {
            '90-100': {'worked': 0, 'missed': 0, 'total': 0},
            '70-89': {'worked': 0, 'missed': 0, 'total': 0},
            '50-69': {'worked': 0, 'missed': 0, 'total': 0},
            '30-49': {'worked': 0, 'missed': 0, 'total': 0},
            '0-29': {'worked': 0, 'missed': 0, 'total': 0},
        }

        threshold = 60  # ≥60分视为"值得通联"

        for spot in scored_spots:
            callsign = spot.get('callsign', '').upper()
            score = spot.get('score', 0)
            was_worked = callsign in worked_callsigns

            # 分数段统计
            bucket = self._score_bucket(score)
            if bucket in score_dist:
                score_dist[bucket]['total'] += 1
                if was_worked:
                    score_dist[bucket]['worked'] += 1
                else:
                    score_dist[bucket]['missed'] += 1

            # 混淆矩阵
            if score >= threshold:
                predicted_work += 1
                if was_worked:
                    tp += 1
                else:
                    fp += 1
            else:
                predicted_skip += 1
                if was_worked:
                    fn += 1
                else:
                    tn += 1

        total = tp + fp + tn + fn
        accuracy = (tp + tn) / total if total > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0

        return {
            'total_scored': len(scored_spots),
            'predicted_work': predicted_work,
            'predicted_skip': predicted_skip,
            'true_positives': tp,
            'false_positives': fp,
            'true_negatives': tn,
            'false_negatives': fn,
            'accuracy': round(accuracy * 100, 1),
            'precision': round(precision * 100, 1),
            'recall': round(recall * 100, 1),
            'score_distribution': score_dist,
            'threshold': threshold,
        }

    @staticmethod
    def _score_bucket(score: int) -> str:
        if score >= 90:
            return '90-100'
        elif score >= 70:
            return '70-89'
        elif score >= 50:
            return '50-69'
        elif score >= 30:
            return '30-49'
        return '0-29'
