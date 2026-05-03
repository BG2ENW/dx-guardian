"""
坐标解析模块（增强版）
数据源优先级:
1. Grid 方格直接转换（最精确，±5km）
2. cty.dat 前缀 - 国家映射（317 个实体，3000+ 前缀，精确坐标）
3. DXCC 前缀库兜底（62 个前缀）

LoTW 验证: 提供呼号有效性验证
"""
import json
import re
import math
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from config import DXCC_PREFIX_FILE

# 外部数据集成
try:
    from cty_parser import get_cty_data
    CTY_AVAILABLE = True
except ImportError:
    CTY_AVAILABLE = False

try:
    from lotw_loader import get_lotw_database
    LOTW_AVAILABLE = True
except ImportError:
    LOTW_AVAILABLE = False


class CoordinateResolver:
    """增强版坐标解析器"""
    
    def __init__(self):
        self.dxcc_db = {}
        self.grid_cache = {}
        
        # 加载 CTY 数据库
        if CTY_AVAILABLE:
            self.cty = get_cty_data()
            print(f'✅ CTY.DAT 已初始化')
        else:
            self.cty = None
        self.cty = None
        
        # 加载 LOTW 数据库
        if LOTW_AVAILABLE:
            self.lotw = get_lotw_database()
        else:
            self.lotw = None
        
        self._load_dxcc_db()
    
    def _load_dxcc_db(self):
        """加载 DXCC 前缀库兜底"""
        try:
            with open(DXCC_PREFIX_FILE, 'r', encoding='utf-8') as f:
                self.dxcc_db = json.load(f)
            print(f'✅ DXCC 前缀库已加载：{len(self.dxcc_db)} 个前缀')
        except Exception as e:
            print(f'❌ DXCC 前缀库加载失败：{e}')
            self.dxcc_db = {}
    
    def resolve(self, callsign, grid=None):
        """增强版坐标解析（4 级策略）
        
        Args:
            callsign: 呼号
            grid: Grid 方格（可选）
        
        Returns:
            dict: {lat, lon, precision, dxcc, prefix, cq, itu, lotw_verified, grid_loc}
        """
        result = {
            'lat': 0.0,
            'lon': 0.0,
            'precision': 'unknown',
            'dxcc': '',
            'prefix': '',
            'cq': None,
            'itu': None,
            'lotw_verified': False,
            'grid_loc': None
        }
        
        # 0. LOTW 验证（可选）
        if self.lotw and callsign:
            result['lotw_verified'] = self.lotw.is_active(callsign)
        
        # 1. Grid 方格（最精确）
        if grid:
            lat, lon = self._grid_to_latlon(grid)
            if lat is not None and lon is not None:
                result['lat'] = lat
                result['lon'] = lon
                result['precision'] = 'grid'
                result['grid_loc'] = grid.upper()
                
                # 从 Grid 推断 DXCC
                dxcc_info = self._lookup_by_latlon(lat, lon)
                if dxcc_info:
                    result['dxcc'] = dxcc_info.get('entity', '')
                    result['prefix'] = dxcc_info.get('prefix', '')
                    result['cq'] = dxcc_info.get('cq')
                    result['itu'] = dxcc_info.get('itu')
                
                return result
        
        # 2. CTY.DAT 前缀查询（精确坐标）
        if CTY_AVAILABLE and self.cty:
            cty_info = self.cty.lookup(callsign)
            if cty_info:
                lat, lon = self._scatter_in_grid(callsign, cty_info['lat'], cty_info['lon'])
                result['lat'] = lat
                result['lon'] = lon
                result['precision'] = 'cty'
                result['dxcc'] = cty_info['name']
                result['cq'] = cty_info['cq']
                result['itu'] = cty_info['itu']
                result['grid_loc'] = self._latlon_to_grid(lat, lon)
                
                # 查找匹配的前缀
                for length in range(min(7, len(callsign)), 0, -1):
                    if callsign[:length] in self.cty.prefix_map:
                        result['prefix'] = callsign[:length]
                        break
                
                return result
        
        # 3. DXCC 简库兜底
        dxcc_info = self._lookup_dxcc(callsign)
        if dxcc_info and dxcc_info.get('lat') != 0 and dxcc_info.get('lon') != 0:
            lat, lon = self._scatter_in_grid(callsign, dxcc_info['lat'], dxcc_info['lon'])
            result['lat'] = lat
            result['lon'] = lon
            result['precision'] = 'dxcc'
            result['dxcc'] = dxcc_info.get('entity', '')
            result['prefix'] = dxcc_info.get('prefix', '')
            result['grid_loc'] = self._latlon_to_grid(lat, lon)
            return result
        
        # 4. 未知
        return result
    
    def _lookup_dxcc(self, callsign):
        """查询 DXCC 兜底数据库"""
        callsign = callsign.upper().strip()
        
        # 特殊处理 portable/mobile 操作
        base_call = callsign.split('/')[0]
        
        for length in range(min(6, len(base_call)), 0, -1):
            prefix = base_call[:length]
            
            if prefix in self.dxcc_db:
                entry = self.dxcc_db[prefix]
                return {
                    'entity': entry.get('dxcc', ''),
                    'lat': entry.get('lat', 0),
                    'lon': entry.get('lon', 0),
                    'prefix': prefix
                }
        
        return None
    
    def _lookup_by_latlon(self, lat, lon):
        """根据坐标反查 DXCC 实体（简化版，用 CTY 数据库）"""
        if not self.cty:
            return None
        
        # 粗略查找最近的实体（实际应该用多边形判断）
        best_match = None
        best_dist = float('inf')
        
        for entity_name, entity in self.cty.entities.items():
            dist = math.sqrt((entity['lat'] - lat)**2 + (entity['lon'] - lon)**2)
            if dist < best_dist:
                best_dist = dist
                best_match = entity
        
        return best_match
    
    def _grid_to_latlon(self, grid):
        """Grid 方格转经纬度（6 位）"""
        if not grid or len(grid) < 4:
            return None, None
        
        grid = grid.upper().strip()
        
        try:
            # Field (2 字符)
            lon = (ord(grid[0]) - ord('A')) * 20 - 180
            lat = (ord(grid[1]) - ord('A')) * 10 - 90
            
            if len(grid) >= 4:
                # Square (2 数字)
                lon += int(grid[2]) * 2
                lat += int(grid[3]) * 1
            
            if len(grid) >= 6:
                # Subsquare (2 字符)
                lon += (ord(grid[4]) - ord('A')) * (5.0/60) + (1.0/60)
                lat += (ord(grid[5]) - ord('A')) * (2.5/60) + (1.0/60)
            
            return lat, lon
        except:
            return None, None
    
    def _latlon_to_grid(self, lat, lon):
        """经纬度转 Grid 方格（6 位）"""
        if lat < -90 or lat > 90 or lon < -180 or lon > 180:
            return None
        
        lon += 180
        lat += 90
        
        field_lon = int(lon / 20)
        field_lat = int(lat / 10)
        lon -= field_lon * 20
        lat -= field_lat * 10
        
        square_lon = int(lon / 2)
        square_lat = int(lat / 1)
        lon -= square_lon * 2
        lat -= square_lat * 1
        
        sub_lon = int(lon / (5.0/60))
        sub_lat = int(lat / (2.5/60))
        
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWX'
        
        return (chars[field_lon] + chars[field_lat] +
                str(square_lon) + str(square_lat) +
                chars[sub_lon] + chars[sub_lat])
    
    def _scatter_in_grid(self, callsign, center_lat, center_lon):
        """在国家中心 Grid 内分散显示（基于呼号 hash）"""
        hash_val = hash(callsign.upper())
        
        lat_offset = ((hash_val % 1000) - 500) / 100.0
        lon_offset = (((hash_val >> 10) % 1000) - 500) / 100.0
        
        lat = center_lat + lat_offset
        lon = center_lon + lon_offset
        
        return lat, lon


# 单例模式
_resolver_instance = None

def get_resolver() -> CoordinateResolver:
    """获取解析器单例"""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = CoordinateResolver()
    return _resolver_instance

def resolve_coordinates(callsign, grid=None):
    """便捷函数"""
    return get_resolver().resolve(callsign, grid)
