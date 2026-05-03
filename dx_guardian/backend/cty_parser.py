"""
CTY.DAT 解析器 - ARRL 前缀数据库
从 /workspace/cty.dat 解析呼号前缀 -> DXCC 实体映射
"""
import re
from pathlib import Path
from typing import Dict, Optional

class CTYData:
    """CTY.DAT 数据库解析器"""
    
    def __init__(self, cty_file: str = '/workspace/cty.dat'):
        """初始化并加载 CTY 数据库"""
        self.entities = {}
        self.prefix_map = {}
        
        # 检查文件是否存在
        import os
        if not os.path.exists(cty_file) or os.path.getsize(cty_file) < 100:
            print(f'⚠️  CTY.DAT 文件不存在或太小 ({cty_file})，使用简化模式')
            return
        
        # 仅当文件有效时才加载
        self._load_cty(cty_file)
    
    def _load_cty(self, filepath: str):
        """加载并解析 cty.dat 文件"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            lines = content.split('\n')
            current_entity = None
            entity_line_pattern = re.compile(
                r'^([^:]+):\s+(\d+):\s+(\d+):\s+([A-Z]{2}):\s+([-\d.]+):\s+([-\d.]+):\s+([-\d.]+):\s+([A-Z0-9*]+):'
            )
            
            for line in lines:
                line_stripped = line.strip()
                
                # 尝试匹配实体定义行
                match = entity_line_pattern.match(line_stripped)
                if match:
                    name, cq, itu, continent, lat, lon, tz, primary = match.groups()
                    
                    current_entity = {
                        'name': name.strip(),
                        'cq': int(cq),
                        'itu': int(itu),
                        'continent': continent.strip(),
                        'lat': float(lat),
                        'lon': -float(lon),  # CTY 使用西经为正，取反转换为标准东经为正
                        'timezone': float(tz),
                        'primary_prefix': primary.strip().lstrip('*')
                    }
                    
                    self.entities[current_entity['name']] = current_entity
                    
                    # 主前缀映射
                    if primary.strip():
                        prefix = primary.strip().lstrip('*')
                        self.prefix_map[prefix] = current_entity['name']
                    continue
                
                # 匹配别名前缀行（以空格或制表符开头，紧跟实体定义）
                if (line.startswith(' ') or line.startswith('\t')) and current_entity:
                    prefix_line = line_stripped.rstrip(';')
                    raw_prefixes = [p.strip().lstrip('=') for p in prefix_line.split(',') if p.strip()]
                    
                    for prefix in raw_prefixes:
                        if not prefix:
                            continue
                        
                        # 忽略操作符前缀（包含 / 的）
                        if '/' in prefix:
                            continue
                        
                        # 提取基础前缀（去掉括号和数字后缀）
                        base_prefix = re.match(r'^([A-Z0-9]{1,6})', prefix)
                        if base_prefix:
                            clean_prefix = base_prefix.group(1)
                            if clean_prefix:
                                self.prefix_map[clean_prefix] = current_entity['name']
            
            print(f'✅ CTY.DAT 已加载：{len(self.entities)} 个实体，{len(self.prefix_map)} 个前缀')
            
        except Exception as e:
            print(f'❌ CTY.DAT 加载失败：{e}')
            import traceback
            traceback.print_exc()
    
    def lookup(self, callsign: str) -> Optional[Dict]:
        """根据呼号查询 DXCC 实体信息"""
        callsign = callsign.upper().strip()
        
        # 尝试不同长度的前缀（从长到短）
        for length in range(min(7, len(callsign)), 0, -1):
            prefix = callsign[:length]
            
            if prefix in self.prefix_map:
                entity_name = self.prefix_map[prefix]
                if entity_name in self.entities:
                    return self.entities[entity_name]
        
        return None
    
    def get_entity_by_prefix(self, prefix: str) -> Optional[Dict]:
        """根据前缀查询实体信息"""
        prefix = prefix.upper().strip()
        if prefix in self.prefix_map:
            entity_name = self.prefix_map[prefix]
            return self.entities.get(entity_name)
        return None


# 单例模式
_cty_instance = None

def get_cty_data() -> CTYData:
    """获取 CTY 数据库单例"""
    global _cty_instance
    if _cty_instance is None:
        _cty_instance = CTYData()
    return _cty_instance


# 测试
if __name__ == '__main__':
    cty = get_cty_data()
    
    test_callsigns = ['BG2ENW', 'JA1AAA', 'W1AW', 'DL1ABC', 'G3P', 'F6ABC', 'VK2ABC', 'K1TTT']
    
    print("\n测试查询:")
    for cs in test_callsigns:
        info = cty.lookup(cs)
        if info:
            print(f"{cs:10} -> {info['name']:30} ({info['lat']:.2f}, {info['lon']:.2f}) CQ:{info['cq']} ITU:{info['itu']}")
        else:
            print(f"{cs:10} -> 未找到")