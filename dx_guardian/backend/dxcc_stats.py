"""
DXCC 统计模块
从日志中统计已通/缺失 DXCC 实体
"""
from typing import List, Set, Dict, Optional
from collections import Counter
from adif_parser import QSORecord


class DXCCStats:
    """DXCC 统计器"""
    
    # 简化的 DXCC 前缀库（常用前缀 -> 实体名）
    # 完整列表应从 official DXCC list 导入
    DXCC_PREFIXES = {
        # 亚洲
        'JA': 'Japan', 'JA*': 'Japan',
        'BV': 'Taiwan', 'BV*': 'Taiwan', 'BJ': 'Taiwan', 'B*': 'Taiwan',
        'HL': 'South Korea', 'HM': 'South Korea', 'DS': 'South Korea', 'H*': 'South Korea',
        'P5': 'North Korea', 'DPRK': 'North Korea',
        'B': 'China', 'BG': 'China', 'BH': 'China', 'BI': 'China', 'BJ': 'China', 'BM': 'China', 'BN': 'China', 'BP': 'China', 'BQ': 'China', 'BR': 'China', 'BS': 'China', 'BT': 'China', 'BU': 'China', 'BV': 'China', 'BW': 'China', 'BX': 'Taiwan',
        'VR': 'Hong Kong', 'V*': 'Hong Kong',
        'XX9': 'Macau',
        'HS': 'Thailand', 'E2': 'Thailand',
        'XU': 'Cambodia',
        'XW': 'Laos',
        'XZ': 'Myanmar', '4N': 'Myanmar',
        'YS': 'Indonesia', '8A': 'Indonesia',
        '9M': 'Malaysia', '9W': 'Malaysia',
        '9V': 'Singapore',
        '8Q': 'Maldives', '9M8': 'Maldives',
        'A4': 'Oman', 'A5': 'Bhutan', 'A6': 'United Arab Emirates', 'A7': 'Qatar',
        'E5/S': 'Samoa', 'E5/N': 'Northern Cook Islands',
        '3W': 'Vietnam', 'XV': 'Vietnam',
        'XJ': 'Mongolia',
        'XK': 'Kosovo',
        
        # 欧洲
        'G': 'England', 'M': 'England', '2*': 'England',
        'GM': 'Scotland', 'MM': 'Scotland',
        'GD': 'Isle of Man', 'MD': 'Isle of Man',
        'GI': 'Northern Ireland', 'MI': 'Northern Ireland',
        'GW': 'Wales', 'MW': 'Wales',
        'GJ': 'Channel Islands', 'MJ': 'Jersey',
        'GU': 'Guernsey',
        'F': 'France', 'TM': 'France', 'TO': 'France',
        'DL': 'Germany', 'DK': 'Germany',
        'ON': 'Belgium', 'OT': 'Belgium',
        'PA': 'Netherlands', 'PH': 'Netherlands', 'PI': 'Netherlands',
        'HB': 'Switzerland',
        'I': 'Italy', 'IK': 'Italy',
        'EA': 'Spain', 'EB': 'Spain', 'EC': 'Spain', 'ED': 'Spain', 'EE': 'Spain', 'EF': 'Spain', 'EG': 'Spain', 'EH': 'Spain', 'EI': 'Spain', 'EJ': 'Spain', 'EK': 'Spain', 'EL': 'Spain', 'EM': 'Spain', 'EN': 'Spain', 'EO': 'Spain', 'EP': 'Spain', 'EQ': 'Spain', 'ER': 'Spain', 'ES': 'Spain', 'ET': 'Spain', 'EU': 'Spain', 'EW': 'Spain', 'EX': 'Spain', 'EY': 'Spain', 'EZ': 'Spain',
        'CT': 'Portugal', 'CQ': 'Portugal',
        'CU': 'Azores', 'CV': 'Madeira',
        'SP': 'Poland', 'SO': 'Poland', 'SN': 'Poland',
        'OK': 'Czech Republic', 'OL': 'Czech Republic',
        'OM': 'Slovakia',
        'HA': 'Hungary', 'HG': 'Hungary',
        'LY': 'Lithuania', 'Y': 'Lithuania',
        'ES': 'Estonia', 'EU': 'Estonia',
        'LO': 'Latvia', 'LV': 'Latvia', 'YL': 'Latvia',
        'YZ': 'Latvia',
        'OH': 'Finland', 'OF': 'Finland', 'OG': 'Finland', 'OH*': 'Finland',
        'OJ': 'Åland', 'OJ0': 'Åland',
        'LA': 'Norway', 'LB': 'Norway', 'LC': 'Norway', 'LD': 'Norway', 'LE': 'Norway', 'LF': 'Norway', 'LG': 'Norway', 'LH': 'Norway', 'LJ': 'Norway', 'LK': 'Norway',
        'OZ': 'Denmark', 'XP': 'Denmark', 'XR': 'Denmark', 'XQ': 'Denmark',
        'SV': 'Greece', 'SW': 'Greece', 'SY': 'Greece', 'SZ': 'Greece',
        'JY': 'Jordan',
        '4X': 'Israel', '4Z': 'Israel',
        'A7': 'Qatar', 'A6': 'United Arab Emirates',
        'TC': 'Turkey', 'TA': 'Turkey',
        'UA': 'Russia', 'R*': 'Russia', 'RV': 'Russia', 'RW': 'Russia', 'RX': 'Russia', 'RY': 'Russia', 'RZ': 'Russia',
        'UH': 'Uzbekistan', 'UK': 'Uzbekistan',
        'UG': 'Kyrgyzstan',
        'T6': 'Afghanistan',
        'EP': 'Iran',
        
        # 北美
        'K': 'United States', 'W*': 'United States', 'N*': 'United States', 'A*': 'United States',
        'KL': 'Alaska', 'AL': 'Alaska',
        'KH': 'Hawaii', 'AH': 'Hawaii',
        'VE': 'Canada', 'VA': 'Canada', 'VO': 'Canada', 'VY': 'Canada', 'CY': 'Canada', 'CF': 'Canada',
        'VY0': 'Nunavut', 'VY1': 'Northwest Territories', 'VY2': 'Ontario', 'VY0': 'Nunavut', 'VE1': 'Nova Scotia', 'VE2': 'Ontario', 'VE3': 'Ontario', 'VE4': 'Manitoba', 'VE5': 'Saskatchewan', 'VE6': 'Alberta', 'VE7': 'British Columbia', 'VE8': 'Northwest Territories', 'VE9': 'Prince Edward Island',
        'XJ': 'Greenland',
        'XE': 'Mexico', 'XF': 'Mexico', 'XG': 'Mexico',
        
        # 南美
        'OA': 'Peru',
        'HC': 'Ecuador', 'HD': 'Ecuador',
        'HP': 'Panama', 'HK': 'Panama', 'HO': 'Panama',
        'P4': 'Aruba',
        'PJ': 'Netherlands Antilles',
        'YS': 'Indonesia', '8A': 'Indonesia',
        'PY': 'Brazil', 'PP': 'Brazil', 'PQ': 'Brazil', 'PR': 'Brazil', 'PS': 'Brazil', 'PT': 'Brazil', 'PV': 'Brazil', 'PW': 'Brazil', 'PX': 'Brazil', 'PZ': 'Brazil',
        'PP5': 'Fernando de Noronha',
        'CE': 'Chile',
        'LZ': 'Paraguay', 'ZP': 'Paraguay',
        'AY': 'Bolivia',
        'CP': 'Bolivia',
        'LV': 'Uruguay',
        'CX': 'Uruguay',
        'LQ': 'Argentina', 'LU': 'Argentina', 'LW': 'Argentina', 'AY': 'Argentina',
        'HC8': 'Galapagos Islands',
        
        # 大洋洲
        'VK': 'Australia', 'AX': 'Australia', 'VH': 'Australia',
        'ZL': 'New Zealand',
        'ZK': 'New Zealand',
        'C2': 'Nauru',
        'C3': 'Andorra',
        'T2': 'Tuvalu',
        'T3': 'Kiribati',
        'D2': 'Angola', 'C8': 'Mozambique',
        'FR': 'Réunion', 'FT': 'Réunion',
        'H4': 'Solomon Islands',
        '5V': 'Togo',
        '5U': 'Niger',
        '6W': 'Senegal',
        '6Y': 'Jamaica',
        '7J': 'Japan',
        '8P': 'Barbados',
        '8Q': 'Maldives',
        '9A': 'Croatia',
        '9K': 'Kuwait',
        '9J': 'Zambia',
        '9L': 'Sierra Leone',
        '9M': 'Malaysia',
        '9N': 'Nepal',
        '9Q': 'Democratic Republic of Congo',
        '9R': 'Guinea',
        '9S': 'Sao Tome and Principe',
        '9U': 'Burundi',
        '9V': 'Singapore',
        '9W': 'Malaysia',
        '9X': 'Rwanda',
        '9Z': 'Angola',
    }
    
    # 前2位前缀 -> 实体名的映射（快速匹配用）
    PREFIX_2CHARS = {}
    for prefix, entity in DXCC_PREFIXES.items():
        if len(prefix) >= 2 and not prefix.endswith('*'):
            key = prefix[:2].upper()
            PREFIX_2CHARS[key] = entity
    
    def __init__(self):
        self.worked_dxcc: Set[str] = set()
        self.missing_dxcc: Set[str] = set()
        self.band_dxcc: Dict[str, Set[str]] = {}
        self.dxcc_count: Counter = Counter()
    
    def analyze_records(self, records: List[QSORecord]) -> Dict:
        """分析 QSO 记录，统计 DXCC"""
        
        for record in records:
            # 提取 DXCC 实体
            entity = self._get_entity_from_call(record.call)
            
            if entity:
                self.worked_dxcc.add(entity)
                self.dxcc_count[entity] += 1
                
                # 按波段统计
                if record.band not in self.band_dxcc:
                    self.band_dxcc[record.band] = set()
                self.band_dxcc[record.band].add(entity)
        
        # 计算缺失的 DXCC
        all_entities = set(self.DXCC_PREFIXES.values())
        self.missing_dxcc = all_entities - self.worked_dxcc
        
        return self._generate_stats()
    
    def _get_entity_from_call(self, callsign: str) -> Optional[str]:
        """从呼号提取 DXCC 实体"""
        if not callsign:
            return None
        
        callsign = callsign.upper().strip()
        
        # 特殊呼号（如 AMSAT 格式）
        if '/' in callsign:
            # 取最后一个部分
            parts = callsign.split('/')
            callsign = parts[-1]
        
        # 提取前2位前缀
        prefix_2 = callsign[:2]
        
        # 匹配 2 位前缀
        if prefix_2 in self.PREFIX_2CHARS:
            return self.PREFIX_2CHARS[prefix_2]
        
        # 匹配特殊前缀（带 * 的通配符）
        for pattern, entity in self.DXCC_PREFIXES.items():
            if pattern.endswith('*'):
                if callsign.startswith(pattern[:-1]):
                    return entity
        
        # 精确匹配完整前缀
        if callsign in self.DXCC_PREFIXES:
            return self.DXCC_PREFIXES[callsign]
        if prefix_2 in self.DXCC_PREFIXES:
            return self.DXCC_PREFIXES[prefix_2]
        
        # 逐位匹配
        for i in range(min(3, len(callsign))):
            test_prefix = callsign[:i+1]
            if test_prefix in self.DXCC_PREFIXES:
                return self.DXCC_PREFIXES[test_prefix]
        
        return None
    
    def _generate_stats(self) -> Dict:
        """生成统计报告"""
        return {
            'total_dxcc_entities': len(set(self.DXCC_PREFIXES.values())),
            'worked_dxcc_count': len(self.worked_dxcc),
            'missing_dxcc_count': len(self.missing_dxcc),
            'worked_dxcc_list': sorted(self.worked_dxcc),
            'missing_dxcc_list': sorted(self.missing_dxcc),
            'band_stats': {
                band: {
                    'count': len(dxcc_set),
                    'dxcc_list': sorted(dxcc_set)
                }
                for band, dxcc_set in sorted(self.band_dxcc.items())
            },
            'top_entities': self.dxcc_count.most_common(10)
        }


