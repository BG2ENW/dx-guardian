"""
Wavelog OnlineLog API 适配器
支持从 Wavelog QSO 系统获取日志数据进行分析
"""

import requests
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta


class WavelogAPIAdapter:
    """
    Wavelog OnlineLog API 适配器
    
    API 端点:
    - GET /api.php?table=qso&action=get 获取所有 QSO
    - GET /api.php?table=qso&action=get&filter[COL_CALL]=xxx 按呼号筛选
    
    配置参数 (通过 config.py 或环境变量):
    - WAVELOG_URL: Wavelog 实例 URL (如 https://log.example.com)
    - WAVELOG_API_KEY: API 密钥
    - WAVELOG_STATION_CALLSIGN: 站台呼号 (可选)
    """
    
    def __init__(self, base_url: str, api_key: str, station_callsign: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.station_callsign = station_callsign
        
        self._cache: List[Dict] = []
        self._cache_ts: float = 0
        self._cache_ttl = 300  # 5 分钟缓存
        self._station_id: Optional[str] = None

    def _resolve_station_id(self) -> Optional[str]:
        """通过 station_info 接口解析可用 station_id。"""
        if self._station_id:
            return self._station_id

        try:
            url = f"{self.base_url}/index.php/api/station_info/{self.api_key}"
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                picked = None
                if self.station_callsign:
                    for row in data:
                        if str(row.get('station_callsign', '')).strip().upper() == self.station_callsign.strip().upper():
                            picked = row
                            break
                if picked is None:
                    for row in data:
                        if str(row.get('station_active', '')) in ('1', 'true', 'True'):
                            picked = row
                            break
                if picked is None:
                    picked = data[0]

                sid = picked.get('station_id')
                if sid is not None:
                    self._station_id = str(sid)
                    return self._station_id
        except Exception:
            return None

        return None

    def _parse_json_or_empty(self, resp: requests.Response):
        """兼容部分接口返回空 body 的情况。"""
        if not resp.text or not resp.text.strip():
            return []
        return resp.json()
    
    def _fetch(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """发送 API 请求（兼容不同 Wavelog 接口形态）。"""
        query_params = {
            'key': self.api_key,
            'type': 'json'
        }
        if params:
            query_params.update(params)

        last_error = None

        # 形态 1: /api.php?table=qso&action=get
        try:
            url = f"{self.base_url}/api.php"
            resp = requests.get(url, params=query_params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and data.get('status') == 'error':
                raise Exception(f"Wavelog API 错误：{data.get('message', 'Unknown')}")
            return data
        except Exception as e:
            last_error = e

        # 形态 2: /index.php/api/qso (POST JSON + station_id)
        try:
            url = f"{self.base_url}/index.php/api/qso"
            body = {'key': self.api_key}
            if params:
                body.update(params)
            station_id = self._resolve_station_id()
            if station_id:
                body['station_id'] = station_id
            resp = requests.post(url, json=body, timeout=30)
            resp.raise_for_status()
            data = self._parse_json_or_empty(resp)
            if isinstance(data, dict) and data.get('status') == 'error':
                raise Exception(f"Wavelog API 错误：{data.get('message', 'Unknown')}")
            return data
        except Exception as e:
            last_error = e

        # 形态 3: /index.php/api/qso (POST JSON + station_profile_id)
        try:
            url = f"{self.base_url}/index.php/api/qso"
            body = {'key': self.api_key}
            if params:
                body.update(params)
            station_id = self._resolve_station_id()
            if station_id:
                body['station_profile_id'] = station_id
            resp = requests.post(url, json=body, timeout=30)
            resp.raise_for_status()
            data = self._parse_json_or_empty(resp)
            if isinstance(data, dict) and data.get('status') == 'error':
                raise Exception(f"Wavelog API 错误：{data.get('message', 'Unknown')}")
            return data
        except Exception as e:
            last_error = e

        raise Exception(f"Wavelog API 请求失败：{last_error}")
    
    def get_all_qsos(self, days_back: int = 365) -> List[Dict]:
        """
        获取所有 QSO 记录
        
        Args:
            days_back: 获取最近 N 天的数据，默认 365 天
        
        Returns:
            QSO 记录列表
        """
        now = time.time()
        
        # 检查缓存
        if self._cache and (now - self._cache_ts) < self._cache_ttl:
            return self._cache
        
        # 计算日期范围
        from_date = datetime.now() - timedelta(days=days_back)
        from_date_str = from_date.strftime('%Y-%m-%d')
        
        # 获取 QSO 数据
        params = {
            'table': 'qso',
            'action': 'get',
            'filter[COL_QSO_DATE]': f">={from_date_str}"
        }
        
        if self.station_callsign:
            params['filter[COL_STATION_CALLSIGN]'] = self.station_callsign
        
        data = self._fetch(endpoint='qso', params=params)
        
        if not data or not isinstance(data, list):
            return []
        
        # 转换为标准格式
        self._cache = [self._normalize_qso(q) for q in data if self._is_valid_qso(q)]
        self._cache_ts = now
        
        return self._cache
    
    def get_qsos_by_call(self, callsign: str) -> List[Dict]:
        """按呼号获取 QSO 记录"""
        params = {
            'table': 'qso',
            'action': 'get',
            'filter[COL_CALL]': callsign
        }
        
        if self.station_callsign:
            params['filter[COL_STATION_CALLSIGN]'] = self.station_callsign
        
        data = self._fetch(endpoint='qso', params=params)
        
        if not data or not isinstance(data, list):
            return []
        
        return [self._normalize_qso(q) for q in data if self._is_valid_qso(q)]
    
    def _normalize_qso(self, qso: Dict) -> Dict:
        """标准化 QSO 记录格式"""
        # Wavelog 字段映射
        freq_khz = float(qso.get('COL_FREQ', 0)) * 1000 if qso.get('COL_FREQ') else 0
        
        return {
            'call': qso.get('COL_CALL', ''),
            'freq': freq_khz,
            'mode': qso.get('COL_MODE', ''),
            'band': qso.get('COL_BAND', ''),
            'dxcc': qso.get('COL_DXCC', ''),
            'grid': qso.get('COL_GRIDSQUARE', ''),
            'rst_sent': qso.get('COL_RST_SENT', ''),
            'rst_rcvd': qso.get('COL_RST_RCVD', ''),
            'qso_date': qso.get('COL_QSO_DATE', ''),
            'time_on': qso.get('COL_TIME_ON', ''),
            'comment': qso.get('COL_COMMENT', ''),
            'qsl_sent': qso.get('COL_QSL_SENT', ''),
            'qsl_rcvd': qso.get('COL_QSL_RCVD', ''),
            'lotw_sent': qso.get('COL_LOTW_QSL_SENT', ''),
            'lotw_rcvd': qso.get('COL_LOTW_QSL_RCVD', ''),
            '_source': 'wavelog',
            '_server_ts': time.time()
        }
    
    def _is_valid_qso(self, qso: Dict) -> bool:
        """验证 QSO 记录有效性"""
        return bool(qso.get('COL_CALL')) and bool(qso.get('COL_QSO_DATE'))
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        logs = self.get_all_qsos()
        
        dxcc_set = set(log['dxcc'] for log in logs if log['dxcc'])
        grid_set = set(log['grid'] for log in logs if log['grid'])
        call_set = set(log['call'] for log in logs)
        
        return {
            'total_qso': len(logs),
            'unique_dxcc': len(dxcc_set),
            'unique_calls': len(call_set),
            'unique_grids': len(grid_set),
            'source': 'wavelog',
            'cache_size': len(self._cache),
            'cache_age': int(time.time() - self._cache_ts) if self._cache_ts else 0
        }
    
    def clear_cache(self):
        """清除缓存"""
        self._cache = []
        self._cache_ts = 0


# 工厂函数
def get_wavelog_adapter(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    station_callsign: Optional[str] = None
) -> Optional[WavelogAPIAdapter]:
    """
    获取 Wavelog API 适配器实例
    
    参数优先级：
    1. 函数参数
    2. 环境变量
    3. config.py 配置
    """
    from config import WAVELOG_URL, WAVELOG_API_KEY, WAVELOG_STATION_CALLSIGN
    import os
    
    # 使用传入参数或配置文件
    url = base_url or os.getenv('WAVELOG_URL') or WAVELOG_URL
    key = api_key or os.getenv('WAVELOG_API_KEY') or WAVELOG_API_KEY
    callsign = station_callsign or os.getenv('WAVELOG_STATION_CALLSIGN') or WAVELOG_STATION_CALLSIGN
    
    if not url or not key:
        return None
    
    return WavelogAPIAdapter(url, key, callsign)
