import re, time
from datetime import datetime, timezone
from collections import OrderedDict

class SpotParser:
    # Pattern 1: DX de REPORTER: CALLSIGN FREQ MODE COMMENT (常见格式)
    PATTERN1 = re.compile(r'DX\s+de\s+(?P<reporter>\S+)\s*:\s*(?P<callsign>\S+)\s+(?P<freq>[\d.]+)\s+(?P<mode>\S+)(?:\s+(?P<comment>.*?))?(?:\s+(?P<time>\d{4}Z))?')
    
    # Pattern 2: DX de REPORTER: FREQ CALLSIGN MODE COMMENT (另一种格式)
    PATTERN2 = re.compile(r'DX\s+de\s+(?P<reporter>\S+)\s*:\s*(?P<freq>[\d.]+)\s+(?P<callsign>\S+)\s+(?P<mode>\S+)(?:\s+(?P<comment>.*?))?(?:\s+(?P<time>\d{4}Z))?')
    
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
        return {
            'callsign': match.group('callsign').upper(),
            'freq': float(match.group('freq')),
            'mode': match.group('mode').upper(),
            'reporter': match.group('reporter'),
            'comment': match.group('comment') or '',
            'time': match.group('time') or '',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'band': self._freq_to_band(float(match.group('freq')))
        }
    
    def _freq_to_band(self, freq):
        """Hz 转为波段名称"""
        if freq < 1000:
            return str(int(freq)) + 'm'  # kHz
        elif freq < 30000:
            return str(int(freq / 1000)) + 'm'  # MHz -> m
        elif freq < 30000000:
            return str(int(freq / 1000000)) + 'm'
        else:
            return 'HF'

class SpotDeduplicator:
    def __init__(self, max_size=10000, window_seconds=300):
        self.seen = OrderedDict()
        self.max_size = max_size
        self.window = window_seconds
    
    def is_duplicate(self, spot):
        # 使用呼号 + 频率作为去重 key（不含时间，因为时间总是不同）
        key = f"{spot.get('callsign', '')}:{spot.get('freq', '')}"
        now = datetime.now(timezone.utc).timestamp()
        
        # 清理过期条目
        for k in [k for k, ts in self.seen.items() if ts < now - self.window]:
            del self.seen[k]
        
        if key in self.seen:
            return True
        
        self.seen[key] = now
        
        # 保持大小限制
        if len(self.seen) > self.max_size:
            self.seen.popitem(last=False)
        
        return False

class SpotRateLimiter:
    def __init__(self, max_per_second=20):
        self.max_per_second = max_per_second
        self.timestamps = []
    
    def allow(self):
        """检查是否允许处理（兼容旧代码）"""
        return self.should_process()
    
    def should_process(self):
        now = time.time()
        # 只保留最近 1 秒的时间戳
        self.timestamps = [t for t in self.timestamps if t > now - 1.0]
        
        if len(self.timestamps) >= self.max_per_second:
            return False
        
        self.timestamps.append(now)
        return True