# 测试代码
if __name__ == '__main__':
    from adif_parser import QSORecord
    
    # 创建测试数据
    test_records = [
        QSORecord(call='JA1BBB', band='20m', mode='FT8', qso_date='2026-04-28', time_on='12:34:56'),
        QSORecord(call='VK2AAA', band='40m', mode='CW', qso_date='2026-04-27', time_on='22:10:30'),
        QSORecord(call='K5TST', band='80m', mode='SSB', qso_date='2026-04-26', time_on='18:00:00'),
        QSORecord(call='DL7ABC', band='15m', mode='RTTY', qso_date='2026-04-25', time_on='14:22:11'),
        QSORecord(call='JA1CCC', band='20m', mode='FT8', qso_date='2026-04-24', time_on='10:00:00', grid='PM96OI'),
    ]
    
    print("测试 DXCC 统计...")
    stats = DXCCStats()
    result = stats.analyze_records(test_records)
    
    print(f"✅ 分析完成")
    print(f"实体总数: {result['total_dxcc_entities']}")
    print(f"已通实体: {result['worked_dxcc_count']}")
    print(f"缺失实体: {result['missing_dxcc_count']}")
    print(f"\\n已通列表: {', '.join(result['worked_dxcc_list'])}")
    print(f"\\n按波段统计:")
    for band, band_stat in result['band_stats'].items():
        print(f"  {band}: {band_stat['count']} 个实体")
    print(f"\\n通联最多的实体:")
    for entity, count in result['top_entities'][:5]:
        print(f"  {entity}: {count} 次")
