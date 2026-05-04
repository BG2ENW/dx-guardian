"""
Callsign API 集成模块

支持 QRZ.com 和 HamQTH.com API，用于查询呼号精确信息（Grid、DXCC、CQ/ITU 分区等）

配置方式：
1. 在 .env 文件中设置 API key:
   QRZ_API_KEY=your_qrz_api_key_here
   HAMQTH_API_KEY=your_hamqth_api_key_here

2. 或在代码中直接设置:
   from callsign_api import CallsignAPI
   api = CallsignAPI(qrz_key="xxx", hamqth_key="yyy")
"""

import os
import hashlib
import time
from typing import Optional, Dict, Any
import requests


class CallsignAPI:
    """Callsign 查询 API 封装"""
    
    def __init__(self, qrz_key: Optional[str] = None, hamqth_key: Optional[str] = None):
        """
        初始化 API
        
        Args:
            qrz_key: QRZ.com API key（需要订阅 XML 数据）
            hamqth_key: HamQTH.com API key（免费）
        """
        self.qrz_key = qrz_key or os.getenv('QRZ_API_KEY')
        self.hamqth_key = hamqth_key or os.getenv('HAMQTH_API_KEY')
        
        self.qrz_session = None
        self.hamqth_session = None
        self.qrz_expires = 0
        self.hamqth_expires = 0
    
    def query(self, callsign: str, prefer: str = 'qrz') -> Optional[Dict[str, Any]]:
        """
        查询呼号信息
        
        Args:
            callsign: 呼号（如 BA5BN）
            prefer: 优先使用的 API ('qrz' 或 'hamqth')
        
        Returns:
            包含呼号信息的字典，或 None（查询失败）
            {
                'callsign': str,
                'grid': str,  # 6 位 Grid
                'dxcc': str,
                'cq_zone': int,
                'itu_zone': int,
                'lat': float,
                'lon': float,
                'country': str,
            }
        """
        if prefer == 'qrz' and self.qrz_key:
            result = self._query_qrz(callsign)
            if result:
                return result
        
        if prefer == 'hamqth' and self.hamqth_key:
            result = self._query_hamqth(callsign)
            if result:
                return result
        
        # 备用查询
        if self.qrz_key:
            result = self._query_qrz(callsign)
            if result:
                return result
        
        if self.hamqth_key:
            result = self._query_hamqth(callsign)
            if result:
                return result
        
        return None
    
    def _query_qrz(self, callsign: str) -> Optional[Dict[str, Any]]:
        """查询 QRZ.com API"""
        if not self.qrz_key:
            return None
        
        try:
            # QRZ API 需要 Session
            if not self.qrz_session or time.time() > self.qrz_expires:
                self._qrz_login()
            
            if not self.qrz_session:
                return None
            
            url = f"https://xmldata.qrz.com/xml/current/?s={self.qrz_session};callsign={callsign}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return self._parse_qrz_response(response.text)
        except Exception as e:
            print(f"QRZ API error: {e}")
        
        return None
    
    def _qrz_login(self):
        """QRZ 登录获取 Session"""
        try:
            key_hash = hashlib.md5(self.qrz_key.encode()).hexdigest()
            url = f"https://xmldata.qrz.com/xml/current/?username={key_hash};password={key_hash}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)
                session_elem = root.find('.//Session')
                if session_elem is not None:
                    sid = session_elem.findtext('Key', '')
                    timeout = int(session_elem.findtext('Timeout', '10'))
                    if sid:
                        self.qrz_session = sid
                        self.qrz_expires = time.time() + (timeout * 60 - 60)  # 提前 1 分钟过期
        except Exception as e:
            print(f"QRZ login error: {e}")
    
    def _parse_qrz_response(self, xml_text: str) -> Optional[Dict[str, Any]]:
        """解析 QRZ XML 响应"""
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_text)
            
            callsign_elem = root.find('.//Callsign')
            if callsign_elem is None:
                return None
            
            result = {
                'callsign': callsign_elem.findtext('Callsign', ''),
                'grid': callsign_elem.findtext('grid', ''),
                'dxcc': callsign_elem.findtext('dxcc', ''),
                'cq_zone': int(callsign_elem.findtext('cqzone', 0) or 0),
                'itu_zone': int(callsign_elem.findtext('ituzone', 0) or 0),
                'country': callsign_elem.findtext('country', ''),
            }
            
            # 从 Grid 推断经纬度
            if result['grid']:
                lat, lon = self._grid_to_latlon(result['grid'])
                result['lat'] = lat
                result['lon'] = lon
            
            return result if result['callsign'] else None
        except Exception as e:
            print(f"Parse QRZ error: {e}")
            return None
    
    def _query_hamqth(self, callsign: str) -> Optional[Dict[str, Any]]:
        """查询 HamQTH.com API"""
        if not self.hamqth_key:
            return None
        
        try:
            # HamQTH API 也需要 Session
            if not self.hamqth_session or time.time() > self.hamqth_expires:
                self._hamqth_login()
            
            if not self.hamqth_session:
                return None
            
            url = f"https://www.hamqth.com/xml.php?s={self.hamqth_session};callsign={callsign}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return self._parse_hamqth_response(response.text)
        except Exception as e:
            print(f"HamQTH API error: {e}")
        
        return None
    
    def _hamqth_login(self):
        """HamQTH 登录获取 Session"""
        try:
            url = f"https://www.hamqth.com/xml.php?u={self.hamqth_key};p={self.hamqth_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)
                session_elem = root.find('.//session')
                if session_elem is not None:
                    sid = session_elem.text
                    if sid:
                        self.hamqth_session = sid
                        self.hamqth_expires = time.time() + 3000  # 50 分钟
        except Exception as e:
            print(f"HamQTH login error: {e}")
    
    def _parse_hamqth_response(self, xml_text: str) -> Optional[Dict[str, Any]]:
        """解析 HamQTH XML 响应"""
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_text)
            
            search_elem = root.find('.//search')
            if search_elem is None:
                return None
            
            result = {}
            
            grid = search_elem.findtext('grid')
            if grid:
                result['grid'] = grid.strip()
                lat, lon = self._grid_to_latlon(result['grid'])
                result['lat'] = lat
                result['lon'] = lon
            
            cq_zone = search_elem.findtext('cq_zone')
            itu_zone = search_elem.findtext('itu_zone')
            
            if cq_zone:
                result['cq_zone'] = int(cq_zone)
            if itu_zone:
                result['itu_zone'] = int(itu_zone)
            
            return result if result else None
        except Exception as e:
            print(f"Parse HamQTH error: {e}")
            return None
    
    @staticmethod
    def _grid_to_latlon(grid: str) -> tuple:
        """Grid 转经纬度"""
        if not grid or len(grid) < 4:
            return None, None
        
        grid = grid.upper().strip()
        
        try:
            lon = (ord(grid[0]) - ord('A')) * 20 - 180
            lat = (ord(grid[1]) - ord('A')) * 10 - 90
            
            if len(grid) >= 4:
                lon += int(grid[2]) * 2 + 1.0
                lat += int(grid[3]) * 1 + 0.5
            
            if len(grid) >= 6:
                lon += (ord(grid[4]) - ord('A')) * (5.0/60) + (2.5/60)
                lat += (ord(grid[5]) - ord('A')) * (2.5/60) + (1.25/60)
            
            return lat, lon
        except:
            return None, None


# 导出全局实例（延迟初始化）
_api_instance: Optional[CallsignAPI] = None

def get_api() -> CallsignAPI:
    """获取 API 实例（懒加载）"""
    global _api_instance
    if _api_instance is None:
        _api_instance = CallsignAPI()
    return _api_instance


def query_callsign(callsign: str) -> Optional[Dict[str, Any]]:
    """便捷查询函数"""
    api = get_api()
    return api.query(callsign)
