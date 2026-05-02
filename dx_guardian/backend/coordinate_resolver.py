"""
坐标解析模块
三级策略：Grid → 呼号查询 → DXCC 兜底
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


class CoordinateResolver:
    """坐标解析器"""
    
    def __init__(self):
        self.dxcc_db = {}
        self.grid_cache = {}  # 呼号 → {grid, lat, lon, timestamp}
        self._load_dxcc_db()
    
    def _load_dxcc_db(self):
        """加载 DXCC 前缀库"""
        try:
            with open(DXCC_PREFIX_FILE, 'r', encoding='utf-8') as f:
                self.dxcc_db = json.load(f)
            print(f'✅ DXCC 前缀库已加载: {len(self.dxcc_db)} 个前缀')
        except Exception as e:
            print(f'❌ DXCC 前缀库加载失败: {e}')
            self.dxcc_db = {}
    
    def resolve(self, callsign, grid=None):
        """
        解析坐标（三级策略）
        
        Args:
            callsign: 呼号（如 JA1AA）
            grid: Grid 方格（如 PM85jk），可选
        
        Returns:
            dict: {
                'lat': float,
                'lon': float,
                'precision': 'grid'|'dxcc',
                'dxcc': str (实体名称),
                'prefix': str (匹配的前缀)
            }
        """
        dxcc_info = self._lookup_dxcc(callsign)
        
        # 第一级：Grid 方格（最精确）
        if grid:
            lat, lon = self._grid_to_latlon(grid)
            if lat is not None and lon is not None:
                return {
                    'lat': lat,
                    'lon': lon,
                    'precision': 'grid',
                    'dxcc': dxcc_info.get('entity', ''),
                    'prefix': dxcc_info.get('prefix', '')
                }
        
        # 第二级：远程呼号查询（缓存优先）
        if callsign:
            remote_grid = self._get_cached_or_fetch_grid(callsign)
            if remote_grid:
                lat, lon = self._grid_to_latlon(remote_grid)
                if lat is not None and lon is not None:
                    return {
                        'lat': lat,
                        'lon': lon,
                        'precision': 'grid',  # 远程获取的Grid也算精确
                        'dxcc': dxcc_info.get('entity', ''),
                        'prefix': dxcc_info.get('prefix', '')
                    }
        
        # 第三级：呼号前缀 → DXCC 数据库（在 Grid 方格内分散显示）
        if dxcc_info and dxcc_info.get('lat') != 0 and dxcc_info.get('lon') != 0:
            lat, lon = self._scatter_in_grid(callsign, dxcc_info['lat'], dxcc_info['lon'])
            return {
                'lat': lat,
                'lon': lon,
                'precision': 'dxcc',
                'dxcc': dxcc_info.get('entity', ''),
                'prefix': dxcc_info.get('prefix', '')
            }
        
        # 第四级：未知（返回 0,0）
        return {
            'lat': 0.0,
            'lon': 0.0,
            'precision': 'unknown',
            'dxcc': '',
            'prefix': ''
        }
    
    def _latlon_to_grid(self, lat, lon):
        """经纬度转 Maidenhead Grid 方格（6位）"""
        if lat < -90 or lat > 90 or lon < -180 or lon > 180:
            return None
        lon += 180
        lat += 90
        
        # 字段（2字符）
        field_lon = int(lon / 20)
        field_lat = int(lat / 10)
        lon -= field_lon * 20
        lat -= field_lat * 10
        
        # 方格（2数字）
        square_lon = int(lon / 2)
        square_lat = int(lat)
        lon -= square_lon * 2
        lat -= square_lat
        
        # 子方格（2字符）
        sub_lon = int(lon / 2 * 24)
        sub_lat = int(lat * 24)
        
        grid = chr(ord('A') + field_lon) + chr(ord('A') + field_lat) + \
               str(square_lon) + str(square_lat) + \
               chr(ord('a') + sub_lon) + chr(ord('a') + sub_lat)
        return grid.upper()

    def _scatter_in_grid(self, callsign, center_lat, center_lon):
        """
        在 Grid 方格内基于呼号哈希分散显示位置
        
        同一个国家的不同电台不会全部堆在国家中心点，
        而是根据呼号哈希在中心点所在的 Grid 方格内分散显示。
        
        Args:
            callsign: 呼号
            center_lat: 国家中心纬度
            center_lon: 国家中心经度
        
        Returns:
            tuple: (lat, lon) 分散后的坐标
        """
        # 用呼号生成确定性哈希值（同一呼号总是得到同一位置）
        hash_val = hash(callsign.upper()) & 0xFFFFFFFF
        
        # 计算中心点所在的 Grid 方格边界
        # Grid 方格大小：2度经度 × 1度纬度
        grid_lon_start = math.floor((center_lon + 180) / 2) * 2 - 180
        grid_lat_start = math.floor(center_lat + 90) - 90
        
        # 在方格内用哈希值生成偏移（0.1~0.9 范围，避免贴边）
        lon_offset = 0.1 + (hash_val % 1000) / 1000 * 0.8
        lat_offset = 0.1 + ((hash_val >> 10) % 1000) / 1000 * 0.8
        
        lat = grid_lat_start + lat_offset
        lon = grid_lon_start + lon_offset
        
        return lat, lon

    
    def _get_cached_or_fetch_grid(self, callsign):
        """
        从缓存或远程API获取呼号的Grid
        
        先检查缓存（24小时有效），未命中则查询API
        
        Args:
            callsign: 呼号
        
        Returns:
            str: Grid方格，或None
        """
        callsign = callsign.upper()
        
        # 检查缓存（24小时 = 86400秒）
        if callsign in self.grid_cache:
            cache_entry = self.grid_cache[callsign]
            if time.time() - cache_entry['timestamp'] < 86400:
                return cache_entry['grid']
            else:
                # 缓存过期，删除
                del self.grid_cache[callsign]
        
        # 远程查询
        grid = self._fetch_grid_from_clublog(callsign)
        
        # 缓存结果
        if grid:
            self.grid_cache[callsign] = {
                'grid': grid,
                'timestamp': time.time()
            }
            # 限制缓存大小
            if len(self.grid_cache) > 500:
                # 删除最旧的100个
                oldest = sorted(self.grid_cache.items(), key=lambda x: x[1]['timestamp'])[:100]
                for key, _ in oldest:
                    del self.grid_cache[key]
        
        return grid
    
    def _fetch_grid_from_clublog(self, callsign):
        """从多个 callbook 数据源获取呼号Grid（QRZ → HamQTH）"""
        # 数据源1：QRZ.com XML API
        grid = self._fetch_grid_from_qrz(callsign)
        if grid:
            print(f'[QRZ] {callsign} → {grid}')
            return grid
        
        # 数据源2：HamQTH API
        grid = self._fetch_grid_from_hamqth(callsign)
        if grid:
            print(f'[HamQTH] {callsign} → {grid}')
            return grid
        
        return None
    
    def _fetch_grid_from_qrz(self, callsign):
        """QRZ.com XML API 查询呼号Grid"""
        try:
            from config import QRZ_USERNAME, QRZ_PASSWORD
            if not QRZ_USERNAME or not QRZ_PASSWORD:
                return None
            
            ns = '{http://xmldata.qrz.com}'
            
            login_url = f'https://xmldata.qrz.com/xml/current/?username={urllib.parse.quote(QRZ_USERNAME)}&password={urllib.parse.quote(QRZ_PASSWORD)}&agent=DX-Guardian-1.0'
            req = urllib.request.Request(login_url, headers={'User-Agent': 'DX-Guardian/1.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                xml_data = resp.read().decode('utf-8')
            
            root = ET.fromstring(xml_data)
            session = root.find(f'{ns}Session')
            if session is None:
                session = root.find('Session')
            if session is None:
                return None
            
            # 检查登录错误
            error = session.find(f'{ns}Error')
            if error is None:
                error = session.find('Error')
            if error is not None:
                print(f'[QRZ登录失败] {error.text}')
                return None
            
            key_el = session.find(f'{ns}Key')
            if key_el is None:
                key_el = session.find('Key')
            if key_el is None:
                return None
            key = key_el.text
            
            # 第二步：查询呼号
            query_url = f'https://xmldata.qrz.com/xml/current/?s={key}&callsign={callsign.upper()}'
            req = urllib.request.Request(query_url, headers={'User-Agent': 'DX-Guardian/1.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                xml_data = resp.read().decode('utf-8')
            
            root = ET.fromstring(xml_data)
            session = root.find(f'{ns}Session')
            if session is None:
                session = root.find('Session')
            if session is not None:
                error = session.find(f'{ns}Error')
                if error is None:
                    error = session.find('Error')
                if error is not None:
                    return None
            
            # 查找 grid（在 CallSign 或 Cache 元素下）
            for tag_name in ['Callsign', 'Cache']:
                call_el = root.find(f'{ns}{tag_name}')
                if call_el is None:
                    call_el = root.find(tag_name)
                if call_el is not None:
                    grid_el = call_el.find(f'{ns}grid')
                    if grid_el is None:
                        grid_el = call_el.find('grid')
                    if grid_el is not None and grid_el.text:
                        grid = grid_el.text.strip().upper()
                        if len(grid) >= 4:
                            return grid
        except Exception as e:
            print(f'[QRZ查询失败] {callsign}: {e}')
        
        return None
    
    def _fetch_grid_from_hamqth(self, callsign):
        """HamQTH API 查询呼号Grid"""
        try:
            from config import HAMQTH_USERNAME, HAMQTH_PASSWORD
            if not HAMQTH_USERNAME or not HAMQTH_PASSWORD:
                return None
            
            ns = '{https://www.hamqth.com}'
            
            login_url = f'https://www.hamqth.com/xml.php?u={urllib.parse.quote(HAMQTH_USERNAME)}&p={urllib.parse.quote(HAMQTH_PASSWORD)}'
            req = urllib.request.Request(login_url, headers={'User-Agent': 'DX-Guardian/1.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                xml_data = resp.read().decode('utf-8')
            
            root = ET.fromstring(xml_data)
            # HamQTH uses xmlns namespace
            session = root.find(f'{ns}session')
            if session is None:
                session = root.find('session')  # fallback
            if session is None:
                return None
            
            sid_el = session.find(f'{ns}session_id')
            if sid_el is None:
                sid_el = session.find('session_id')
            if sid_el is None:
                return None
            sid = sid_el.text
            
            # 查询呼号
            query_url = f'https://www.hamqth.com/xml.php?id={sid}&callsign={callsign.upper()}&prg=DX-Guardian'
            req = urllib.request.Request(query_url, headers={'User-Agent': 'DX-Guardian/1.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                xml_data = resp.read().decode('utf-8')
            
            root = ET.fromstring(xml_data)
            search = root.find(f'{ns}search')
            if search is None:
                search = root.find('search')
            if search is not None:
                grid_el = search.find(f'{ns}grid')
                if grid_el is None:
                    grid_el = search.find('grid')
                if grid_el is not None and grid_el.text:
                    grid = grid_el.text.strip().upper()
                    if len(grid) >= 4:
                        return grid
                # 没有 grid 但有 lat/lon，转换成 grid
                lat_el = search.find(f'{ns}latitude')
                if lat_el is None:
                    lat_el = search.find('latitude')
                lon_el = search.find(f'{ns}longitude')
                if lon_el is None:
                    lon_el = search.find('longitude')
                if lat_el is not None and lon_el is not None and lat_el.text and lon_el.text:
                    try:
                        lat = float(lat_el.text)
                        lon = float(lon_el.text)
                        grid = self._latlon_to_grid(lat, lon)
                        if grid:
                            return grid
                    except ValueError:
                        pass
        except Exception as e:
            print(f'[HamQTH查询失败] {callsign}: {e}')
        
        return None

    
    def _grid_to_latlon(self, grid):
        """
        Maidenhead Grid 方格转经纬度
        
        Grid 格式：2字符(字段) + 2数字(方格) + 2字符(子方格)
        如：PN35HS → 哈尔滨
        
        Args:
            grid: Grid 方格字符串
        
        Returns:
            tuple: (lat, lon) 或 (None, None)
        """
        if not grid or len(grid) < 4:
            return None, None
        
        grid = grid.upper()
        
        try:
            # 字段（2字符）
            lon_field = ord(grid[0]) - ord('A')  # A=0, B=1, ...
            lat_field = ord(grid[1]) - ord('A')
            
            # 方格（2数字）
            lon_square = int(grid[2])
            lat_square = int(grid[3])
            
            # 基础经纬度
            lon = (lon_field * 20) + (lon_square * 2) - 180
            lat = (lat_field * 10) + lat_square - 90
            
            # 子方格（2字符，可选）
            if len(grid) >= 6:
                lon_sub = ord(grid[4]) - ord('A')
                lat_sub = ord(grid[5]) - ord('A')
                lon += (lon_sub + 0.5) * (2.0 / 24)
                lat += (lat_sub + 0.5) * (1.0 / 24)
            else:
                # 没有子方格，取方格中心
                lon += 1.0  # 方格宽度2度，中心偏移1度
                lat += 0.5  # 方格高度1度，中心偏移0.5度
            
            return lat, lon
            
        except (ValueError, IndexError):
            return None, None
    
    # ITU 呼号前缀分配表（字母+数字组合 → 国家）
    # 格式：前缀字母范围 → (lat, lon, entity, continent, cq_zone, itu_zone)
    ITU_PREFIX_MAP = {
        # 美国：AA-AL, KA-KZ, NA-NZ, WA-WZ
        'A_US': (38.0, -97.0, 'United States of America', 'NA', 5, 8),
        'K_US': (38.0, -97.0, 'United States of America', 'NA', 5, 8),
        'N_US': (38.0, -97.0, 'United States of America', 'NA', 5, 8),
        'W_US': (38.0, -97.0, 'United States of America', 'NA', 5, 8),
        # 日本：JA-JS, 7A-7N, 8A-8N
        'J_JP': (36.0, 138.0, 'Japan', 'AS', 25, 45),
        # 巴西：PP-PY, ZV-ZZ
        'P_BR': (-10.0, -55.0, 'Brazil', 'SA', 11, 15),
        'Z_BR': (-10.0, -55.0, 'Brazil', 'SA', 11, 15),
        # 中国：BA-BQ, BY, B+数字
        'B_CN': (35.0, 105.0, 'China', 'AS', 24, 44),
        # 韩国：DS-DT, D7-D9, HL-HM, 6K-6N
        'D_KR': (37.0, 127.0, 'Republic of Korea', 'AS', 25, 44),
        'H_KR': (37.0, 127.0, 'Republic of Korea', 'AS', 25, 44),
        '6_KR': (37.0, 127.0, 'Republic of Korea', 'AS', 25, 44),
        # 加拿大：VA-VG, VE, VO, VY-VZ, CY-CK
        'V_CA': (60.0, -95.0, 'Canada', 'NA', 5, 9),
        'C_CA': (60.0, -95.0, 'Canada', 'NA', 5, 9),
        # 俄罗斯：RA-RZ, UA-UI
        'R_RU': (56.0, 38.0, 'European Russia', 'EU', 16, 29),
        'U_RU': (56.0, 38.0, 'European Russia', 'EU', 16, 29),
        # 乌克兰：UR-UZ
        'U_UA': (49.0, 32.0, 'Ukraine', 'EU', 16, 29),
        # 德国：DA-DR
        'D_DE': (51.0, 10.0, 'Federal Republic of Germany', 'EU', 14, 28),
        # 英国：MA-MZ, 2A-2Z
        'M_GB': (54.0, -2.0, 'England', 'EU', 14, 27),
        # 法国：F, HW-HY, TH-TK, TM-TQ, TV-TW
        'T_FR': (46.0, 2.0, 'France', 'EU', 14, 27),
        # 意大利：IA-IZ
        'I_IT': (42.0, 12.0, 'Italy', 'EU', 15, 28),
        # 西班牙：EA-EH, AM-AO
        'E_ES': (40.0, -4.0, 'Spain', 'EU', 14, 37),
        # 印度：AT-AW, VT-VW, 8T-8W
        'A_IN': (21.0, 78.0, 'India', 'AS', 22, 41),
        'V_IN': (21.0, 78.0, 'India', 'AS', 22, 41),
        '8_IN': (21.0, 78.0, 'India', 'AS', 22, 41),
        # 澳大利亚：AX-VH, VK-VN, VZ
        'V_AU': (-25.0, 134.0, 'Australia', 'OC', 30, 59),
    }

    def _itu_lookup(self, callsign):
        """
        ITU 呼号分配规则匹配
        根据呼号的字母+数字组合确定国家
        这比纯前缀匹配更准确
        """
        if not callsign or len(callsign) < 2:
            return None

        c = callsign.upper()
        c0 = c[0]
        c1 = c[1]

        # 检查是否有数字（标准呼号格式：字母+数字+字母）
        has_digit = any(ch.isdigit() for ch in c[1:4])

        result = None

        # === 美国 ===
        # AA-AL + 数字 = 美国
        if c0 == 'A' and 'A' <= c1 <= 'L' and has_digit:
            result = self.ITU_PREFIX_MAP['A_US']
        # KA-KZ + 数字 = 美国
        elif c0 == 'K' and has_digit:
            result = self.ITU_PREFIX_MAP['K_US']
        # NA-NZ + 数字 = 美国
        elif c0 == 'N' and has_digit:
            result = self.ITU_PREFIX_MAP['N_US']
        # WA-WZ + 数字 = 美国
        elif c0 == 'W' and has_digit:
            result = self.ITU_PREFIX_MAP['W_US']

        # === 中国 ===
        # BA-BQ + 数字, BY + 数字, B + 数字
        elif c0 == 'B' and (c1.isdigit() or ('A' <= c1 <= 'Q') or c1 == 'Y'):
            result = self.ITU_PREFIX_MAP['B_CN']

        # === 日本 ===
        # JA-JS + 数字
        elif c0 == 'J' and 'A' <= c1 <= 'S' and has_digit:
            result = self.ITU_PREFIX_MAP['J_JP']

        # === 巴西 ===
        # PP-PY + 数字
        elif c0 == 'P' and 'P' <= c1 <= 'Y' and has_digit:
            result = self.ITU_PREFIX_MAP['P_BR']
        # ZV-ZZ + 数字
        elif c0 == 'Z' and 'V' <= c1 <= 'Z' and has_digit:
            result = self.ITU_PREFIX_MAP['Z_BR']

        # === 韩国 ===
        # DS-DT + 数字
        elif c0 == 'D' and 'S' <= c1 <= 'T' and has_digit:
            result = self.ITU_PREFIX_MAP['D_KR']
        # HL-HM + 数字
        elif c0 == 'H' and 'L' <= c1 <= 'M' and has_digit:
            result = self.ITU_PREFIX_MAP['H_KR']

        # === 加拿大 ===
        # VA-VG, VE, VO, VY-VZ + 数字
        elif c0 == 'V' and 'A' <= c1 <= 'G' and has_digit:
            result = self.ITU_PREFIX_MAP['V_CA']
        elif c0 == 'V' and c1 in ('E', 'O', 'Y', 'Z') and has_digit:
            result = self.ITU_PREFIX_MAP['V_CA']
        # CF-CK + 数字
        elif c0 == 'C' and 'F' <= c1 <= 'K' and has_digit:
            result = self.ITU_PREFIX_MAP['C_CA']

        # === 俄罗斯 ===
        # RA-RZ + 数字
        elif c0 == 'R' and 'A' <= c1 <= 'Z' and has_digit:
            result = self.ITU_PREFIX_MAP['R_RU']
        # UA-UI + 数字
        elif c0 == 'U' and 'A' <= c1 <= 'I' and has_digit:
            result = self.ITU_PREFIX_MAP['U_RU']

        # === 乌克兰 ===
        # UR-UZ + 数字
        elif c0 == 'U' and 'R' <= c1 <= 'Z' and has_digit:
            result = self.ITU_PREFIX_MAP['U_UA']

        # === 德国 ===
        # DA-DR + 数字
        elif c0 == 'D' and 'A' <= c1 <= 'R' and has_digit:
            result = self.ITU_PREFIX_MAP['D_DE']

        # === 英国 ===
        # MA-MZ + 数字
        elif c0 == 'M' and 'A' <= c1 <= 'Z' and has_digit:
            result = self.ITU_PREFIX_MAP['M_GB']

        # === 法国 ===
        # TM-TQ, TV-TW + 数字
        elif c0 == 'T' and (('M' <= c1 <= 'Q') or ('V' <= c1 <= 'W')) and has_digit:
            result = self.ITU_PREFIX_MAP['T_FR']

        # === 意大利 ===
        # IA-IZ + 数字
        elif c0 == 'I' and 'A' <= c1 <= 'Z' and has_digit:
            result = self.ITU_PREFIX_MAP['I_IT']

        # === 西班牙 ===
        # EA-EH + 数字
        elif c0 == 'E' and 'A' <= c1 <= 'H' and has_digit:
            result = self.ITU_PREFIX_MAP['E_ES']

        # === 印度 ===
        # AT-AW + 数字
        elif c0 == 'A' and 'T' <= c1 <= 'W' and has_digit:
            result = self.ITU_PREFIX_MAP['A_IN']
        # VT-VW + 数字
        elif c0 == 'V' and 'T' <= c1 <= 'W' and has_digit:
            result = self.ITU_PREFIX_MAP['V_IN']

        # === 澳大利亚 ===
        # VK-VN, AX + 数字
        elif c0 == 'V' and 'K' <= c1 <= 'N' and has_digit:
            result = self.ITU_PREFIX_MAP['V_AU']
        elif c0 == 'A' and c1 == 'X' and has_digit:
            result = self.ITU_PREFIX_MAP['V_AU']

        # === 乌拉圭 ===
        # CX + 数字
        elif c0 == 'C' and c1 == 'X' and has_digit:
            result = (-34.5, -56.0, 'Uruguay', 'SA', 13, 14)

        # === 挪威 ===
        # LA-LN + 数字
        elif c0 == 'L' and 'A' <= c1 <= 'N' and has_digit:
            result = (64.0, 12.0, 'Norway', 'EU', 14, 18)

        # === 阿根廷 ===
        # AY-AZ + 数字
        elif c0 == 'A' and 'Y' <= c1 <= 'Z' and has_digit:
            result = (-34.0, -64.0, 'Argentina', 'SA', 13, 14)
        # LO-LW + 数字
        elif c0 == 'L' and 'O' <= c1 <= 'W' and has_digit:
            result = (-34.0, -64.0, 'Argentina', 'SA', 13, 14)

        # === 智利 ===
        # CA-CE + 数字
        elif c0 == 'C' and 'A' <= c1 <= 'E' and has_digit:
            result = (-30.0, -71.0, 'Chile', 'SA', 12, 14)

        # === 墨西哥 ===
        # XA-XI + 数字
        elif c0 == 'X' and 'A' <= c1 <= 'I' and has_digit:
            result = (23.0, -102.0, 'Mexico', 'NA', 6, 10)

        # === 荷兰 ===
        # PA-PI + 数字
        elif c0 == 'P' and 'A' <= c1 <= 'I' and has_digit:
            result = (52.0, 5.0, 'Netherlands', 'EU', 14, 27)

        # === 比利时 ===
        # ON-OT + 数字
        elif c0 == 'O' and 'N' <= c1 <= 'T' and has_digit:
            result = (50.5, 4.0, 'Belgium', 'EU', 14, 27)

        # === 瑞士 ===
        # HB-HB + 数字
        elif c0 == 'H' and 'B' <= c1 <= 'B' and has_digit:
            result = (47.0, 8.0, 'Switzerland', 'EU', 14, 28)

        # === 波兰 ===
        # HF-HZ, SN-SR, 3Z + 数字
        elif c0 == 'H' and 'F' <= c1 <= 'Z' and has_digit:
            result = (52.0, 20.0, 'Poland', 'EU', 15, 28)
        elif c0 == 'S' and 'N' <= c1 <= 'R' and has_digit:
            result = (52.0, 20.0, 'Poland', 'EU', 15, 28)

        # === 瑞典 ===
        # SA-SM + 数字
        elif c0 == 'S' and 'A' <= c1 <= 'M' and has_digit:
            result = (62.0, 15.0, 'Sweden', 'EU', 14, 18)

        # === 芬兰 ===
        # OF-OJ + 数字
        elif c0 == 'O' and 'F' <= c1 <= 'J' and has_digit:
            result = (64.0, 26.0, 'Finland', 'EU', 15, 18)

        # === 挪威 ===
        # LA-LN + 数字
        elif c0 == 'L' and 'A' <= c1 <= 'N' and has_digit:
            result = (64.0, 12.0, 'Norway', 'EU', 14, 18)

        # === 丹麦 ===
        # OU-OZ + 数字
        elif c0 == 'O' and 'U' <= c1 <= 'Z' and has_digit:
            result = (56.0, 10.0, 'Denmark', 'EU', 14, 18)

        # === 奥地利 ===
        # OE-OH... OE + 数字
        elif c0 == 'O' and c1 == 'E' and has_digit:
            result = (47.5, 14.0, 'Austria', 'EU', 15, 28)

        # === 葡萄牙 ===
        # CT-CU + 数字
        elif c0 == 'C' and 'T' <= c1 <= 'U' and has_digit:
            result = (39.5, -8.0, 'Portugal', 'EU', 14, 37)

        # === 希腊 ===
        # SV-SZ, J2 + 数字
        elif c0 == 'S' and 'V' <= c1 <= 'Z' and has_digit:
            result = (39.0, 22.0, 'Greece', 'EU', 20, 28)
        elif c0 == 'J' and c1 == '2' and has_digit:
            result = (39.0, 22.0, 'Greece', 'EU', 20, 28)

        # === 土耳其 ===
        # TA-TH + 数字
        elif c0 == 'T' and 'A' <= c1 <= 'H' and has_digit:
            result = (39.0, 35.0, 'Turkey', 'AS', 20, 39)

        # === 南非 ===
        # ZR-ZU + 数字
        elif c0 == 'Z' and 'R' <= c1 <= 'U' and has_digit:
            result = (-29.0, 24.0, 'South Africa', 'AF', 38, 57)

        # === 新西兰 ===
        # ZL-ZM + 数字
        elif c0 == 'Z' and 'L' <= c1 <= 'M' and has_digit:
            result = (-42.0, 174.0, 'New Zealand', 'OC', 32, 60)

        if result:
            return {
                'entity': result[2],
                'lat': result[0],
                'lon': result[1],
                'prefix': c0 + c1,
                'continent': result[3],
                'cq_zone': result[4],
                'itu_zone': result[5]
            }

        return None

    def _lookup_dxcc(self, callsign):
        """
        根据呼号前缀查找 DXCC 实体

        优先级：
        1. ITU 呼号分配规则（最准确）
        2. 前缀库匹配（从长到短）
        """
        if not callsign or not self.dxcc_db:
            return None

        callsign = callsign.upper()

        # 第一优先级：ITU 呼号分配规则
        itu_result = self._itu_lookup(callsign)
        if itu_result:
            return itu_result

        # 第二优先级：前缀库匹配（从长到短）
        for length in range(min(4, len(callsign)), 0, -1):
            prefix = callsign[:length]
            if prefix in self.dxcc_db:
                info = self.dxcc_db[prefix].copy()
                info['prefix'] = prefix
                return info

_resolver = None

def get_resolver():
    """获取坐标解析器单例"""
    global _resolver
    if _resolver is None:
        _resolver = CoordinateResolver()
    return _resolver

def resolve_coordinates(callsign, grid=None):
    """便捷函数：解析坐标"""
    return get_resolver().resolve(callsign, grid)


if __name__ == '__main__':
    # 测试
    resolver = CoordinateResolver()
    
    # 测试 Grid 解析
    print('\n=== Grid 解析测试 ===')
    test_grids = [
        ('BG2ENW', 'PN35HS'),  # 哈尔滨
        ('JA1AA', 'PM85jk'),   # 东京
        ('W1AW', 'FN31'),      # 美国康涅狄格
        ('VK3XX', 'QF22'),     # 澳大利亚
    ]
    
    for call, grid in test_grids:
        result = resolver.resolve(call, grid)
        print(f'{call} ({grid}): lat={result["lat"]:.2f}, lon={result["lon"]:.2f}, precision={result["precision"]}, dxcc={result["dxcc"]}')
    
    # 测试 DXCC 前缀匹配
    print('\n=== DXCC 前缀匹配测试 ===')
    test_calls = ['JA1AA', 'W1AW', 'VK3XX', 'DL1AA', 'G4ABC', 'PY2XX', 'ZL1AA', 'BG2ENW', 'HL1AA']
    
    for call in test_calls:
        result = resolver.resolve(call)
        print(f'{call}: lat={result["lat"]:.1f}, lon={result["lon"]:.1f}, precision={result["precision"]}, dxcc={result["dxcc"]}, prefix={result["prefix"]}')
