"""
DX Guardian - 机会评分引擎 V2 (增强版)
基于 v6.3 规划的多因子加权评分系统

增强功能:
1. 添加传播预测集成 (VOACAP)
2. 添加历史成功率因子
3. 添加用户偏好匹配
4. 添加实时衰减机制
5. 优化评分算法权重
"""
import math
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from pathlib import Path


class OpportunityScorerV2:
    """机会评分引擎 V2 (增强版)"""

    # 评分因子权重 (总和=1.0)
    WEIGHTS = {
        'band_activity': 0.22,    # 波段活跃度 (降低 3%)
        'solar': 0.18,            # 太阳数据 (降低 2%)
        'time_window': 0.15,      # 时间窗口 (不变)
        'distance': 0.13,         # 距离匹配 (降低 2%)
        'spot_heat': 0.12,        # Spot 热度 (降低 3%)
        'mode_match': 0.10,       # 模式匹配 (不变)
        'propagation': 0.07,      # 传播预测 (新增)
        'history_success': 0.03,  # 历史成功率 (新增)
    }

    # 各因子最大分
    MAX_SCORES = {
        'band_activity': 22,
        'solar': 18,
        'time_window': 15,
        'distance': 13,
        'spot_heat': 12,
        'mode_match': 10,
        'propagation': 7,
        'history_success': 3,
    }

    # 波段优先级配置
    BAND_PRIORITY = {
        '10m': {' freq_khz': 28000, 'max_dist_km': 15000, 'min_sfi': 100},
        '12m': {'freq_khz': 24000, 'max_dist_km': 12000, 'min_sfi': 90},
        '15m': {'freq_khz': 21000, 'max_dist_km': 10000, 'min_sfi': 80},
        '17m': {'freq_khz': 18000, 'max_dist_km': 8000, 'min_sfi': 70},
        '20m': {'freq_khz': 14000, 'max_dist_km': 15000, 'min_sfi': 60},
        '30m': {'freq_khz': 10000, 'max_dist_km': 5000, 'min_sfi': 50},
        '40m': {'freq_khz': 7000, 'max_dist_km': 4000, 'min_sfi': 40},
        '80m': {'freq_khz': 3500, 'max_dist_km': 2000, 'min_sfi': 30},
        '160m': {'freq_khz': 1800, 'max_dist_km': 1000, 'min_sfi': 20},
    }

    def __init__(self, station_lat: float = 45.8, station_lon: float = 126.5,
                 user_modes: List[str] = None, user_bands: List[str] = None):
        """
        初始化评分器
        
        Args:
            station_lat: 台站纬度
            station_lon: 台站经度
            user_modes: 用户支持的模式列表
            user_bands: 用户关注的波段列表
        """
        self.my_lat = station_lat
        self.my_lon = station_lon
        self.my_modes = [m.upper() for m in (user_modes or ['FT8', 'CW', 'SSB'])]
        self.my_bands = user_bands or None  # None 表示全波段
        self.history_cache = {}  # 历史成功率缓存
        self.prop_cache = {}  # 传播预测缓存

    def update_station(self, lat: float, lon: float, modes: List[str] = None,
                       bands: List[str] = None):
        """更新台站配置"""
        self.my_lat = lat
        self.my_lon = lon
        if modes:
            self.my_modes = [m.upper() for m in modes]
        if bands:
            self.my_bands = [b.lower() for b in bands]

    def score(self, spot: Dict, band_counts: Dict, total_spots: int,
              solar_data: Dict, spot_dxcc_count: int = 0,
              voacap_data: Optional[Dict] = None) -> Dict:
        """
        计算机会评分 (V2 增强版)

        Args:
            spot: Spot 数据
            band_counts: 当前各波段 Spot 数量
            total_spots: Spot 总数
            solar_data: 太阳数据 {sfi, sn, k_index, a_index}
            spot_dxcc_count: 该 DXCC 当前 Spot 数量
            voacap_data: VOACAP 传播预测数据 (可选)

        Returns:
            {
                'total': 0-100,
                'factors': {各因子得分和说明},
                'recommendation': '推荐等级',
                'decay_factor': 实时衰减系数
            }
        """
        factors = {}

        # 1. 波段活跃度 (22 分)
        factors['band_activity'] = self._score_band_activity(
            spot.get('band', ''), band_counts, total_spots
        )

        # 2. 太阳数据 (18 分)
        factors['solar'] = self._score_solar(solar_data, spot.get('band', ''))

        # 3. 时间窗口 + 灰线 (15 分)
        factors['time_window'] = self._score_time_window_v2(
            spot.get('band', ''), spot.get('lat', 0), spot.get('lon', 0)
        )

        # 4. 距离匹配 (13 分)
        factors['distance'] = self._score_distance_v2(
            spot.get('lat', 0), spot.get('lon', 0), spot.get('band', ''), solar_data
        )

        # 5. Spot 热度 (12 分)
        factors['spot_heat'] = self._score_spot_heat(spot_dxcc_count)

        # 6. 模式匹配 (10 分)
        factors['mode_match'] = self._score_mode_match(spot.get('mode', ''))

        # 7. 传播预测 (7 分，新增)
        factors['propagation'] = self._score_propagation(
            spot.get('band', ''), voacap_data, solar_data
        )

        # 8. 历史成功率 (3 分，新增)
        factors['history_success'] = self._score_history_success(
            spot.get('dxcc', ''), spot.get('band', '')
        )

        # 计算基础总分
        total = sum(f['score'] for f in factors.values())

        # 应用实时衰减 (Spot 时间越久分数越低)
        decay_factor = self._calc_time_decay(spot)
        total = total * decay_factor

        # 用户偏好加成 (关注的波段/模式)
        preference_bonus = self._calc_preference_bonus(spot)
        total = min(total + preference_bonus, 100)

        # 推荐等级
        if total >= 80:
            recommendation = '🟢 强烈推荐'
        elif total >= 60:
            recommendation = '🟡 推荐'
        elif total >= 40:
            recommendation = '🟠 一般'
        else:
            recommendation = '🔴 不推荐'

        return {
            'total': round(min(total, 100), 1),
            'factors': factors,
            'recommendation': recommendation,
            'decay_factor': round(decay_factor, 2),
            'preference_bonus': round(preference_bonus, 1)
        }

    def _score_band_activity(self, band: str, band_counts: Dict, total_spots: int) -> Dict:
        """波段活跃度评分"""
        max_score = self.MAX_SCORES['band_activity']

        if not band or total_spots == 0:
            return {'score': 0, 'max': max_score, 'detail': '无数据'}

        band_count = band_counts.get(band, 0)
        ratio = band_count / max(total_spots, 1)

        # 优化：考虑波段优先级
        priority_multiplier = 1.0
        if self.my_bands and band.lower() in self.my_bands:
            priority_multiplier = 1.2  # 关注波段 +20%

        score = min(int(ratio * max_score * 4 * priority_multiplier), max_score)
        detail = f'{band} 活跃 ({band_count}/{total_spots} = {ratio*100:.1f}%)'

        if priority_multiplier > 1.0:
            detail += ' [关注波段 +20%]'

        return {'score': score, 'max': max_score, 'detail': detail}

    def _score_solar(self, solar_data: Dict, band: str) -> Dict:
        """太阳数据评分 (V2 优化)"""
        max_score = self.MAX_SCORES['solar']

        if not solar_data:
            return {'score': 5, 'max': max_score, 'detail': '太阳数据缺失'}

        sfi = solar_data.get('sfi', 0)
        k = solar_data.get('k_index', 0)
        a = solar_data.get('a_index', 0)

        score = 0
        details = []

        # SFI 评分 (最高 10 分，更细粒度)
        if sfi >= 150:
            sfi_score = 10
            details.append('SFI 极佳')
        elif sfi >= 120:
            sfi_score = 9
            details.append('SFI 优秀')
        elif sfi >= 100:
            sfi_score = 8
            details.append('SFI 良好')
        elif sfi >= 80:
            sfi_score = 6
            details.append('SFI 正常')
        elif sfi >= 70:
            sfi_score = 5
            details.append('SFI 一般')
        elif sfi >= 50:
            sfi_score = 3
            details.append('SFI 偏低')
        else:
            sfi_score = 1
            details.append('SFI 很低')

        score += sfi_score

        # K 指数评分 (最高 6 分)
        if k <= 1:
            k_score = 6
            details.append('K 极稳定')
        elif k <= 2:
            k_score = 5
            details.append('K 稳定')
        elif k <= 3:
            k_score = 3
            details.append('K 轻微扰动')
        elif k <= 4:
            k_score = 2
            details.append('K 扰动')
        elif k <= 5:
            k_score = 1
            details.append('K 地磁扰动')
        else:
            k_score = 0
            details.append('K 地磁暴')

        score += k_score

        # A 指数修正 (额外 ±1 分)
        if a <= 5:
            score += 1
            details.append('A 稳定')
        elif a >= 30:
            score -= 1
            details.append('A 扰动')

        # 波段修正：高频段需要更高的 SFI
        hf_bands_needing_good_sfi = ['10m', '12m', '15m', '17m']
        if band in hf_bands_needing_good_sfi and sfi < 70:
            score = max(score - 3, 0)
            details.append(f'{band} 需要更高 SFI')

        return {'score': min(score, max_score), 'max': max_score, 'detail': ', '.join(details)}

    def _score_time_window_v2(self, band: str, lat: float, lon: float) -> Dict:
        """时间窗口评分 (V2 增强：添加灰线计算)"""
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

        # 灰线计算增强版
        grayline_bonus = self._calc_grayline_bonus(lat, lon, hour_utc)
        if grayline_bonus > 0:
            score += min(grayline_bonus, 3)
            details.append(f'灰线时间 +{grayline_bonus}分')

        return {'score': min(score, max_score), 'max': max_score, 'detail': ', '.join(details)}

    def _calc_grayline_bonus(self, lat: float, lon: float, hour_utc: int) -> int:
        """
        计算灰线时间加分
        
        灰线：日出日落前后 1 小时
        根据目标位置和本地位置的相对时区计算
        """
        bonus = 0
        
        # 目标位置时区估算 (经度/15)
        target_tz_offset = int(lon / 15)
        target_hour = (hour_utc + target_tz_offset) % 24
        
        # 日出 (6 点前后) 和 日落 (18 点前后) 加分
        if target_hour in [5, 6, 7, 17, 18, 19]:
            bonus += 2
        
        # 本地 (哈尔滨 UTC+8) 的灰线时间
        local_hour = (hour_utc + 8) % 24
        if local_hour in [5, 6, 7, 17, 18, 19]:
            bonus += 1
        
        return bonus

    def _score_distance_v2(self, lat: float, lon: float, band: str, solar_data: Dict) -> Dict:
        """距离匹配评分 (V2 优化：考虑太阳数据)"""
        max_score = self.MAX_SCORES['distance']

        if lat == 0 and lon == 0:
            return {'score': 5, 'max': max_score, 'detail': '坐标未知，默认中性'}

        dist_km = self._haversine(self.my_lat, self.my_lon, lat, lon)
        score = 0
        detail = f'{dist_km:.0f} km'

        # 考虑太阳数据的波段修正
        sfi = solar_data.get('sfi', 0) if solar_data else 0
        hf_boost = 1.0 if (band in ['10m', '12m', '15m'] and sfi >= 100) else 1.0

        if band in ['160m', '80m', '60m']:
            if dist_km <= 2000:
                score = 13
            elif dist_km <= 4000:
                score = 9
            else:
                score = 4
            detail += f' → {band} 短距传播'

        elif band in ['40m', '30m', '20m']:
            if 1000 <= dist_km <= 8000:
                score = 13
            elif 500 <= dist_km <= 12000:
                score = 9
            else:
                score = 5
            detail += f' → {band} 中距传播'

        elif band in ['17m', '15m', '12m', '10m']:
            if dist_km >= 3000:
                score = int(13 * hf_boost)
            elif dist_km >= 1500:
                score = 9
            else:
                score = 4
            detail += f' → {band} 远距传播' + (' (SFI 加成)' if hf_boost > 1.0 else '')

        else:
            score = 6
            detail += f' → {band or "?"} 距离中性'

        return {'score': min(score, max_score), 'max': max_score, 'detail': detail}

    def _score_spot_heat(self, dxcc_count: int) -> Dict:
        """Spot 热度评分"""
        max_score = self.MAX_SCORES['spot_heat']

        if dxcc_count <= 0:
            return {'score': 2, 'max': max_score, 'detail': '该区域无近期 Spot'}

        if dxcc_count >= 10:
            score = 12
            detail = f'非常活跃 ({dxcc_count} 个 Spot)'
        elif dxcc_count >= 5:
            score = 10
            detail = f'活跃 ({dxcc_count} 个 Spot)'
        elif dxcc_count >= 3:
            score = 7
            detail = f'中等活跃 ({dxcc_count} 个 Spot)'
        elif dxcc_count >= 1:
            score = 4
            detail = f'少量活跃 ({dxcc_count} 个 Spot)'
        else:
            score = 2
            detail = '冷门区域'

        return {'score': score, 'max': max_score, 'detail': detail}

    def _score_mode_match(self, mode: str) -> Dict:
        """模式匹配评分"""
        max_score = self.MAX_SCORES['mode_match']

        if not mode:
            return {'score': 5, 'max': max_score, 'detail': '模式未知'}

        mode = mode.upper()

        if mode in self.my_modes:
            return {'score': 10, 'max': max_score, 'detail': f'{mode} 匹配'}
        else:
            return {'score': 2, 'max': max_score, 'detail': f'{mode} 不匹配 (支持：{",".join(self.my_modes)})'}

    def _score_propagation(self, band: str, voacap_data: Optional[Dict], solar_data: Dict) -> Dict:
        """
        传播预测评分 (新增因子)
        
        如果有 VOACAP 数据，使用预测结果；否则使用太阳数据估算
        """
        max_score = self.MAX_SCORES['propagation']

        if voacap_data:
            # 使用 VOACAP 预测数据
            prob = voacap_data.get('probability', 0)
            if prob >= 80:
                return {'score': max_score, 'max': max_score, 'detail': f'VOACAP 预测极佳 ({prob}%)'}
            elif prob >= 60:
                return {'score': int(max_score * 0.8), 'max': max_score, 'detail': f'VOACAP 预测良好 ({prob}%)'}
            elif prob >= 40:
                return {'score': int(max_score * 0.5), 'max': max_score, 'detail': f'VOACAP 预测一般 ({prob}%)'}
            else:
                return {'score': 1, 'max': max_score, 'detail': f'VOACAP 预测较差 ({prob}%)'}

        # 无 VOACAP 数据时，使用太阳数据估算
        sfi = solar_data.get('sfi', 0) if solar_data else 0
        k = solar_data.get('k_index', 0) if solar_data else 0

        if sfi >= 100 and k <= 2:
            return {'score': 5, 'max': max_score, 'detail': '太阳数据暗示传播良好'}
        elif sfi >= 70 and k <= 3:
            return {'score': 4, 'max': max_score, 'detail': '太阳数据中性'}
        else:
            return {'score': 2, 'max': max_score, 'detail': '太阳条件不佳'}

    def _score_history_success(self, dxcc: str, band: str) -> Dict:
        """
        历史成功率评分 (新增因子)
        
        基于过去与该 DXCC 在该波段的成功 QSO 记录
        """
        max_score = self.MAX_SCORES['history_success']
        
        cache_key = f"{dxcc}_{band}"
        if cache_key in self.history_cache:
            success_rate = self.history_cache[cache_key]
            if success_rate >= 0.7:
                return {'score': 3, 'max': max_score, 'detail': f'历史成功率高 ({success_rate*100:.0f}%)'}
            elif success_rate >= 0.4:
                return {'score': 2, 'max': max_score, 'detail': f'历史成功率中等 ({success_rate*100:.0f}%)'}
            else:
                return {'score': 1, 'max': max_score, 'detail': f'历史成功率低 ({success_rate*100:.0f}%)'}
        
        return {'score': 1, 'max': max_score, 'detail': '无历史记录'}

    def update_history(self, dxcc: str, band: str, success: bool):
        """更新历史成功率缓存"""
        cache_key = f"{dxcc}_{band}"
        if cache_key not in self.history_cache:
            self.history_cache[cache_key] = 0.5  # 默认 50%
        
        old_rate = self.history_cache[cache_key]
        self.history_cache[cache_key] = old_rate * 0.9 + (1.0 if success else 0.0) * 0.1

    def _calc_time_decay(self, spot: Dict) -> float:
        """
        计算实时衰减因子
        
        Spot 时间越久，评分越低
        5 分钟内：无衰减
        30 分钟：衰减到 90%
        1 小时：衰减到 70%
        2 小时：衰减到 50%
        """
        spot_ts = spot.get('_server_ts')
        if not spot_ts:
            return 1.0
        
        age_minutes = (time.time() - spot_ts) / 60.0
        
        if age_minutes <= 5:
            return 1.0
        elif age_minutes <= 30:
            return 0.95
        elif age_minutes <= 60:
            return 0.85
        elif age_minutes <= 120:
            return 0.70
        else:
            return 0.50

    def _calc_preference_bonus(self, spot: Dict) -> float:
        """
        计算用户偏好加成
        
        关注的波段 +5 分
        特别想要的 DXCC +10 分
        """
        bonus = 0.0
        
        band = spot.get('band', '').lower()
        dxcc = spot.get('dxcc', '').upper()
        
        # 关注波段加成
        if self.my_bands and band in self.my_bands:
            bonus += 3.0
        
        # TODO: 如果有 DXCC 愿望清单，可以增加额外加成
        # if dxcc in self.wishlist:
        #     bonus += 10.0
        
        return bonus

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点间大圆距离（km）"""
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        return R * c


# 测试
if __name__ == '__main__':
    scorer = OpportunityScorerV2()
    
    test_spot = {
        'callsign': 'JA1AAA',
        'freq': 14.074,
        'band': '20m',
        'mode': 'FT8',
        'lat': 35.6762,
        'lon': 139.6503,
        'dxcc': 'Japan',
        '_server_ts': time.time() - 300  # 5 分钟前
    }
    
    test_band_counts = {'20m': 234, '40m': 180}
    test_total = 800
    test_solar = {'sfi': 105, 'sn': 80, 'k_index': 2, 'a_index': 5}
    
    result = scorer.score(test_spot, test_band_counts, test_total, test_solar, spot_dxcc_count=15)
    
    print(f"总分：{result['total']}")
    print(f"推荐：{result['recommendation']}")
    for k, v in result['factors'].items():
        print(f"  {k}: {v['score']}/{v['max']} - {v['detail']}")
