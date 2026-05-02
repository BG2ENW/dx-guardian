"""
DX Guardian - VOACAP 风格传播预测模块
基于电离层物理模型，提供 HF 波段传播预测

VOACAP 使用的主要参数：
- 太阳通量指数 (SFI) - 影响 F 层电离
- K 指数 - 地磁活动
- 时间 - 影响 D/E/F 层可用性
- 距离 - 单跳/多跳传播
- 模式 - 不同模式穿透能力不同
"""
import math
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional


class VOACAPPredictor:
    """VOACAP 风格 HF 传播预测器"""

    def __init__(self):
        # 各波段的基本 MUF 因子（相对于 F2 层临界频率）
        self.band_muf_factors = {
            '160m': 1.0,   # 夜间可用
            '80m': 1.2,
            '60m': 1.5,
            '40m': 2.0,
            '30m': 2.5,
            '20m': 3.0,
            '17m': 3.5,
            '15m': 4.0,
            '12m': 4.5,
            '10m': 5.0,
            '6m': 7.0,
        }

        # 波段频率（MHz）
        self.band_freqs = {
            '160m': 1.8, '80m': 3.5, '60m': 5.3, '40m': 7.0,
            '30m': 10.1, '20m': 14.0, '17m': 18.0, '15m': 21.0,
            '12m': 24.9, '10m': 28.0, '6m': 50.0
        }

    def calculate_muf(self, sfi: float, lat: float, utc_hour: int) -> Dict[str, float]:
        """
        计算各波段的最大可用频率 (MUF)

        Args:
            sfi: 太阳通量指数 (典型值 70-200)
            lat: 纬度（影响电离层高度）
            utc_hour: UTC 时间（0-23）

        Returns:
            各波段 MUF 字典
        """
        # F2 层临界频率基础值（基于 SFI）
        foF2_base = 3.0 + (sfi - 70) / 40  # 基础 foF2 约 3-6 MHz

        # 纬度修正（高纬度 foF2 较低）
        lat_factor = 1.0 - abs(lat) / 180  # 赤道 1.0，极区 0.5

        # 时间修正（白天 foF2 高，夜间低）
        # 太阳高度角近似
        local_time_factor = self._sun_elevation_factor(utc_hour, lat)

        foF2 = foF2_base * lat_factor * local_time_factor

        # 计算各波段 MUF
        muf_dict = {}
        for band, factor in self.band_muf_factors.items():
            muf_dict[band] = foF2 * factor

        return muf_dict

    def _sun_elevation_factor(self, utc_hour: int, lat: float) -> float:
        """计算太阳高度角因子（简化模型）"""
        # 正午太阳最高
        hour_angle = abs(utc_hour - 12) / 12  # 0-1，正午为0

        # 季节因子（简化，假设春分）
        declination = 0  # 太阳赤纬

        # 太阳高度角近似
        elevation = 90 - abs(lat - declination) - hour_angle * 90
        elevation = max(0, elevation)

        # 白天因子：1.0（正午）到 0.3（夜间）
        factor = 0.3 + 0.7 * math.sin(math.radians(elevation))
        return max(0.3, min(1.0, factor))

    def predict_propagation(self,
                           from_lat: float,
                           from_lon: float,
                           to_lat: float,
                           to_lon: float,
                           sfi: float = 100,
                           k_index: float = 2.0,
                           utc_time: datetime = None) -> Dict:
        """
        预测两点之间的传播条件

        Args:
            from_lat, from_lon: 发射台坐标
            to_lat, to_lon: 接收台坐标
            sfi: 太阳通量指数
            k_index: K 指数（地磁活动）
            utc_time: UTC 时间

        Returns:
            传播预测结果
        """
        if utc_time is None:
            utc_time = datetime.now(timezone.utc)

        # 计算大圆距离
        distance_km = self._haversine(from_lat, from_lon, to_lat, to_lon)

        # 计算传播模式（单跳/多跳）
        hop_info = self._calculate_hops(distance_km)

        # 计算中点纬度（用于电离层参数）
        mid_lat = (from_lat + to_lat) / 2

        # 计算 MUF
        muf_dict = self.calculate_muf(sfi, mid_lat, utc_time.hour)

        # 各波段预测
        band_predictions = {}
        for band, freq in self.band_freqs.items():
            prediction = self._predict_band(
                band, freq, muf_dict[band],
                distance_km, hop_info,
                sfi, k_index, utc_time.hour
            )
            band_predictions[band] = prediction

        return {
            'distance_km': round(distance_km, 0),
            'hops': hop_info,
            'solar_conditions': {
                'sfi': sfi,
                'k_index': k_index,
                'utc_hour': utc_time.hour
            },
            'bands': band_predictions,
            'best_bands': self._get_best_bands(band_predictions, 3),
            'grayline_path': self._is_grayline_path(from_lat, to_lat, utc_time)
        }

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点间大圆距离（km）"""
        R = 6371  # 地球半径 km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def _calculate_hops(self, distance_km: float) -> Dict:
        """计算传播跳数"""
        # 单跳最大距离约 4000km（F2 层）
        # 单跳 E 层约 2000km
        f2_hop_max = 4000
        e_hop_max = 2000

        f2_hops = math.ceil(distance_km / f2_hop_max)
        e_hops = math.ceil(distance_km / e_hop_max)

        return {
            'distance': distance_km,
            'f2_hops': f2_hops,
            'e_hops': e_hops,
            'recommended_mode': 'F2' if f2_hops <= 2 else 'Multi-hop'
        }

    def _predict_band(self,
                     band: str,
                     freq: float,
                     muf: float,
                     distance_km: float,
                     hop_info: Dict,
                     sfi: float,
                     k_index: float,
                     utc_hour: int) -> Dict:
        """预测单个波段的条件"""

        # 基础信噪比估计
        snr_base = 20  # dB

        # MUF 因子：如果频率 > MUF，信号无法反射
        if freq > muf * 1.1:
            return {
                'band': band,
                'frequency': freq,
                'muf': round(muf, 2),
                'condition': 'CLOSED',
                'quality': 'Poor',
                'score': 0,
                'reason': f'频率 {freq}MHz > MUF {muf:.1f}MHz'
            }

        # MUF 余量（频率低于 MUF 的程度）
        muf_margin = (muf - freq) / freq

        # 距离因子
        if distance_km < 100:
            distance_factor = 0.3  # 太近，地面波
        elif distance_km < 2000:
            distance_factor = 1.0  # 最佳单跳距离
        elif distance_km < 4000:
            distance_factor = 0.9
        else:
            distance_factor = 0.8 ** (hop_info['f2_hops'] - 1)

        # K 指数因子（地磁活动影响）
        k_factor = max(0.3, 1.0 - (k_index - 2) * 0.15)

        # 时间因子（夜间低频好，白天高频好）
        is_night = utc_hour < 6 or utc_hour > 18
        if is_night and freq < 10:
            time_factor = 1.2
        elif not is_night and freq >= 14:
            time_factor = 1.1
        else:
            time_factor = 0.9

        # 综合评分 (0-100)
        score = min(100, int(
            40 * muf_margin +
            30 * distance_factor +
            20 * k_factor +
            10 * time_factor
        ))

        # 条件分类
        if score >= 80:
            condition = 'EXCELLENT'
            quality = 'Excellent'
        elif score >= 60:
            condition = 'GOOD'
            quality = 'Good'
        elif score >= 40:
            condition = 'FAIR'
            quality = 'Fair'
        else:
            condition = 'POOR'
            quality = 'Poor'

        return {
            'band': band,
            'frequency': freq,
            'muf': round(muf, 2),
            'muf_margin': round(muf_margin, 2),
            'condition': condition,
            'quality': quality,
            'score': score,
            'factors': {
                'distance': round(distance_factor, 2),
                'geomagnetic': round(k_factor, 2),
                'time': round(time_factor, 2)
            }
        }

    def _get_best_bands(self, predictions: Dict, n: int = 3) -> List[Dict]:
        """获取最佳波段"""
        sorted_bands = sorted(
            predictions.items(),
            key=lambda x: x[1].get('score', 0),
            reverse=True
        )
        return [
            {'band': band, 'score': data['score'], 'quality': data['quality']}
            for band, data in sorted_bands[:n]
            if data.get('score', 0) > 0
        ]

    def _is_grayline_path(self, lat1: float, lat2: float, utc_time: datetime) -> bool:
        """判断路径是否经过灰线区域"""
        # 简化判断：如果一端是白天，一端是夜晚
        from terminator import TerminatorCalculator
        calc = TerminatorCalculator()

        decl = calc.get_sun_declination(utc_time)

        # 计算两端的太阳高度角
        elev1 = self._sun_elevation(lat1, utc_time.hour, decl)
        elev2 = self._sun_elevation(lat2, utc_time.hour, decl)

        # 如果一端在日出/日落附近（高度角 < 6度），认为是灰线路径
        grayline_threshold = 6
        return (abs(elev1) < grayline_threshold or abs(elev2) < grayline_threshold)

    def _sun_elevation(self, lat: float, hour: int, decl: float) -> float:
        """计算太阳高度角（简化）"""
        hour_angle = (hour - 12) * 15  # 每小时 15 度
        elevation = 90 - abs(lat - decl) - abs(hour_angle) / 2
        return elevation


if __name__ == '__main__':
    predictor = VOACAPPredictor()

    # 测试：北京到纽约
    result = predictor.predict_propagation(
        from_lat=39.9, from_lon=116.4,   # 北京
        to_lat=40.7, to_lon=-74.0,       # 纽约
        sfi=120,
        k_index=2
    )

    print(f"距离: {result['distance_km']} km")
    print(f"跳数: {result['hops']}")
    print(f"最佳波段: {[b['band'] for b in result['best_bands']]}")
    print(f"灰线路径: {result['grayline_path']}")
