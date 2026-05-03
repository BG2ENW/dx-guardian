"""
坐标解析模块（增强版）
数据源优先级:
1. Grid 方格直接转换（最精确，±5km）
2. Grid 数据库查询（29,950 条呼号-Grid 映射，±5km）
3. cty.dat 前缀 - 国家映射（317 个实体，3000+ 前缀，精确坐标）
4. DXCC 前缀库兜底（62 个前缀）

LoTW 验证：提供呼号有效性验证
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

try:
    from grid_database import GridDatabase
    GRID_DB_AVAILABLE = True
except ImportError:
    GRID_DB_AVAILABLE = False


class CoordinateResolver:
    """增强版坐标解析器"""
    
    def __init__(self):
        self.dxcc_db = {}
        self.grid_cache = {}
        self.grid_db = None
        self.china_grid_db = {}  # 中国常见呼号 Grid 数据库
        
        # 加载 Grid 数据库
        if GRID_DB_AVAILABLE:
            try:
                self.grid_db = GridDatabase()
                # 优先加载 JSON 格式
                json_path = Path(__file__).parent / 'data' / 'grid_callsign_map_extracted.json'
                if json_path.exists():
                    count = self.grid_db.load_from_json(str(json_path))
                    print(f'✅ Grid 数据库已加载：{count:,} 条呼号 -Grid 映射')
                else:
                    # 尝试加载 JTDX 原始格式
                    jtdx_path = Path(__file__).parent.parent.parent / 'grid_data.bin'
                    if jtdx_path.exists():
                        count = self.grid_db.load_jtdx_format(str(jtdx_path))
                        print(f'✅ JTDX Grid 数据库已加载：{count:,} 条记录')
            except Exception as e:
                print(f'⚠️  Grid 数据库加载失败：{e}')
                self.grid_db = None
        
        # 加载中国常见呼号 Grid 数据库
        china_grid_path = Path(__file__).parent / 'data' / 'china_callsign_grid_map.json'
        if china_grid_path.exists():
            try:
                with open(china_grid_path, 'r', encoding='utf-8') as f:
                    self.china_grid_db = json.load(f)
                print(f'✅ 中国呼号 Grid 数据库已加载：{len(self.china_grid_db):,} 条记录')
            except Exception as e:
                print(f'⚠️  中国呼号 Grid 数据库加载失败：{e}')
        
        # 加载 CTY 数据库
        if CTY_AVAILABLE:
            self.cty = get_cty_data()
            print(f'✅ CTY.DAT 已初始化')
        else:
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
        """增强版坐标解析（6 级策略）
        
        优先级：
        1. Grid 方格直接转换（PSK Reporter，最精确 ±5km）
        1.5. 中国常见呼号 Grid 数据库（±500m）
        2. JTDX Grid 数据库查询（29,950 条呼号-Grid 映射，±5km）
        3. CTY.DAT 前缀查询（317 实体，+/- 50km 散射）
        4. DXCC 前缀库兜底（62 前缀，国家中心）
        5. 未知位置（0, 0）
        
        Args:
            callsign: 呼号
            grid: Grid 方格（可选）
        
        Returns:
            dict: {lat, lon, precision, dxcc, prefix, cq, itu, lotw_verified, grid}
            precision 可能是：'grid', 'china_grid', 'grid_db', 'cty', 'dxcc', 'unknown'
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
            'grid': None
        }
        
        # 0. LOTW 验证（可选）
        if self.lotw and callsign:
            result['lotw_verified'] = self.lotw.is_active(callsign)
        
        # 1. Grid 方格（最精确，显示在 Grid 中心点）
        if grid:
            lat, lon = self._grid_to_latlon(grid)
            if lat is not None and lon is not None:
                result['lat'] = lat
                result['lon'] = lon
                result['precision'] = 'grid'
                result['grid'] = grid.upper()
                
                # 从 Grid 推断 DXCC/CQ/ITU
                dxcc_info = self._lookup_by_latlon(lat, lon)
                if dxcc_info:
                    result['dxcc'] = dxcc_info.get('name', '')
                    result['cq'] = dxcc_info.get('cq')
                    result['itu'] = dxcc_info.get('itu')
                
                return result
        
        # 1.5. 中国常见呼号 Grid 数据库（±500m 精度）
        if callsign and callsign.upper().startswith('B'):
            china_grid = self.china_grid_db.get(callsign.upper())
            if china_grid:
                lat, lon = self._grid_to_latlon(china_grid)
                if lat is not None and lon is not None:
                    result['lat'] = lat
                    result['lon'] = lon
                    result['precision'] = 'china_grid'
                    result['grid'] = china_grid.upper()
                    
                    # 从 Grid 推断 DXCC/CQ/ITU
                    dxcc_info = self._lookup_by_latlon(lat, lon)
                    if dxcc_info:
                        result['dxcc'] = dxcc_info.get('name', '')
                        result['cq'] = dxcc_info.get('cq')
                        result['itu'] = dxcc_info.get('itu')
                    
                    return result
        
        # 2. Grid 数据库查询（精确坐标）
        if self.grid_db and callsign:
            grid_from_db = self.grid_db.lookup(callsign)
            if grid_from_db:
                lat, lon = self._grid_to_latlon(grid_from_db)
                if lat is not None and lon is not None:
                    result['lat'] = lat
                    result['lon'] = lon
                    result['precision'] = 'grid_db'
                    result['grid'] = grid_from_db.upper()
                    
                    # 从 Grid 推断 DXCC/CQ/ITU
                    dxcc_info = self._lookup_by_latlon(lat, lon)
                    if dxcc_info:
                        result['dxcc'] = dxcc_info.get('name', '')
                        result['cq'] = dxcc_info.get('cq')
                        result['itu'] = dxcc_info.get('itu')
                    
                    return result
        
        # 3. CTY.DAT 前缀查询（精确坐标）
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
                # 不反推 Grid，保持 result['grid'] = None
                
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
            # 不反推 Grid，保持 result['grid'] = None
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
            # Field (2 字符): 20°×10°
            lon = (ord(grid[0]) - ord('A')) * 20 - 180
            lat = (ord(grid[1]) - ord('A')) * 10 - 90
            
            if len(grid) >= 4:
                # Square (2 数字): 2°×1°
                # + 中心点偏移（半个格子）
                lon += int(grid[2]) * 2 + 1.0
                lat += int(grid[3]) * 1 + 0.5
            
            if len(grid) >= 6:
                # Subsquare (2 字符): 5'×2.5'
                # + 中心点偏移（半个 subsquare）
                lon += (ord(grid[4]) - ord('A')) * (5.0/60) + (2.5/60)
                lat += (ord(grid[5]) - ord('A')) * (2.5/60) + (1.25/60)
            
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
    
    def _scatter_in_grid(self, callsign, center_lat, center_lon, dxcc_name=None):
        """在国家范围内分散显示（基于呼号 hash）
        
        根据国家/地区典型尺寸扩大散列范围，避免所有电台挤在中心点
        针对中国使用省份中心点提高准确性
        """
        # 中国省份中心点数据库（用于根据呼号前缀推断省份）
        china_provinces = {
            # 东北地区
            'BA': (45.8, 126.5), 'BB': (43.9, 125.3), 'BG2': (45.8, 126.5),  # 黑龙江
            'BD': (41.8, 123.4), 'BG3': (41.8, 123.4),  # 辽宁
            'BE': (43.9, 125.3),  # 吉林
            # 华北地区
            'BI': (39.9, 116.4),  # 北京
            'BT': (39.1, 117.2),  # 天津
            'BH': (38.0, 114.5), 'BG7': (38.0, 114.5),  # 河北
            'BS': (37.9, 112.6),  # 山西
            'BN': (40.8, 111.7),  # 内蒙古
            # 华东地区
            'BV': (31.2, 121.5),  # 上海
            'BF': (32.1, 118.8), 'BG5': (32.1, 118.8),  # 江苏
            'BZ': (30.3, 120.2),  # 浙江
            'BAH': (31.8, 117.3),  # 安徽
            'BBH': (36.7, 117.0),  # 山东
            'BP': (28.2, 112.9),  # 江西
            'BL': (30.6, 104.1),  # 四川
            # 华南地区
            'BY': (23.1, 113.3), 'BG8': (23.1, 113.3),  # 广东
            'BG9': (20.0, 110.3),  # 海南
            'BG6': (30.6, 114.3),  # 湖北
            # 第 7 区（南方）- BD7/BH7 通常在广东/广西
            'BD7': (23.1, 113.3), 'BH7': (23.1, 113.3),  # 广东
            # 第 6 区（中部）- BD6 在湖北
            'BD6': (30.6, 114.3),  # 湖北
            # 华中地区
            'BG4': (34.8, 113.7),  # 河南
            # 第 4 区（华东）- B4 在安徽/湖北
            'B4': (31.5, 115.0),  # 安徽/湖北边界
            # 第 3 区（华北）- B3 在山西
            'B3': (37.5, 112.0),  # 山西
            # 第 1 区（华北）- B1 在北京
            'B1': (39.9, 116.4),  # 北京
            # 西北地区
            'BX': (34.3, 108.9),  # 陕西
            'BQ': (36.1, 103.8),  # 甘肃
            'BK': (36.6, 101.8),  # 青海
            'BM': (43.8, 87.6),  # 新疆
            # 西南地区
            'BU': (25.0, 102.7),  # 云南
            'GW': (26.6, 106.7),  # 贵州
            # 特别行政区
            'VR2': (22.3, 114.2),  # 香港
        }
        
        # 根据大概经纬度判断国家尺寸
        lat_range, lon_range = 5, 8  # 默认 ±2.5-4 度
        
        # 中国 - 使用省份中心点优化
        if dxcc_name == 'China' or (20 < center_lat < 50 and 75 < center_lon < 135):
            # 尝试根据呼号前缀匹配省份
            callsign_upper = callsign.upper()
            province_center = None
            
            # 检查前缀（从长到短）
            for length in [4, 3, 2]:
                prefix = callsign_upper[:length]
                if prefix in china_provinces:
                    province_center = china_provinces[prefix]
                    break
            
            if province_center:
                # 使用省份中心点，小范围散射
                center_lat, center_lon = province_center
                lat_range, lon_range = 3, 4  # 省份内±1.5-2 度
            else:
                # 无法匹配省份，使用较大散射范围
                lat_range, lon_range = 15, 25
        
        # 低纬度 + 东经 120-150 = 日本/东南亚
        elif abs(center_lat) < 30 and 120 < center_lon < 150:
            lat_range, lon_range = 10, 12
        # 中高纬度 + 东经 20-180 = 俄罗斯/亚洲
        elif center_lat > 50 and center_lon > 20:
            lat_range, lon_range = 20, 50
        # 欧洲中部
        elif 35 < center_lat < 60 and -10 < center_lon < 40:
            lat_range, lon_range = 5, 8
        # 北美
        elif 25 < center_lat < 55 and -130 < center_lon < -50:
            lat_range, lon_range = 15, 25
        # 澳洲
        elif -45 < center_lat < -10 and 110 < center_lon < 155:
            lat_range, lon_range = 20, 30
        # 南美
        elif -55 < center_lat < 10 and -80 < center_lon < -35:
            lat_range, lon_range = 20, 25
        # 非洲
        elif -35 < center_lat < 40 and -20 < center_lon < 55:
            lat_range, lon_range = 15, 20
        # 日本/韩国 - 缩小范围避免落入海洋
        elif 33 < center_lat < 45 and 130 < center_lon < 145:
            lat_range, lon_range = 6, 8  # ±3°纬度，±4°经度
        
        hash_val = hash(callsign.upper())
        
        # 在范围内散列（±range/2 度）
        lat_offset = ((hash_val % 100) - 50) / 100.0 * lat_range
        lon_offset = (((hash_val >> 10) % 100) - 50) / 100.0 * lon_range
        
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
