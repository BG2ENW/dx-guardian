"""
DX Guardian - 机会评分引擎
基于规则的多因子评分系统
输入：太阳数据 + 距离 + 波段活跃度 + 时间 + 模式
输出：0-100 评分 + 各因子详细得分
"""
import math
import time
from typing import Dict, Optional
from datetime import datetime, timezone


class OpportunityScorer:
    """机会评分引擎"""

    # 评分因子权重
    WEIGHTS = {
        'band_activity': 0.25,    # 波段活跃度
        'solar': 0.20,            # 太阳数据
        'time_window': 0.15,      # 时间窗口
        'distance': 0.15,         # 距离匹配
        'spot_heat': 0.15,        # Spot 热度
        'mode_match': 0.10,       # 模式匹配
    }

    # 各因子最大分
    MAX_SCORES = {
        'band_activity': 25,
        'solar': 20,
        'time_window': 15,
        'distance': 15,
        'spot_heat': 15,
        'mode_match': 10,
    }

    def __init__(self):
        self.my_lat = 45.8   # 默认哈尔滨
        self.my_lon = 126.5
        self.my_modes = ['FT8', 'CW', 'SSB']  # 默认支持的模式

    def update_station(self, lat: float, lon: float, modes: list = None):
        """更新台站位置和模式"""
        self.my_lat = lat
        self.my_lon = lon
        if modes:
            self.my_modes = [m.upper() for m in modes]

    def score(self, spot: dict, band_counts: dict, total_spots: int,
              solar_data: dict, spot_dxcc_count: int = 0) -> dict:
        """
        计算机会评分

        Args:
            spot: Spot 数据
            band_counts: 当前各波段 Spot 数量
            total_spots: Spot 总数
            solar_data: 太阳数据 {sfi, sn, k_index, a_index}
            spot_dxcc_count: 该 DXCC 当前 Spot 数量

        Returns:
            {
                'total': 0-100,
                'factors': {各因子得分和说明},
                'recommendation': '推荐'/'一般'/'不推荐'
            }
        """
        factors = {}

        # 1. 波段活跃度 (25分)
        factors['band_activity'] = self._score_band_activity(
            spot.get('band', ''), band_counts, total_spots
        )

        # 2. 太阳数据 (20分)
        factors['solar'] = self._score_solar(solar_data, spot.get('band', ''))

        # 3. 时间窗口 (15分)
        factors['time_window'] = self._score_time_window(spot.get('band', ''))

        # 4. 距离匹配 (15分)
        factors['distance'] = self._score_distance(
            spot.get('lat', 0), spot.get('lon', 0), spot.get('band', '')
        )

        # 5. Spot 热度 (15分)
        factors['spot_heat'] = self._score_spot_heat(spot_dxcc_count)

        # 6. 模式匹配 (10分)
        factors['mode_match'] = self._score_mode_match(spot.get('mode', ''))

        # 计算总分
        total = sum(f['score'] for f in factors.values())

        # 推荐等级
        if total >= 70:
            recommendation = '🟢 强烈推荐'
        elif total >= 50:
            recommendation = '🟡 推荐'
        elif total >= 30:
            recommendation = '🟠 一般'
        else:
            recommendation = '🔴 不推荐'

        return {
            'total': min(total, 100),
            'factors': factors,
            'recommendation': recommendation
        }

    def _score_band_activity(self, band: str, band_counts: dict, total_spots: int) -> dict:
        """波段活跃度评分"""
        max_score = self.MAX_SCORES['band_activity']

        if not band or total_spots == 0:
            return {'score': 0, 'max': max_score, 'detail': '无数据'}

        band_count = band_counts.get(band, 0)
        ratio = band_count / max(total_spots, 1)

        # 活跃度越高分越高
        score = min(int(ratio * max_score * 4), max_score)  # 25% 活跃度 = 满分

        detail = f'{band} 活跃 ({band_count}/{total_spots} = {ratio*100:.1f}%)'

        return {'score': score, 'max': max_score, 'detail': detail}

    def _score_solar(self, solar_data: dict, band: str) -> dict:
        """太阳数据评分"""
        max_score = self.MAX_SCORES['solar']

        sfi = solar_data.get('sfi', 0) if solar_data else 0
        k = solar_data.get('k_index', 0) if solar_data else 0

        score = 0
        details = []

        # SFI 评分 (最高12分)
        if sfi >= 150:
            sfi_score = 12
            details.append('SFI 极佳')
        elif sfi >= 100:
            sfi_score = 10
            details.append('SFI 良好')
        elif sfi >= 70:
            sfi_score = 7
            details.append('SFI 正常')
        elif sfi >= 50:
            sfi_score = 4
            details.append('SFI 偏低')
        else:
            sfi_score = 2
            details.append('SFI 很低')

        score += sfi_score

        # K 指数评分 (最高8分)
        if k <= 1:
            k_score = 8
            details.append('K 极稳定')
        elif k <= 2:
            k_score = 6
            details.append('K 稳定')
        elif k <= 3:
            k_score = 4
            details.append('K 轻微扰动')
        elif k <= 4:
            k_score = 2
            details.append('K 扰动')
        else:
            k_score = 0
            details.append('K 地磁暴')

        score += k_score

        # 波段修正：高频段需要更高的 SFI
        hf_bands_needing_good_sfi = ['10m', '12m', '15m', '17m']
        if band in hf_bands_needing_good_sfi and sfi < 70:
            score = max(score - 5, 0)
            details.append(f'{band} 需要更高 SFI')

        return {'score': min(score, max_score), 'max': max_score, 'detail': ', '.join(details)}

    def _score_time_window(self, band: str) -> dict:
        """时间窗口评分"""
        max_score = self.MAX_SCORES['time_window']

        now = datetime.now(timezone.utc)
        hour_utc = now.hour

        score = 5  # 基础分
        details = []

        # 低频段 (160m-40m): 夜间更好
        low_bands = ['160m', '80m', '60m', '40m']
        # 高频段 (20m-10m): 白天更好
        high_bands = ['20m', '17m', '15m', '12m', '10m']

        if band in low_bands:
            if 20 <= hour_utc or hour_utc <= 6:
                score += 10
                details.append('夜间低频传播好')
            elif 18 <= hour_utc <= 22 or 4 <= hour_utc <= 8:
                score += 5
                details.append('黄昏/黎明低频可用')
            else:
                details.append('白天低频吸收大')
        elif band in high_bands:
            if 8 <= hour_utc <= 16:
                score += 10
                details.append('白天 F2 层传播好')
            elif 6 <= hour_utc <= 18:
                score += 5
                details.append('F2 层部分可用')
            else:
                details.append('夜间高频关闭')
        else:
            details.append(f'{band or "未知"} 波段时间评估中性')

        # 灰线加分（日出日落前后）
        # 哈尔滨 UTC+8，日出约 22UTC，日落约 12UTC（近似）
        if hour_utc in [21, 22, 23, 0, 11, 12, 13]:
            score += 3
            details.append('灰线时间加分')

        return {'score': min(score, max_score), 'max': max_score, 'detail': ', '.join(details)}

    def _score_distance(self, lat: float, lon: float, band: str) -> dict:
        """距离匹配评分"""
        max_score = self.MAX_SCORES['distance']

        if lat == 0 and lon == 0:
            return {'score': 5, 'max': max_score, 'detail': '坐标未知，默认中性'}

        # 计算大圆距离
        dist_km = self._haversine(self.my_lat, self.my_lon, lat, lon)

        score = 0
        detail = f'{dist_km:.0f} km'

        # 根据距离匹配波段
        if band in ['160m', '80m', '60m']:
            # 低频段：近距离好（0-2000km）
            if dist_km <= 2000:
                score = 15
            elif dist_km <= 4000:
                score = 10
            else:
                score = 3
            detail += f' → {band} 短距传播'

        elif band in ['40m', '30m', '20m']:
            # 中频段：中距离好（1000-8000km）
            if 1000 <= dist_km <= 8000:
                score = 15
            elif 500 <= dist_km <= 12000:
                score = 10
            else:
                score = 5
            detail += f' → {band} 中距传播'

        elif band in ['17m', '15m', '12m', '10m']:
            # 高频段：远距离好（3000+km）
            if dist_km >= 3000:
                score = 15
            elif dist_km >= 1500:
                score = 10
            else:
                score = 3
            detail += f' → {band} 远距传播'

        else:
            score = 7
            detail += f' → {band or "?"} 距离中性'

        return {'score': min(score, max_score), 'max': max_score, 'detail': detail}

    def _score_spot_heat(self, dxcc_count: int) -> dict:
        """Spot 热度评分"""
        max_score = self.MAX_SCORES['spot_heat']

        if dxcc_count <= 0:
            return {'score': 3, 'max': max_score, 'detail': '该区域无近期 Spot'}

        if dxcc_count >= 10:
            score = 15
            detail = f'非常活跃 ({dxcc_count} 个 Spot)'
        elif dxcc_count >= 5:
            score = 12
            detail = f'活跃 ({dxcc_count} 个 Spot)'
        elif dxcc_count >= 3:
            score = 8
            detail = f'中等活跃 ({dxcc_count} 个 Spot)'
        elif dxcc_count >= 1:
            score = 5
            detail = f'少量活跃 ({dxcc_count} 个 Spot)'
        else:
            score = 3
            detail = '冷门区域'

        return {'score': score, 'max': max_score, 'detail': detail}

    def _score_mode_match(self, mode: str) -> dict:
        """模式匹配评分"""
        max_score = self.MAX_SCORES['mode_match']

        if not mode:
            return {'score': 5, 'max': max_score, 'detail': '模式未知'}

        mode = mode.upper()

        if mode in self.my_modes:
            return {'score': 10, 'max': max_score, 'detail': f'{mode} 匹配'}
        else:
            return {'score': 2, 'max': max_score, 'detail': f'{mode} 不匹配 (支持: {",".join(self.my_modes)})'}

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点间大圆距离（km）"""
        R = 6371  # 地球半径 km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        return R * c


# 测试
if __name__ == '__main__':
    scorer = OpportunityScorer()

    # 模拟 Spot
    test_spot = {
        'callsign': 'JA1AAA',
        'freq': 14.074,
        'band': '20m',
        'mode': 'FT8',
        'lat': 35.6762,
        'lon': 139.6503,
        'dxcc': 'Japan'
    }

    # 模拟数据
    test_band_counts = {'20m': 234, '40m': 180, '15m': 120, '10m': 50}
    test_total = 800
    test_solar = {'sfi': 105, 'sn': 80, 'k_index': 2, 'a_index': 5}

    result = scorer.score(test_spot, test_band_counts, test_total, test_solar, spot_dxcc_count=15)

    print(f"🎯 机会评分：{result['total']}/100")
    print(f"   推荐：{result['recommendation']}")
    print()
    for name, factor in result['factors'].items():
        print(f"   ├─ {name}: {factor['score']}/{factor['max']} ({factor['detail']})")
