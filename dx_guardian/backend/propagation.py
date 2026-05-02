"""
DX Guardian - HF 传播预测模块
基于 hamqsl.com 的传播数据（数据源同 NOAA/VOACAP）
"""
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


class PropagationPredictor:
    """HF 传播预测"""

    CACHE_TIMEOUT = 300  # 5 分钟缓存

    def __init__(self):
        self._cache = None
        self._last_fetch = 0

    def get_propagation(self, force=False) -> dict:
        """获取传播预测数据"""
        now = time.time()
        if not force and self._cache and (now - self._last_fetch) < self.CACHE_TIMEOUT:
            return self._cache

        try:
            data = self._fetch()
            self._cache = data
            self._last_fetch = now
            return data
        except Exception as e:
            if self._cache:
                return {**self._cache, 'stale': True, 'error': str(e)}
            return {'error': str(e), 'bands': {}, 'vhf': []}

    def _fetch(self) -> dict:
        """从 hamqsl.com 获取传播数据"""
        url = 'https://www.hamqsl.com/solarxml.php'
        xml_data = urllib.request.urlopen(url, timeout=10).read().decode('utf-8')
        root = ET.fromstring(xml_data)

        result = {
            'bands': {},
            'vhf': [],
            'updated': None,
            'stale': False
        }

        # 解析 HF 波段传播条件
        for cond in root.findall('.//calculatedconditions/band'):
            name = cond.get('name', '')
            time_of_day = cond.get('time', '')
            quality = cond.text.strip() if cond.text else 'Unknown'

            if name not in result['bands']:
                result['bands'][name] = {}
            result['bands'][name][time_of_day] = quality

        # 解析 VHF 传播条件
        for phenomenon in root.findall('.//calculatedvhfconditions/phenomenon'):
            result['vhf'].append({
                'name': phenomenon.get('name', ''),
                'location': phenomenon.get('location', ''),
                'status': phenomenon.text.strip() if phenomenon.text else 'Unknown'
            })

        # 更新时间
        updated_el = root.find('.//solardata/updated')
        if updated_el is not None and updated_el.text:
            result['updated'] = updated_el.text.strip()

        return result

    def get_band_condition(self, band: str, is_night: bool = None) -> dict:
        """
        获取指定波段的传播条件

        Args:
            band: 波段名称（如 '20m', '40m'）
            is_night: 是否夜间（None 自动判断）

        Returns:
            {'quality': 'Good'/'Fair'/'Poor', 'score': 0-100, 'detail': ...}
        """
        prop = self.get_propagation()
        bands = prop.get('bands', {})

        # 波段映射到 hamqsl 波段组
        band_map = {
            '160m': '80m-40m', '80m': '80m-40m', '60m': '80m-40m', '40m': '80m-40m',
            '30m': '30m-20m', '20m': '30m-20m',
            '17m': '17m-15m', '15m': '17m-15m',
            '12m': '12m-10m', '10m': '12m-10m',
        }

        group = band_map.get(band, '')
        if not group or group not in bands:
            return {'quality': 'Unknown', 'score': 50, 'detail': f'{band} 无预测数据'}

        day_cond = bands[group].get('day', 'Unknown')
        night_cond = bands[group].get('night', 'Unknown')

        # 自动判断白天/夜间
        if is_night is None:
            hour_utc = datetime.now(timezone.utc).hour
            is_night = hour_utc < 6 or hour_utc >= 20

        quality = night_cond if is_night else day_cond

        # 质量评分
        score_map = {
            'Excellent': 95, 'Good': 75, 'Fair': 50, 'Poor': 25, 'Very Poor': 10,
            'Band Closed': 5, 'Unknown': 50
        }
        score = score_map.get(quality, 50)

        detail = f'白天: {day_cond} / 夜间: {night_cond}'
        if is_night:
            detail = f'夜间预测: {night_cond} (白天: {day_cond})'
        else:
            detail = f'白天预测: {day_cond} (夜间: {night_cond})'

        return {
            'quality': quality,
            'score': score,
            'day': day_cond,
            'night': night_cond,
            'detail': detail,
            'is_night': is_night
        }

    def get_all_band_summary(self) -> list:
        """获取所有波段传播条件摘要"""
        prop = self.get_propagation()
        hour_utc = datetime.now(timezone.utc).hour
        is_night = hour_utc < 6 or hour_utc >= 20

        bands_order = ['160m', '80m', '60m', '40m', '30m', '20m', '17m', '15m', '12m', '10m']
        result = []
        for band in bands_order:
            info = self.get_band_condition(band, is_night)
            result.append({
                'band': band,
                **info
            })
        return result
