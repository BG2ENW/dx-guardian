"""
DX Guardian - 趋势预测模块
基于历史 Spot 数据分析各波段活跃趋势
"""
from datetime import datetime, timezone, timedelta
from collections import defaultdict


class TrendAnalyzer:
    """趋势分析器"""

    def __init__(self):
        self.window_minutes = 60  # 分析窗口：60分钟

    def analyze(self, spot_history: list) -> dict:
        """
        分析波段趋势

        Args:
            spot_history: 最近 Spot 历史 [{band, time, ...}, ...]

        Returns:
            {
                'bands': {band: {count, trend, trend_label, top_dxcc}},
                'overall': '上升'/'稳定'/'下降',
                'peak_hours': [小时列表],
                'recent_rate': '每5分钟平均 Spot 数'
            }
        """
        if not spot_history:
            return {'bands': {}, 'overall': '无数据', 'peak_hours': [], 'recent_rate': 0}

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=self.window_minutes)

        # 按时间分段（10分钟一段）
        segments = 6
        seg_len = self.window_minutes // segments

        # 统计每个波段在每个时间段的 Spot 数
        band_seg_counts = defaultdict(lambda: [0] * segments)
        band_dxcc = defaultdict(lambda: defaultdict(int))
        total_per_seg = [0] * segments

        for spot in spot_history[-2000:]:
            ts = spot.get('_server_ts')
            if not ts:
                t = self._parse_time(spot.get('time', ''))
            else:
                t = datetime.fromtimestamp(ts, tz=timezone.utc)
            if not t or t < cutoff:
                continue

            age_minutes = (now - t).total_seconds() / 60
            seg_idx = min(int(age_minutes // seg_len), segments - 1)
            seg_idx = max(0, segments - 1 - seg_idx)  # 0=最早, segments-1=最近

            band = spot.get('band', '')
            if band:
                band_seg_counts[band][seg_idx] += 1
                total_per_seg[seg_idx] += 1
                dxcc = spot.get('dxcc', '')
                if dxcc:
                    band_dxcc[band][dxcc] += 1

        # 计算趋势
        result = {}
        all_up = 0
        all_down = 0

        for band, counts in sorted(band_seg_counts.items()):
            # 用后3段 vs 前3段对比
            early = sum(counts[:3])
            late = sum(counts[-3:])

            if early == 0 and late == 0:
                trend = '无活动'
                trend_val = 0
            elif early == 0:
                trend = '🆕 新活跃'
                trend_val = 100
            else:
                change = (late - early) / early * 100
                if change > 30:
                    trend = '📈 上升'
                    trend_val = change
                    all_up += 1
                elif change < -30:
                    trend = '📉 下降'
                    trend_val = change
                    all_down += 1
                else:
                    trend = '➡️ 稳定'
                    trend_val = change

            top_dxcc = sorted(band_dxcc[band].items(), key=lambda x: x[1], reverse=True)[:3]

            result[band] = {
                'count': sum(counts),
                'trend': trend,
                'trend_value': round(trend_val, 1),
                'top_dxcc': [{'name': d, 'count': c} for d, c in top_dxcc],
                'segment_counts': counts,
                'latest_rate': counts[-1] / (seg_len / 5) if counts[-1] > 0 else 0,
            }

        # 整体趋势
        early_total = sum(total_per_seg[:3])
        late_total = sum(total_per_seg[-3:])
        if early_total == 0 and late_total == 0:
            overall = '无数据'
        elif all_up > all_down * 2:
            overall = '📈 上升'
        elif all_down > all_up * 2:
            overall = '📉 下降'
        else:
            overall = '➡️ 稳定'

        # 最近5分钟速率
        recent_5m = sum(total_per_seg[-1:]) / max(len(total_per_seg[-1:]), 1) * (5 / seg_len) if total_per_seg else 0

        return {
            'bands': result,
            'overall': overall,
            'total_spots_1h': sum(total_per_seg),
            'recent_rate': round(recent_5m, 1),
            'peak_hours': self._find_peak_hours(spot_history, now),
        }

    def _parse_time(self, time_str: str) -> datetime | None:
        """解析 Spot 时间字符串"""
        if not time_str:
            return None
        try:
            # 尝试多种格式
            for fmt in ['%Y-%m-%dT%H:%M:%S', '%H%Mz', '%H:%M', '%Y-%m-%d %H:%M:%S']:
                try:
                    t = datetime.strptime(time_str, fmt)
                    if len(time_str) <= 8:
                        t = t.replace(year=datetime.now(timezone.utc).year,
                                      month=datetime.now(timezone.utc).month,
                                      day=datetime.now(timezone.utc).day,
                                      tzinfo=timezone.utc)
                    return t
                except ValueError:
                    continue
        except Exception:
            pass
        return None

    def _find_peak_hours(self, spot_history: list, now: datetime) -> list:
        """找出最近最活跃的小时"""
        hour_counts = defaultdict(int)
        for spot in spot_history[-1000:]:
            ts = spot.get('_server_ts')
            if ts:
                t = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                t = self._parse_time(spot.get('time', ''))
            if t:
                hour_counts[t.hour] += 1
        if not hour_counts:
            return []
        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
        return [{'hour': h, 'count': c} for h, c in sorted_hours[:5]]
