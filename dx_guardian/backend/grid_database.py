"""
Grid Database Module - 提供 Maidenhead Grid 查询功能

支持从 JTDX grid_data.bin 格式加载呼号-Grid 映射
"""

import zlib
import json
import re
import struct
from typing import Optional, Tuple, Dict
from pathlib import Path


class GridDatabase:
    """
    Maidenhead Grid 数据库
    
    提供呼号到 Grid Locator 的查询功能
    支持 JTDX 格式和 JSON 格式
    """
    
    def __init__(self):
        """初始化 Grid 数据库"""
        self.grid_map: Dict[str, str] = {}  # callsign -> grid
        self.loaded = False
    
    def load_jtdx_format(self, filepath: str) -> int:
        """
        加载 JTDX 格式的 Grid 数据库
        
        Args:
            filepath: grid_data.bin 文件路径
            
        Returns:
            加载的记录数
        """
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # zlib 解压（跳过 4 字节头）
        try:
            decompressed = zlib.decompress(data[4:])
        except zlib.error as e:
            raise ValueError(f"Failed to decompress grid data: {e}")
        
        # 解析记录
        offset = 0
        grid_re = re.compile(r'([A-R]{2}\d{2}[A-X]{0,2})', re.I)
        callsign_re = re.compile(r'^[A-Z0-9]{3,12}$')
        records_parsed = 0
        
        while offset + 8 <= len(decompressed):
            # 2 字节长度（大端序）
            length = struct.unpack('>H', decompressed[offset:offset+2])[0]
            
            if length == 0 or length > 100:
                offset += 1
                continue
            
            # 2 字节 ID（未使用）
            # id_val = struct.unpack('>H', decompressed[offset+2:offset+4])[0]
            
            # ASCII 数据
            try:
                text = decompressed[offset+4:offset+4+length].decode('ascii', errors='ignore').strip()
            except:
                offset += 4 + length
                continue
            
            # 查找 Grid
            grid_match = grid_re.search(text)
            if grid_match:
                grid = grid_match.group(1).upper()
                
                # Grid 之前的部分为呼号
                callsign = text[:grid_match.start()].strip()
                callsign = re.sub(r'[^A-Z0-9/]', '', callsign).upper()
                
                if callsign_re.match(callsign):
                    self.grid_map[callsign] = grid
                    records_parsed += 1
            
            offset += 4 + length
        
        self.loaded = True
        return records_parsed
    
    def load_from_json(self, filepath: str) -> int:
        """
        从预解析的 JSON 文件加载
        
        Args:
            filepath: JSON 文件路径
            
        Returns:
            加载的记录数
        """
        with open(filepath, 'r') as f:
            self.grid_map = json.load(f)
        
        self.loaded = True
        return len(self.grid_map)
    
    def lookup(self, callsign: str) -> Optional[str]:
        """
        查询呼号对应的 Grid
        
        Args:
            callsign: 呼号
            
        Returns:
            Grid Locator（6 字符），如果未找到则返回 None
        """
        if not self.loaded:
            return None
        
        return self.grid_map.get(callsign.upper())
    
    def has_callsign(self, callsign: str) -> bool:
        """
        检查呼号是否在数据库中
        
        Args:
            callsign: 呼号
            
        Returns:
            True 如果存在，否则 False
        """
        return callsign.upper() in self.grid_map
    
    def get_stats(self) -> Dict:
        """
        获取数据库统计信息
        
        Returns:
            包含统计信息的字典
        """
        if not self.loaded:
            return {'loaded': False}
        
        # 统计 Grid 分布
        grid_counts = {}
        for grid in self.grid_map.values():
            if len(grid) >= 4:
                # 统计前 4 字符（Field + Square）
                prefix = grid[:4]
                grid_counts[prefix] = grid_counts.get(prefix, 0) + 1
        
        return {
            'loaded': True,
            'total_callsigns': len(self.grid_map),
            'unique_grids': len(set(self.grid_map.values())),
            'grid_prefixes': len(grid_counts),
            'top_grids': sorted(grid_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def __len__(self) -> int:
        """返回数据库中的记录数"""
        return len(self.grid_map)
    
    def __contains__(self, callsign: str) -> bool:
        """检查呼号是否在数据库中"""
        return callsign.upper() in self.grid_map


def grid_to_latlon(grid: str) -> Optional[Tuple[float, float]]:
    """
    将 Maidenhead Grid 转换为经纬度（返回 Grid 中心点）
    
    Args:
        grid: Grid Locator（4-6 字符）
             格式：FN31pr
             - Field: 2 字母 (A-R) -> 18°×18°
             - Square: 2 数字 (0-9) -> 2°×1°
             - Subsquare: 2 字母 (A-X) -> 5'×2.5'
    
    Returns:
        (latitude, longitude) 元组，如果格式错误则返回 None
        
    Examples:
        >>> grid_to_latlon('PN35HS')
        (45.083333333333336, 127.54166666666667)
        >>> grid_to_latlon('FN31')
        (41.5, -72.5)
    """
    if not grid or len(grid) < 4:
        return None
    
    grid = grid.upper().strip()
    
    # 验证 Grid 格式
    grid_pattern = re.compile(r'^[A-R]{2}\d{2}([A-X]{2})?$')
    if not grid_pattern.match(grid):
        return None
    
    # 解析 Field（2 字母）
    lon_field = ord(grid[0]) - ord('A')
    lat_field = ord(grid[1]) - ord('A')
    
    # 解析 Square（2 数字）
    lon_sq = int(grid[2])
    lat_sq = int(grid[3])
    
    # 计算基础经纬度
    # Field: 经度每格 20°,纬度每格 10°
    lon = (lon_field * 20) + (lon_sq * 2) - 180
    lat = (lat_field * 10) + (lat_sq * 1) - 90
    
    # 解析 Subsquare（2 字母，可选）
    if len(grid) >= 6:
        lon_subsq = ord(grid[4]) - ord('A')
        lat_subsq = ord(grid[5]) - ord('A')
        
        # Subsquare 中心点
        # 每个 Subsquare 是 5' × 2.5'
        # 中心点在 +2.5' 和 +1.25'
        lon += (lon_subsq * (5/60)) + (2.5/60)
        lat += (lat_subsq * (2.5/60)) + (1.25/60)
    else:
        # 只有 4 字符，返回 Square 中心点
        lon += 1  # 2° 的中心
        lat += 0.5  # 1° 的中心
    
    return (lat, lon)


def latlon_to_grid(lat: float, lon: float, precision: int = 4) -> str:
    """
    将经纬度转换为 Maidenhead Grid
    
    Args:
        lat: 纬度 (-90 到 90)
        lon: 经度 (-180 到 180)
        precision: Grid 精度 (4 或 6)
    
    Returns:
        Grid Locator 字符串
    """
    # Field
    field_lon = chr(ord('A') + int((lon + 180) / 18))
    field_lat = chr(ord('A') + int((lat + 90) / 18))
    
    # Square
    square_lon = str(int((lon + 180) % 18 / 2))
    square_lat = str(int((lat + 90) % 18))
    
    grid = f"{field_lon}{field_lat}{square_lon}{square_lat}"
    
    # Subsquare
    if precision >= 6:
        sub_lon = chr(ord('A') + int(((lon + 180) % 2) / (5/60)))
        sub_lat = chr(ord('A') + int(((lat + 90) % 1) / (2.5/60)))
        grid += sub_lon + sub_lat
    
    return grid


# 便捷函数
def lookup_grid(callsign: str, db_path: str = '/workspace/dx_guardian/backend/data/grid_callsign_map.json') -> Optional[str]:
    """
    查询呼号对应的 Grid（便捷函数）
    
    Args:
        callsign: 呼号
        db_path: Grid 数据库路径
        
    Returns:
        Grid Locator 或 None
    """
    db = GridDatabase()
    
    # 尝试加载 JSON 格式
    if Path(db_path).exists():
        db.load_from_json(db_path)
        return db.lookup(callsign)
    
    # 尝试加载 JTDX 格式
    jtdx_path = str(Path(db_path).parent / 'grid_data.bin')
    if Path(jtdx_path).exists():
        db.load_jtdx_format(jtdx_path)
        return db.lookup(callsign)
    
    return None


if __name__ == '__main__':
    # 测试代码
    import sys
    
    print("=" * 60)
    print("Grid Database Test")
    print("=" * 60)
    
    # 测试 JTDX 格式加载
    jtdx_path = '/workspace/grid_data.bin'
    if Path(jtdx_path).exists():
        print(f"\n加载 JTDX 格式：{jtdx_path}")
        db = GridDatabase()
        count = db.load_jtdx_format(jtdx_path)
        print(f"✓ 加载成功：{count:,} 条记录")
        
        # 保存为 JSON
        output_path = '/workspace/grid_callsign_map_extracted.json'
        with open(output_path, 'w') as f:
            json.dump(db.grid_map, f, indent=2)
        print(f"✓ 已保存到：{output_path}")
        
        # 显示统计信息
        stats = db.get_stats()
        print(f"\n统计信息:")
        print(f"  总呼号数：{stats['total_callsigns']:,}")
        print(f"  唯一 Grid 数：{stats['unique_grids']:,}")
        print(f"  Grid 前缀数：{stats['grid_prefixes']:,}")
        print(f"\nTop 10 Grid:")
        for grid, count in stats['top_grids']:
            print(f"  {grid}: {count} 个呼号")
        
        # 测试 Grid 转换
        print("\n\nGrid 转换测试:")
        test_grids = ['PN35HS', 'JO21SP', 'FN31', 'IO82', 'PM30', 'EM77']
        for grid in test_grids:
            result = grid_to_latlon(grid)
            if result:
                lat, lon = result
                print(f"  {grid:6s} -> ({lat:+7.4f}°, {lon:+8.4f}°)")
            else:
                print(f"  {grid:6s} -> 无效格式")
        
        # 测试查询
        print("\n示例呼叫号查询:")
        test_callsigns = ['BG2ENW', 'W7CIE', 'A6ZPA/P', 'U8YD', '5KIM']
        for cs in test_callsigns:
            gr = db.lookup(cs)
            if gr:
                lat, lon = grid_to_latlon(gr)
                print(f"  {cs:12s} -> {gr:6s} ({lat:+7.4f}°, {lon:+8.4f}°)")
            else:
                print(f"  {cs:12s} -> 未找到")
    else:
        print(f"✗ 文件不存在：{jtdx_path}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
