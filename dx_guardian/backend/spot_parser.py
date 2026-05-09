import re, time
from datetime import datetime, timezone
from collections import OrderedDict

class SpotParser:
    # Grid 提取正则（忽略大小写，支持 4 位和 6 位）
    GRID_PATTERN = re.compile(r'\b([A-R]{2}\d{2}[A-X]{0,2})\b', re.IGNORECASE)
    
    # Pattern 1: DX de REPORTER: CALLSIGN FREQ MODE COMMENT (常见格式)
    # comment 捕获 time 之前的所有内容
    PATTERN1 = re.compile(r'DX\s+de\s+(?P<reporter>\S+)\s*:\s*(?P<callsign>\S+)\s+(?P<freq>[\d.]+)\s+(?P<mode>\S+)\s+(?P<comment>.+?)?\s*(?P<time>\d{4}Z)\s*$')
    
    # Pattern 2: DX de REPORTER: FREQ CALLSIGN MODE COMMENT (另一种格式)
    PATTERN2 = re.compile(r'DX\s+de\s+(?P<reporter>\S+)\s*:\s*(?P<freq>[\d.]+)\s+(?P<callsign>\S+)\s+(?P<mode>\S+)\s+(?P<comment>.+?)?\s*(?P<time>\d{4}Z)\s*$')
    
    def parse(self, line):
        # Try pattern 1 first (more common)
        m = self.PATTERN1.search(line)
        if m:
            return self._create_spot(m)
        
        # Try pattern 2
        m = self.PATTERN2.search(line)
        if m:
            return self._create_spot(m)
        
        return None
    
    def _create_spot(self, match):
        freq_khz = float(match.group('freq'))
        comment = match.group('comment') or ''
        
        # 从 comment 中提取 Grid
        grid = None
        if comment:
            grid_match = self.GRID_PATTERN.search(comment)
            if grid_match:
                grid = grid_match.group(1).upper()  # 统一转大写
        
        return {
            'callsign': match.group('callsign').upper(),
            'freq': freq_khz,
            'mode': match.group('mode').upper(),
            'reporter': match.group('reporter'),
            'comment': comment,
            'time': match.group('time') or '',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'band': self._freq_to_band(freq_khz),
            'grid': grid
        }
    
    def _freq_to_band(self, freq_khz):
        """kHz 转为标准业余波段名称"""
        # HF 波段
        if freq_khz < 500:
            return '160m'   # 1800-2000 kHz
        elif freq_khz < 4000:
            return '80m'    # 3500-4000 kHz
        elif freq_khz < 5500:
            return '60m'    # 5250-5400 kHz
        elif freq_khz < 7500:
            return '40m'    # 7000-7300 kHz
        elif freq_khz < 10200:
            return '30m'    # 10100-10150 kHz
        elif freq_khz < 14500:
            return '20m'    # 14000-14350 kHz
        elif freq_khz < 18200:
            return '17m'    # 18068-18168 kHz
        elif freq_khz < 21500:
            return '15m'    # 21000-21450 kHz
        elif freq_khz < 25000:
            return '12m'    # 24890-24990 kHz
        elif freq_khz < 29000:
            return '10m'    # 28000-29700 kHz
        elif freq_khz < 54000:
            return '6m'     # 50-54 MHz = 50000-54000 kHz
        elif freq_khz < 148000:
            return '2m'     # 144-148 MHz
        else:
            return 'VHF/UHF'

class SpotDeduplicator:
    def __init__(self, max_size=10000, window_seconds=300):
        self.seen = OrderedDict()
        self.max_size = max_size
        self.window = window_seconds
    
    def is_duplicate(self, spot, source=None):
        # PSK Reporter 使用不同的 key 前缀，避免被 Cluster Spot 去重
        # 因为 PSK Reporter 的 Grid 是实际接收到的，比 Cluster 更可靠
        # PSK Reporter 的 key 包含 Grid，因为同一呼号可能在不同 Grid 被接收
        if source == 'pskreporter':
            grid = spot.get('grid', '')
            key = f"psk:{spot.get('callsign', '')}:{spot.get('freq', '')}:{grid}"
        else:
            key = f"{spot.get('callsign', '')}:{spot.get('freq', '')}"
        now = datetime.now(timezone.utc).timestamp()
        
        for k in [k for k, ts in self.seen.items() if ts < now - self.window]:
            del self.seen[k]
        
        if key in self.seen:
            return True
        
        self.seen[key] = now
        
        if len(self.seen) > self.max_size:
            self.seen.popitem(last=False)
        
        return False

class SpotRateLimiter:
    def __init__(self, max_per_second=20):
        self.max_per_second = max_per_second
        self.timestamps = []
    
    def allow(self):
        return self.should_process()
    
    def should_process(self):
        now = time.time()
        self.timestamps = [t for t in self.timestamps if t > now - 1.0]
        
        if len(self.timestamps) >= self.max_per_second:
            return False
        
        self.timestamps.append(now)
        return True
