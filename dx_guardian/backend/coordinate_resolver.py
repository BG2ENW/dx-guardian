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
        
        # 中国省份前缀映射（用于 resolve 函数直接访问）
        # 格式：前缀 -> (纬度，经度)
        # 优先级：3 字符前缀 (含数字) > 2 字符前缀 > 数字分区兜底
        self.china_provinces_for_resolve = {
            # ===== 标准字母前缀（按主要分区）=====
            # 东北地区（2 区为主）
            'BA': (45.8, 126.5),  # 黑龙江
            'BB': (43.9, 125.3),  # 吉林
            'BC': (41.8, 123.4),  # 辽宁
            
            # 华北地区（1 区为主）
            'BE': (38.0, 114.5),  # 河北
            'BF': (39.1, 117.2),  # 天津
            'BG': (39.9, 116.4),  # 北京
            'BH': (37.9, 112.6),  # 山西
            'BI': (39.9, 116.4),  # 北京新增
            'BJ': (38.0, 114.5),  # 河北新增
            'BK': (39.1, 117.2),  # 天津新增
            'BL': (40.8, 111.7),  # 内蒙古
            
            # 华东地区（4 区为主）
            'BM': (36.7, 117.0),  # 山东
            'BN': (32.1, 118.8),  # 江苏
            'BO': (30.3, 120.2),  # 浙江
            'BP': (31.8, 117.3),  # 安徽
            'BQ': (31.2, 121.5),  # 上海
            
            # 东南地区（5 区为主）
            'BR': (26.1, 119.3),  # 福建
            'BS': (28.2, 112.9),  # 江西
            'BT': (28.2, 112.9),  # 湖南
            
            # 华中地区（6 区为主）
            'BU': (30.6, 114.3),  # 湖北
            'BV': (34.8, 113.7),  # 河南
            
            # 华南地区（7 区为主）
            'BW': (23.1, 113.3),  # 广东
            'BX': (22.8, 108.3),  # 广西
            'BY': (20.0, 110.3),  # 海南
            
            # 西南地区（8 区为主）
            'BZ': (30.6, 104.1),  # 四川
            
            # ===== 按数字分区的通配前缀 =====
            'BD': (45.0, 125.0),  # BD 默认 2 区，具体按数字
            'B1': (39.9, 116.4),  # 1 区兜底
            'B2': (45.0, 125.0),  # 2 区兜底
            'B3': (34.3, 108.9),  # 3 区兜底
            'B4': (32.1, 118.8),  # 4 区兜底
            'B5': (28.0, 116.0),  # 5 区兜底
            'B6': (30.6, 114.3),  # 6 区兜底
            'B7': (23.1, 113.3),  # 7 区兜底
            'B8': (25.0, 102.7),  # 8 区兜底
            'B9': (29.6, 91.1),   # 9 区兜底
            
            # ===== 特别行政区 =====
            'VR2': (22.3, 114.2),  # 香港
        }
        
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
                
                # DXCC 根据呼号前缀判断（不从 Grid 反推，避免坐标偏差导致国家判断错误）
                result['dxcc'] = self._dxcc_from_callsign(callsign)
                if not result['dxcc']:
                    dxcc_info = self._lookup_by_latlon(lat, lon)
                    if dxcc_info:
                        result['dxcc'] = dxcc_info.get('name', '')
                
                # CQ 分区：中国呼号根据数字，其他国家从 CTY
                if callsign and callsign.upper().startswith('B') and self._dxcc_from_callsign(callsign) == 'China':
                    result['cq'] = self._china_cq_zone_from_callsign(callsign)
                    result['itu'] = 44
                
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
                    
                    # DXCC 固定为中国（呼号前缀判断）
                    result['dxcc'] = 'China'
                    result['cq'] = self._china_cq_zone_from_callsign()
                    result['itu'] = 44
                    
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
                    
                    # DXCC 根据呼号前缀判断（不从 Grid 反推）
                    result['dxcc'] = self._dxcc_from_callsign(callsign)
                    if not result['dxcc']:
                        dxcc_info = self._lookup_by_latlon(lat, lon)
                        if dxcc_info:
                            result['dxcc'] = dxcc_info.get('name', '')
                    
                    # CQ 分区：中国呼号根据数字
                    if callsign.upper().startswith('B') and result['dxcc'] == 'China':
                        result['cq'] = self._china_cq_zone_from_callsign(callsign)
                        result['itu'] = 44
                    
                    return result
        
        # 3. CTY.DAT 前缀查询（精确坐标）
        if CTY_AVAILABLE and self.cty:
            # 特殊地区优先处理（使用精确坐标）
            callsign_upper = callsign.upper()
            
            # 香港 VR2
            if callsign_upper.startswith('VR2'):
                lat, lon = self._scatter_in_grid(callsign, 22.3, 114.2, dxcc_name='Hong Kong')
                result['lat'] = lat
                result['lon'] = lon
                result['dxcc'] = 'Hong Kong'
                result['cq'] = 24
                result['itu'] = 44
                result['precision'] = 'cty'
                return result
            
            # 澳门 XX9
            if callsign_upper.startswith('XX9'):
                lat, lon = self._scatter_in_grid(callsign, 22.2, 113.5, dxcc_name='Macao')
                result['lat'] = lat
                result['lon'] = lon
                result['dxcc'] = 'Macao'
                result['cq'] = 24
                result['itu'] = 44
                result['precision'] = 'cty'
                return result
            
            # 斯卡伯勒浅滩 BS7（黄岩岛）
            if callsign_upper.startswith('BS7'):
                lat, lon = self._scatter_in_grid(callsign, 15.08, 117.72, dxcc_name='Scarborough Reef')
                result['lat'] = lat
                result['lon'] = lon
                result['dxcc'] = 'Scarborough Reef'
                result['cq'] = 27
                result['itu'] = 50
                result['precision'] = 'cty'
                return result
            
            # 法国海外领地（CTY 经常识别错误，手动覆盖，不散射）
            if callsign_upper.startswith('FT5W'):
                # 阿姆斯特丹岛 - 小散射
                lat, lon = self._scatter_in_grid(callsign, -37.83, 77.55, dxcc_name='Amsterdam Island')
                result['lat'] = lat
                result['lon'] = lon
                result['dxcc'] = 'Amsterdam Island'
                result['cq'] = 39
                result['itu'] = 68
                result['precision'] = 'cty'
                return result
            
            if callsign_upper.startswith('FT5Z'):
                lat, lon = self._scatter_in_grid(callsign, -46.43, 51.80, dxcc_name='Crozet Island')
                result['lat'] = lat
                result['lon'] = lon
                result['dxcc'] = 'Crozet Island'
                result['cq'] = 39
                result['itu'] = 68
                result['precision'] = 'cty'
                return result
            
            if callsign_upper.startswith('FT5X'):
                lat, lon = self._scatter_in_grid(callsign, 10.30, -109.22, dxcc_name='Clipperton Island')
                result['lat'] = lat
                result['lon'] = lon
                result['dxcc'] = 'Clipperton Island'
                result['cq'] = 7
                result['itu'] = 9
                result['precision'] = 'cty'
                return result
            
            cty_info = self.cty.lookup(callsign)
            if cty_info:
                # 中国呼号特殊处理：强制识别被 CTY 错误识别的中国呼号
                callsign_upper = callsign.upper()
                
                # 中国呼号识别规则：
                # 1. B 开头 + 第二位字母为 A-Z + 第三位数字 1-9 = 中国
                # 2. 但排除已知的非中国前缀（如 JA, BV(Taiwan), VR2(HK), XX9(Macao) 等）
                non_china_prefixes = ['JA', 'KA', 'LA', 'MA', 'NA', 'OA', 'PA', 'RA', 'SA', 'TA', 'VA', 'WA', 'XA', 'YA', 'ZA',
                                      'JE', 'JF', 'JG', 'JH', 'JI', 'JJ', 'JK', 'JL', 'JM', 'JN', 'JO', 'JP', 'JQ', 'JR', 'JS', 'JT', 'JU', 'JV', 'JW', 'JX', 'JY', 'JZ',
                                      'BV', 'BX']  # BV/BX = Taiwan
                
                # 中国呼号识别规则：
                # 1. B + 字母 + 数字 1-9（现代格式，如 BA5BN）
                # 2. B + 数字 1-9 + 字母（早期格式，如 B1CRA）
                is_potential_china = False
                china_digit = None
                
                if callsign_upper.startswith('B') and len(callsign_upper) >= 3 and callsign_upper[:2] not in non_china_prefixes:
                    # 规则 1：B + 字母 + 数字 1-9
                    if callsign_upper[1].isalpha() and len(callsign_upper) >= 3 and callsign_upper[2].isdigit() and callsign_upper[2] in '123456789':
                        is_potential_china = True
                        china_digit = callsign_upper[2]
                    # 规则 2：B + 数字 1-9 + 字母（早期格式，如 B1CRA）
                    elif callsign_upper[1].isdigit() and callsign_upper[1] in '123456789' and len(callsign_upper) >= 3 and callsign_upper[2].isalpha():
                        is_potential_china = True
                        china_digit = callsign_upper[1]
                
                if is_potential_china and china_digit:
                    # 按数字分区定位（最高优先级）
                    zone_map = {
                        '1': (39.9, 116.4),  # 华北（北京/天津/河北/山西/内蒙古）
                        '2': (45.0, 125.0),  # 东北（辽宁/吉林/黑龙江）
                        '3': (34.3, 108.9),  # 西北（陕西/甘肃/宁夏/青海/新疆）
                        '4': (32.1, 118.8),  # 华东（上海/江苏/浙江/安徽/山东）
                        '5': (28.0, 116.0),  # 东南（江西/福建/湖南）
                        '6': (30.6, 114.3),  # 华中（湖北/河南）
                        '7': (23.1, 113.3),  # 华南（广东/广西/海南）
                        '8': (25.0, 102.7),  # 西南（四川/重庆/贵州/云南）
                        '9': (29.6, 91.1),   # 西藏
                    }
                    province_pos = zone_map.get(china_digit)
                    
                    # 如果有 3 字符前缀精确匹配（如 BD2），则覆盖
                    prefix_key_3 = callsign_upper[:3] if len(callsign_upper) >= 3 else None
                    if prefix_key_3 and prefix_key_3 in self.china_provinces_for_resolve:
                        province_pos = self.china_provinces_for_resolve[prefix_key_3]
                    
                    if province_pos:
                        lat, lon = self._scatter_in_grid(callsign, province_pos[0], province_pos[1], dxcc_name='China')
                        result['lat'] = lat
                        result['lon'] = lon
                        result['precision'] = 'china_province'
                        result['dxcc'] = 'China'
                        result['cq'] = int(china_digit)
                        result['itu'] = 44
                        result['grid'] = None
                        return result
                
                # 非中国呼号或无省份匹配，使用 CTY 原逻辑
                lat, lon = self._scatter_in_grid(callsign, cty_info['lat'], cty_info['lon'], dxcc_name=cty_info['name'])
                result['lat'] = lat
                result['lon'] = lon
                result['dxcc'] = cty_info['name']
                result['cq'] = cty_info['cq']
                result['itu'] = cty_info['itu']
                
                # 中国呼号检查省份匹配
                if cty_info['name'] == 'China':
                    callsign_upper = callsign.upper()
                    province_matched = False
                    # 中国省份前缀（按字母分区）
                    china_prefixes = [
                        # 东北（2 区）
                        'BA', 'BA2', 'BB', 'BB2', 'BC', 'BC2', 'BD', 'BD2', 'BG2', 'BG3',
                        # 华北（1 区）
                        'BE', 'BE1', 'BF', 'BF1', 'BG', 'BG1', 'BH', 'BH1', 'BI', 'BI1', 'BJ', 'BJ1', 'BK', 'BK1', 'BL', 'BL1', 'B1',
                        # 华东（4 区）
                        'BM', 'BM4', 'BN', 'BN4', 'BO', 'BO4', 'BP', 'BP4', 'BQ', 'BQ4', 'B4', 'BD4',
                        # 东南（5 区）
                        'BR', 'BR5', 'BS', 'BS5', 'BT', 'BT5', 'B5', 'BD5',
                        # 华中（6 区）
                        'BU', 'BU6', 'BV', 'BV6', 'B6', 'BD6', 'BG6', 'BH6',
                        # 华南（7 区）
                        'BW', 'BW7', 'BX', 'BX7', 'BY', 'BY7', 'B7', 'BD7', 'BH7', 'BG8',
                        # 西南（8/9 区）
                        'BZ', 'BZ8', 'CA', 'CA8', 'CB', 'CB8', 'CC', 'CC8', 'CD', 'CD9', 'B8', 'BD8', 'BH8', 'BD9', 'BH9',
                        # 西北（3 区）
                        'CE', 'CE3', 'CF', 'CF3', 'CG', 'CG3', 'CH', 'CH3', 'CI', 'CI3', 'B3', 'BX3', 'BH3',
                        # 特别行政区
                        'VR2', 'XX9',
                    ]
                    for prefix in china_prefixes:
                        if callsign_upper.startswith(prefix):
                            province_matched = True
                            break
                    result['precision'] = 'china_province' if province_matched else 'cty'
                else:
                    result['precision'] = 'cty'
                
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
            lat, lon = self._scatter_in_grid(callsign, dxcc_info['lat'], dxcc_info['lon'], dxcc_name=dxcc_info.get('entity', ''))
            result['lat'] = lat
            result['lon'] = lon
            result['precision'] = 'dxcc'
            result['dxcc'] = dxcc_info.get('entity', '')
            result['prefix'] = dxcc_info.get('prefix', '')
            # 不反推 Grid，保持 result['grid'] = None
            return result
        
        # 4. API 查询（QRZ/HamQTH，需要配置 API key）
        try:
            from callsign_api import query_callsign
            api_result = query_callsign(callsign)
            if api_result and api_result.get('grid'):
                # 使用 API 返回的 Grid 转换为坐标
                lat = api_result.get('lat')
                lon = api_result.get('lon')
                if lat is not None and lon is not None:
                    result['lat'] = lat
                    result['lon'] = lon
                    result['grid'] = api_result['grid'].upper()
                    result['precision'] = 'api'
                    result['dxcc'] = api_result.get('dxcc', '')
                    result['cq'] = api_result.get('cq_zone')
                    result['itu'] = api_result.get('itu_zone')
                    return result
        except ImportError:
            pass  # API 模块未配置，跳过
        except Exception as e:
            print(f"API query error: {e}")  # 日志记录
        
        # 5. 未知
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
    
    def _dxcc_from_callsign(self, callsign=None):
        """根据呼号前缀判断 DXCC 实体（不依赖坐标）"""
        if not callsign:
            return ''
        
        callsign_upper = callsign.upper().strip()
        if not callsign_upper:
            return ''
        
        # 中国 B 前缀
        if callsign_upper.startswith('B') and callsign_upper[:2] not in ['BV', 'BX']:
            return 'China'
        
        # 台湾
        if callsign_upper.startswith(('BV', 'BX')):
            return 'Taiwan'
        
        # 香港
        if callsign_upper.startswith('VR2'):
            return 'Hong Kong'
        
        # 澳门
        if callsign_upper.startswith('XX9'):
            return 'Macao'
        
        # 黄岩岛
        if callsign_upper.startswith('BS7'):
            return 'Scarborough Reef'
        
        # 韩国
        if callsign_upper.startswith('HL'):
            return 'Republic of Korea'
        
        # 朝鲜
        if callsign_upper.startswith('P5'):
            return 'DPR of Korea'
        
        # 日本
        if callsign_upper.startswith('J') and callsign_upper[:2] in ['JA', 'JE', 'JF', 'JG', 'JH', 'JI', 'JJ', 'JK', 'JL', 'JM', 'JN', 'JO', 'JP', 'JQ', 'JR', 'JS', 'JT', 'JU', 'JV', 'JW', 'JX', 'JY', 'JZ']:
            return 'Japan'
        
        # CTY 查询兜底
        if CTY_AVAILABLE and self.cty:
            cty_info = self.cty.lookup(callsign_upper)
            if cty_info:
                return cty_info.get('name', '')
        
        return ''
    
    def _cq_itu_from_callsign(self):
        """根据呼号前缀判断 CQ/ITU 分区"""
        return None  # 由具体分支单独处理
    
    def _china_cq_zone_from_callsign(self, callsign):
        """中国呼号按数字分区判断 CQ 分区（1-9 区）"""
        if not callsign:
            return 24
        
        callsign_upper = callsign.upper()
        
        # B + 数字 + 字母 格式（早期格式，如 B1CRA）
        if len(callsign_upper) >= 3 and callsign_upper.startswith('B') and callsign_upper[1].isdigit() and callsign_upper[1] in '123456789':
            return int(callsign_upper[1])
        
        # B + 字母 + 数字 格式（现代格式，如 BA5BN）
        if len(callsign_upper) >= 3 and callsign_upper.startswith('B') and callsign_upper[2].isdigit() and callsign_upper[2] in '123456789':
            return int(callsign_upper[2])
        
        return 24  # 默认
    
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
        callsign_upper = callsign.upper()
        
        # 小岛屿领地 - 不散射或极小散射，避免落入海洋
        if dxcc_name in ('Amsterdam Island', 'Crozet Island', 'Clipperton Island',
                         'Scarborough Reef', 'Hong Kong', 'Macao'):
            # 极小散射±0.5 度
            hash_val = hash(callsign_upper)
            lat_offset = ((hash_val % 100) - 50) / 100.0 * 1.0
            lon_offset = (((hash_val >> 10) % 100) - 50) / 100.0 * 1.0
            return center_lat + lat_offset, center_lon + lon_offset
        # 中国省份中心点数据库（用于根据呼号前缀推断省份）
        china_provinces = {
            # ===== 东北地区（2 区：辽宁、吉林、黑龙江）=====
            'BA': (45.8, 126.5), 'BA2': (45.8, 126.5),  # 黑龙江
            'BB': (43.9, 125.3), 'BB2': (43.9, 125.3),  # 吉林
            'BC': (41.8, 123.4), 'BC2': (41.8, 123.4),  # 辽宁
            'BD': (45.0, 125.0), 'BD2': (45.0, 125.0),  # 东北通称
            'BG2': (45.8, 126.5), 'BG3': (41.8, 123.4),  # BG 按数字分区
            
            # ===== 华北地区（1 区：北京、天津、河北、山西、内蒙古）=====
            'BE': (38.0, 114.5), 'BE1': (38.0, 114.5),  # 河北
            'BF': (39.1, 117.2), 'BF1': (39.1, 117.2),  # 天津
            'BG': (39.9, 116.4), 'BG1': (39.9, 116.4),  # 北京
            'BH': (37.9, 112.6), 'BH1': (37.9, 112.6),  # 山西
            'BI': (39.9, 116.4), 'BI1': (39.9, 116.4),  # 北京（新增）
            'BJ': (38.0, 114.5), 'BJ1': (38.0, 114.5),  # 河北（新增）
            'BK': (39.1, 117.2), 'BK1': (39.1, 117.2),  # 天津（新增）
            'BL': (40.8, 111.7), 'BL1': (40.8, 111.7),  # 内蒙古
            
            # ===== 华东地区（4 区：上海、江苏、浙江、安徽、山东）=====
            'BM': (36.7, 117.0), 'BM4': (36.7, 117.0),  # 山东
            'BN': (32.1, 118.8), 'BN4': (32.1, 118.8),  # 江苏
            'BO': (30.3, 120.2), 'BO4': (30.3, 120.2),  # 浙江
            'BP': (31.8, 117.3), 'BP4': (31.8, 117.3),  # 安徽
            'BQ': (31.2, 121.5), 'BQ4': (31.2, 121.5),  # 上海
            'B4': (32.1, 118.8), 'BD4': (32.1, 118.8),  # 4 区通称
            
            # ===== 东南地区（5 区：江西、福建、湖南）=====
            'BR': (26.1, 119.3), 'BR5': (26.1, 119.3),  # 福建
            'BS': (28.2, 112.9), 'BS5': (28.2, 112.9),  # 江西
            'BT': (28.2, 112.9), 'BT5': (28.2, 112.9),  # 湖南
            'B5': (28.0, 116.0), 'BD5': (28.0, 116.0),  # 5 区通称
            
            # ===== 华中地区（6 区：湖北、河南）=====
            'BU': (30.6, 114.3), 'BU6': (30.6, 114.3),  # 湖北
            'BV': (34.8, 113.7), 'BV6': (34.8, 113.7),  # 河南
            'B6': (30.6, 114.3), 'BD6': (30.6, 114.3),  # 6 区通称
            'BG6': (30.6, 114.3), 'BH6': (30.6, 114.3),  # 按数字分区
            
            # ===== 华南地区（7 区：广东、广西、海南）=====
            'BW': (23.1, 113.3), 'BW7': (23.1, 113.3),  # 广东
            'BX': (22.8, 108.3), 'BX7': (22.8, 108.3),  # 广西
            'BY': (20.0, 110.3), 'BY7': (20.0, 110.3),  # 海南
            'B7': (23.1, 113.3), 'BD7': (23.1, 113.3),  # 7 区通称
            'BH7': (23.1, 113.3), 'BG8': (23.1, 113.3),  # 按数字分区
            
            # ===== 西南地区（8 区：四川、重庆、贵州、云南、西藏）=====
            'BZ': (30.6, 104.1), 'BZ8': (30.6, 104.1),  # 四川
            'CA': (29.6, 106.7), 'CA8': (29.6, 106.7),  # 重庆
            'CB': (26.6, 106.7), 'CB8': (26.6, 106.7),  # 贵州
            'CC': (25.0, 102.7), 'CC8': (25.0, 102.7),  # 云南
            'CD': (29.6, 91.1), 'CD9': (29.6, 91.1),   # 西藏
            'B8': (25.0, 102.7), 'BD8': (25.0, 102.7), 'BH8': (25.0, 102.7),  # 8 区通称
            
            # ===== 西北地区（3 区：陕西、甘肃、宁夏、青海、新疆）=====
            'CE': (34.3, 108.9), 'CE3': (34.3, 108.9),  # 陕西
            'CF': (36.1, 103.8), 'CF3': (36.1, 103.8),  # 甘肃
            'CG': (38.5, 106.3), 'CG3': (38.5, 106.3),  # 宁夏
            'CH': (36.6, 101.8), 'CH3': (36.6, 101.8),  # 青海
            'CI': (43.8, 87.6), 'CI3': (43.8, 87.6),   # 新疆
            'B3': (34.3, 108.9), 'BX3': (34.3, 108.9),  # 3 区通称
            'BH3': (34.3, 108.9),  # 按数字分区
            
            # ===== 特别行政区 =====
            'VR2': (22.3, 114.2),  # 香港
            'XX9': (22.2, 113.5),  # 澳门
        }
        
        # 根据大概经纬度判断国家尺寸
        lat_range, lon_range = 5, 8  # 默认 ±2.5-4 度
        country_matched = False  # 标记是否已匹配特定国家
        
        # 日本 - 按数字分区精确定位，避免落入海洋
        if dxcc_name == 'Japan':
            country_matched = True
            callsign_upper = callsign.upper()
            
            # 日本 CQ 分区中心点（1-9 区）
            japan_call_areas = {
                'JG1': (35.7, 139.7), 'JH1': (35.7, 139.7), 'JI1': (35.7, 139.7), 'JJ1': (35.7, 139.7), 'JK1': (35.7, 139.7), 'JA1': (35.7, 139.7),  # 1 区：关东
                'JG2': (35.2, 136.9), 'JH2': (35.2, 136.9), 'JI2': (35.2, 136.9), 'JJ2': (35.2, 136.9), 'JK2': (35.2, 136.9), 'JA2': (35.2, 136.9),  # 2 区：中部
                'JG3': (34.7, 135.5), 'JH3': (34.7, 135.5), 'JI3': (34.7, 135.5), 'JJ3': (34.7, 135.5), 'JK3': (34.7, 135.5), 'JA3': (34.7, 135.5),  # 3 区：关西
                'JG4': (34.4, 132.5), 'JH4': (34.4, 132.5), 'JI4': (34.4, 132.5), 'JJ4': (34.4, 132.5), 'JK4': (34.4, 132.5), 'JA4': (34.4, 132.5),  # 4 区：中国/四国
                'JA5': (33.6, 130.4),  # 5 区：九州北部
                'JA6': (32.0, 130.8),  # 6 区：九州南部/冲绳
                'JG7': (38.3, 141.0), 'JH7': (38.3, 141.0), 'JI7': (38.3, 141.0), 'JJ7': (38.3, 141.0), 'JK7': (38.3, 141.0), 'JA7': (38.3, 141.0),  # 7 区：东北
                'JG8': (43.1, 141.3), 'JH8': (43.1, 141.3), 'JI8': (43.1, 141.3), 'JJ8': (43.1, 141.3), 'JK8': (43.1, 141.3), 'JA8': (43.1, 141.3),  # 8 区：北海道
                'JG9': (36.6, 140.0), 'JH9': (36.6, 140.0), 'JI9': (36.6, 140.0), 'JJ9': (36.6, 140.0), 'JK9': (36.6, 140.0), 'JA9': (36.6, 140.0),  # 9 区：北陆
            }
            
            # 查找匹配的前缀（从长到短）
            japan_center = None
            for length in [3, 2]:
                prefix = callsign_upper[:length]
                if prefix in japan_call_areas:
                    japan_center = japan_call_areas[prefix]
                    break
            
            if japan_center:
                center_lat, center_lon = japan_center
                lat_range, lon_range = 1.5, 2.0  # 小范围散射±0.75-1°
            else:
                center_lat, center_lon = 36.5, 139.0  # 本州岛中心兜底
                lat_range, lon_range = 2.5, 3.0  # ±1.25-1.5°
        
        # 新西兰 - 按分区精确定位，避免落入海洋
        elif dxcc_name == 'New Zealand':
            country_matched = True
            callsign_upper = callsign.upper()
            
            # 新西兰 Call Area 中心点
            nz_call_areas = {
                'ZL1': (-36.8, 174.8),  # 1 区：奥克兰/北地
                'ZL2': (-40.9, 175.7),  # 2 区：惠灵顿/马纳瓦图
                'ZL3': (-43.5, 172.6),  # 3 区：坎特伯雷/查塔姆岛
                'ZL4': (-45.9, 170.5),  # 4 区：奥塔哥/南地
            }
            
            # 查找匹配的前缀
            nz_center = None
            for length in [3]:
                prefix = callsign_upper[:length]
                if prefix in nz_call_areas:
                    nz_center = nz_call_areas[prefix]
                    break
            
            if nz_center:
                center_lat, center_lon = nz_center
                lat_range, lon_range = 1.5, 2.0  # 小范围散射
            else:
                center_lat, center_lon = -40.9, 174.8  # 新西兰中部兜底
                lat_range, lon_range = 2.5, 3.0
        
        # 英国/英格兰/苏格兰/威尔士/北爱尔兰 - 小范围散射
        elif dxcc_name in ('England', 'Scotland', 'Wales', 'Northern Ireland', 'United Kingdom'):
            country_matched = True
            callsign_upper = callsign.upper()
            
            # 英国各地区中心点
            uk_call_areas = {
                'G': (52.0, -2.0), 'M': (52.0, -2.0),  # 英国通称
                '2E0': (51.5, -0.1),  # 英格兰新手
                'M0': (51.5, -0.1), 'M1': (51.5, -0.1),  # 英格兰
                'MM': (56.0, -4.0),  # 苏格兰
                'MW': (52.0, -3.5),  # 威尔士
                'MI': (54.6, -6.0),  # 北爱尔兰
                'MJ': (49.2, -2.1),  # 泽西岛
                'MU': (49.2, -2.5),  # 根西岛
            }
            
            # 查找匹配的前缀
            uk_center = None
            for length in [3, 2, 1]:
                prefix = callsign_upper[:length]
                if prefix in uk_call_areas:
                    uk_center = uk_call_areas[prefix]
                    break
            
            if uk_center:
                center_lat, center_lon = uk_center
                lat_range, lon_range = 1.5, 2.0
            else:
                center_lat, center_lon = 52.0, -2.0
                lat_range, lon_range = 2.0, 2.5
        
        # 爱尔兰 - 小范围散射
        elif dxcc_name == 'Republic of Ireland':
            country_matched = True
            center_lat, center_lon = 53.0, -7.5  # 爱尔兰中部
            lat_range, lon_range = 1.8, 2.5
        
        # 澳大利亚 - 按州精确定位
        elif dxcc_name == 'Australia':
            country_matched = True
            callsign_upper = callsign.upper()
            
            # 澳大利亚 Call Area 中心点
            au_call_areas = {
                'VK2': (-33.0, 151.0),  # 新南威尔士
                'VK3': (-37.8, 144.9),  # 维多利亚
                'VK4': (-27.5, 153.0),  # 昆士兰
                'VK5': (-34.9, 138.6),  # 南澳
                'VK6': (-31.9, 115.8),  # 西澳
                'VK7': (-42.9, 147.3),  # 塔斯马尼亚
                'VK8': (-12.5, 130.8),  # 北领地
                'VK9': (-31.5, 159.1),  # 外部领地（诺福克等）
                'VK0': (-54.5, 159.0),  # 南极领地/麦夸里岛
            }
            
            # 查找匹配的前缀
            au_center = None
            for length in [3]:
                prefix = callsign_upper[:length]
                if prefix in au_call_areas:
                    au_center = au_call_areas[prefix]
                    break
            
            if au_center:
                center_lat, center_lon = au_center
                lat_range, lon_range = 2.0, 3.0
            else:
                center_lat, center_lon = (-25.0, 135.0)  # 澳洲中部兜底
                lat_range, lon_range = 15, 20
        
        # 美国本土 - 使用 Call Area，但 KH6/KL7 等特殊地区单独处理
        elif dxcc_name in ('United States', 'USA'):
            country_matched = True
            callsign_upper = callsign.upper()
            
            # 夏威夷 KH6/KH7/KH8
            if callsign_upper.startswith(('KH6', 'KH7', 'KH8')):
                center_lat, center_lon = 20.5, -156.5  # 夏威夷大岛
                lat_range, lon_range = 1.5, 2.0
            # 阿拉斯加 KL7
            elif callsign_upper.startswith('KL7'):
                center_lat, center_lon = 64.0, -150.0  # 阿拉斯加中部
                lat_range, lon_range = 10, 20
            # 关岛 KH0
            elif callsign_upper.startswith('KH0'):
                center_lat, center_lon = 13.5, 144.8  # 关岛
                lat_range, lon_range = 0.5, 0.8
            # 波多黎各 KP4 - 精确散射
            elif callsign_upper.startswith('KP4'):
                center_lat, center_lon = 18.2, -66.5  # 波多黎各
                lat_range, lon_range = 0.8, 1.0
            # 美属维尔京群岛 KP2
            elif callsign_upper.startswith('KP2'):
                center_lat, center_lon = 17.7, -64.8  # 维尔京群岛
                lat_range, lon_range = 0.5, 0.8
            # 美属萨摩亚 KH8
            elif callsign_upper.startswith(('KH8S', 'K3S')):
                center_lat, center_lon = -14.3, -170.7  # 美属萨摩亚
                lat_range, lon_range = 0.5, 0.8
            else:
                # 美国本土 Call Areas
                usa_call_areas = {
                    'K1': (44, -71), 'N1': (44, -71), 'W1': (44, -71),  # 1 区：新英格兰
                    'K2': (40, -74), 'N2': (40, -74), 'W2': (40, -74),  # 2 区：纽约/新泽西
                    'K3': (40, -77), 'N3': (40, -77), 'W3': (40, -77),  # 3 区：中大西洋
                    'K4': (28, -82), 'N4': (28, -82), 'W4': (28, -82),  # 4 区：东南部
                    'K5': (32, -97), 'N5': (32, -97), 'W5': (32, -97),  # 5 区：中南部
                    'K6': (37, -120), 'N6': (37, -120), 'W6': (37, -120),  # 6 区：加州
                    'K7': (45, -115), 'N7': (45, -115), 'W7': (45, -115),  # 7 区：西北部
                    'K8': (40, -83), 'N8': (40, -83), 'W8': (40, -83),  # 8 区：五大湖
                    'K9': (42, -88), 'N9': (42, -88), 'W9': (42, -88),  # 9 区：中西部
                    'K0': (39, -105), 'N0': (39, -105), 'W0': (39, -105),  # 0 区：中西部山区
                }
                
                usa_center = None
                for length in [2, 1]:
                    prefix = callsign_upper[:length]
                    if prefix in usa_call_areas:
                        usa_center = usa_call_areas[prefix]
                        break
                
                if usa_center:
                    center_lat, center_lon = usa_center
                    lat_range, lon_range = 6, 10
                else:
                    center_lat, center_lon = 39, -98  # 美国中部兜底
                    lat_range, lon_range = 15, 25
        
        # 韩国 - 缩小散射范围避免落入海洋
        elif dxcc_name == 'Republic of Korea':
            country_matched = True
            center_lat, center_lon = 36.5, 128.0  # 韩国中部（大邱附近）
            lat_range, lon_range = 1.5, 2  # ±0.75°纬度，±1°经度
        
        # 香港 - 小范围散射避免落入深圳/珠海
        elif dxcc_name == 'Hong Kong':
            country_matched = True
            lat_range, lon_range = 0.5, 0.8  # ±0.25°纬度，±0.4°经度
        
        # 澳门 - 小范围散射
        elif dxcc_name == 'Macao':
            country_matched = True
            lat_range, lon_range = 0.3, 0.5  # ±0.15°纬度，±0.25°经度
        
        # 斯卡伯勒浅滩（黄岩岛）- 精确定点，不散射
        elif dxcc_name == 'Scarborough Reef':
            country_matched = True
            lat_range, lon_range = 0, 0  # 不散射，保持精确坐标
        
        # 台湾 - 缩小散射范围
        elif dxcc_name == 'Taiwan':
            country_matched = True
            center_lat, center_lon = 23.7, 120.9  # 台湾中部
            lat_range, lon_range = 2, 2.5  # ±1°纬度，±1.25°经度
        
        # 中国 - 使用省份中心点优化（排除韩国和台湾）
        # 注意：resolve 函数已经按数字分区处理好了中国呼号，这里不再重复处理
        elif dxcc_name == 'China':
            country_matched = True
            # 直接使用传入的 center_lat, center_lon（已在 resolve 中按数字分区计算）
            # 不再重新查找 china_provinces，避免覆盖正确的结果
            lat_range, lon_range = 5, 8  # 省份内散射
        
        # 美国 - 使用 Call Area 中心点
        elif dxcc_name in ('United States', 'USA'):
            country_matched = True
            usa_call_areas = {
                'K1': (44, -71), 'N1': (44, -71), 'W1': (44, -71),  # 1 区：新英格兰
                'K2': (40, -74), 'N2': (40, -74), 'W2': (40, -74),  # 2 区：纽约/新泽西
                'K3': (40, -77), 'N3': (40, -77), 'W3': (40, -77),  # 3 区：中大西洋
                'K4': (28, -82), 'N4': (28, -82), 'W4': (28, -82),  # 4 区：东南部
                'K5': (32, -97), 'N5': (32, -97), 'W5': (32, -97),  # 5 区：中南部
                'K6': (37, -120), 'N6': (37, -120), 'W6': (37, -120),  # 6 区：加州
                'K7': (45, -115), 'N7': (45, -115), 'W7': (45, -115),  # 7 区：西北部
                'K8': (40, -83), 'N8': (40, -83), 'W8': (40, -83),  # 8 区：五大湖
                'K9': (42, -88), 'N9': (42, -88), 'W9': (42, -88),  # 9 区：中西部
                'K0': (39, -105), 'N0': (39, -105), 'W0': (39, -105),  # 0 区：中西部山区
            }
            
            callsign_upper = callsign.upper()
            usa_center = None
            
            # 检查前缀（从长到短）
            for length in [2, 1]:
                prefix = callsign_upper[:length]
                if prefix in usa_call_areas:
                    usa_center = usa_call_areas[prefix]
                    break
            
            if usa_center:
                center_lat, center_lon = usa_center
                lat_range, lon_range = 6, 10  # Call Area 内±3-5 度
            else:
                lat_range, lon_range = 15, 25
        
        # 加拿大 - 使用 Call Area 中心点
        elif dxcc_name == 'Canada':
            country_matched = True
            canada_call_areas = {
                'VE1': (45, -64), 'VY1': (45, -64),  # 1 区：沿海省份
                'VE2': (46, -71),  # 2 区：魁北克
                'VE3': (44, -80),  # 3 区：安大略
                'VE4': (50, -97),  # 4 区：马尼托巴
                'VE5': (52, -107),  # 5 区：萨斯喀彻温
                'VE6': (53, -114),  # 6 区：阿尔伯塔
                'VE7': (49, -123),  # 7 区：BC 省
                'VY0': (61, -68),  # 0 区：努纳武特
                'VY9': (62, -114),  # 9 区：西北地区
            }
            
            callsign_upper = callsign.upper()
            canada_center = None
            
            # 检查前缀（从长到短）
            for length in [3, 2]:
                prefix = callsign_upper[:length]
                if prefix in canada_call_areas:
                    canada_center = canada_call_areas[prefix]
                    break
            
            if canada_center:
                center_lat, center_lon = canada_center
                lat_range, lon_range = 4, 8  # Call Area 内±2-4 度
            else:
                lat_range, lon_range = 15, 25
        
        # 欧洲国家 - 根据前缀设置中心点
        else:
            europe_prefixes = {
                # 波罗的海国家
                'YL': (56.5, 24.5),  # 拉脱维亚
                'ES': (59.0, 25.0),  # 爱沙尼亚
                'LY': (55.0, 24.0),  # 立陶宛
                # 北欧
                'SM': (62.0, 15.0), 'SA': (62.0, 15.0),  # 瑞典
                'LA': (62.0, 10.0), 'LN': (62.0, 10.0),  # 挪威
                'OH': (62.0, 26.0), 'OF': (62.0, 26.0),  # 芬兰
                'OZ': (56.0, 10.0),  # 丹麦
                # 西欧
                'DL': (51.0, 10.0),  # 德国
                'G': (54.0, -2.0), 'M': (54.0, -2.0),  # 英国
                'F': (46.0, 2.0),  # 法国
                'I': (42.0, 12.0),  # 意大利
                'EA': (40.0, -4.0),  # 西班牙
                'PA': (52.0, 5.0), 'PD': (52.0, 5.0), 'PF': (52.0, 5.0),  # 荷兰
                'ON': (50.5, 4.5), 'OR': (50.5, 4.5), 'OT': (50.5, 4.5),  # 比利时
                'LX': (49.5, 6.0),  # 卢森堡
                'HB': (47.0, 8.0),  # 瑞士
                'OE': (47.5, 14.0),  # 奥地利
                # 中欧
                'SP': (52.0, 20.0), 'SN': (52.0, 20.0), 'SO': (52.0, 20.0), 'SQ': (52.0, 20.0),  # 波兰
                'OK': (49.5, 15.0), 'OM': (49.5, 15.0),  # 捷克/斯洛伐克
                'HA': (47.0, 20.0),  # 匈牙利
                'S5': (46.0, 14.0),  # 斯洛文尼亚
                '9A': (45.0, 16.0),  # 克罗地亚
                'YO': (46.0, 25.0),  # 罗马尼亚
                'LZ': (42.5, 25.0),  # 保加利亚
                'SV': (38.0, 22.0),  # 希腊
                'UA': (55.0, 50.0),  # 俄罗斯欧洲部分
            }
            
            if dxcc_name in europe_prefixes or any(callsign.upper().startswith(p) for p in europe_prefixes):
                country_matched = True
                
                callsign_upper = callsign.upper()
                eu_center = None
                
                # 检查前缀（从长到短）
                for length in [3, 2, 1]:
                    prefix = callsign_upper[:length]
                    if prefix in europe_prefixes:
                        eu_center = europe_prefixes[prefix]
                        break
                
                if eu_center:
                    center_lat, center_lon = eu_center
                    lat_range, lon_range = 4, 6  # 国家内±2-3 度
                else:
                    # 使用默认欧洲范围
                    lat_range, lon_range = 5, 8
        
        # 地理判断兜底 - 只在未匹配特定国家时使用
        if not country_matched:
            # DEBUG
            # 低纬度 + 东经 120-150 = 日本/东南亚
            if abs(center_lat) < 30 and 120 < center_lon < 150:
                lat_range, lon_range = 10, 12
                # DEBUG
            # 中高纬度 + 东经 20-180 = 俄罗斯/亚洲
            elif center_lat > 50 and center_lon > 20:
                lat_range, lon_range = 20, 50
                # DEBUG
            # 欧洲中部
            elif 35 < center_lat < 60 and -10 < center_lon < 40:
                lat_range, lon_range = 5, 8
                # DEBUG
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
