"""
DX Guardian - 波段开放时间预测
预测未来24小时各波段的开放情况
"""
import math
from datetime import datetime, timezone, timedelta


class BandOpeningPredictor:
    """波段开放时间预测器"""

    def __init__(self):
        self.band_info = {
            '160m': {'freq': 1.8, 'type': 'night'},
            '80m': {'freq': 3.5, 'type': 'night'},
            '60m': {'freq': 5.3, 'type': 'transition'},
            '40m': {'freq': 7.0, 'type': 'night'},
            '30m': {'freq': 10.1, 'type': 'day'},
            '20m': {'freq': 14.0, 'type': 'day'},
            '17m': {'freq': 18.0, 'type': 'day'},
            '15m': {'freq': 21.0, 'type': 'day'},
            '12m': {'freq': 24.9, 'type': 'day'},
            '10m': {'freq': 28.0, 'type': 'day'},
            '6m': {'freq': 50.0, 'type': 'sporadic'},
        }

    def predict_24h(self, sfi: float = 100, k_index: float = 2.0,
                    lat: float = 45.0) -> list:
        """预测未来24小时各波段开放情况

        Returns:
            每小时预测数据 [{hour, bands: {band: {open, quality, score}}}, ...]
        """
        now = datetime.now(timezone.utc)
        forecast = []

        for h in range(24):
            future_time = now + timedelta(hours=h)
            hour = future_time.hour

            # 判断日夜
            is_night = hour < 6 or hour > 18
            is_sunrise = 5 <= hour <= 7
            is_sunset = 17 <= hour <= 19
            is_noon = 10 <= hour <= 14

            # 太阳高度因子
            sun_factor = self._sun_factor(hour, lat)

            hour_data = {
                'hour': hour,
                'label': f'{hour:02d}:00',
                'bands': {}
            }

            for band, info in self.band_info.items():
                freq = info['freq']
                btype = info['type']

                score = 0
                open_ = False

                if btype == 'night' and is_night:
                    score = 80
                    open_ = True
                elif btype == 'night' and (is_sunrise or is_sunset):
                    score = 50
                    open_ = True
                elif btype == 'day' and is_night:
                    score = 20
                elif btype == 'day' and is_noon:
                    score = 80 + min(20, sfi / 10)
                    open_ = True
                elif btype == 'day' and (is_sunrise or is_sunset):
                    score = 60
                    open_ = True
                elif btype == 'transition' and (is_sunrise or is_sunset):
                    score = 90
                    open_ = True
                elif btype == 'sporadic':
                    score = min(30, sfi / 5)
                    if sfi > 150:
                        score += 20
                        open_ = True

                # K指数衰减
                if k_index > 3:
                    score *= max(0.3, 1 - (k_index - 3) * 0.15)

                # 质量标签
                if score >= 80:
                    quality = '优秀'
                elif score >= 60:
                    quality = '良好'
                elif score >= 40:
                    quality = '一般'
                elif score >= 20:
                    quality = '较差'
                else:
                    quality = '关闭'

                hour_data['bands'][band] = {
                    'score': round(score),
                    'quality': quality,
                    'open': open_
                }

            forecast.append(hour_data)

        return forecast

    def _sun_factor(self, hour: int, lat: float) -> float:
        """太阳高度因子（0-1）"""
        decl = 23.44 * math.sin(math.radians((360 / 365) * (datetime.now(timezone.utc).timetuple().tm_yday - 81)))
        ha = abs(hour - 12) * 15
        elev = 90 - abs(lat - decl) - ha / 2
        return max(0, math.sin(math.radians(elev)))


if __name__ == '__main__':
    pred = BandOpeningPredictor()
    result = pred.predict_24h(sfi=120, k_index=2)
    print(f"预测完成：{len(result)} 小时")
    for h in result[:3]:
        print(f"  {h['label']}: 开放波段 {[b for b, v in h['bands'].items() if v['open']]}")
