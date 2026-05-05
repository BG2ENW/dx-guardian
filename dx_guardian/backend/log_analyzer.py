"""
日志分析引擎
支持多种数据源：wsjtx_log.adi、Wavelog API、ADIF 文件
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# 导入现有模块
from adif_parser import ADIFParser
# from cty_parser import CTYParser  # 预留
def freq_to_band(freq_value):
    """频率转波段，兼容 kHz/MHz 输入。"""
    if freq_value is None:
        return None

    freq_num = float(freq_value)
    # 兼容两种单位：
    # - >1000 视为 kHz（如 7074）
    # - <=1000 视为 MHz（如 7.074）
    freq_mhz = freq_num / 1000.0 if freq_num > 1000 else freq_num
    
    if freq_mhz < 2: return None
    elif freq_mhz < 2.5: return '160m'
    elif freq_mhz < 4.5: return '80m'
    elif freq_mhz < 5.5: return '60m'
    elif freq_mhz < 7.5: return '40m'
    elif freq_mhz < 10.5: return '30m'
    elif freq_mhz < 14.5: return '20m'
    elif freq_mhz < 18.5: return '17m'
    elif freq_mhz < 21.5: return '15m'
    elif freq_mhz < 25: return '12m'
    elif freq_mhz < 29.5: return '10m'
    elif freq_mhz < 54: return '6m'
    elif freq_mhz < 148: return '2m'
    else: return None


class LogSourceInterface:
    """日志源接口 - 所有数据源的基类"""
    
    def get_logs(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """获取日志记录"""
        raise NotImplementedError
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计摘要"""
        raise NotImplementedError
    
    def export_adif(self) -> str:
        """导出为 ADIF 格式"""
        raise NotImplementedError


class WSJTXLogAdapter(LogSourceInterface):
    """wsjtx_log.adi 文件适配器"""
    
    def __init__(self, filepath: str = '/workspace/dx_guardian/wsjtx_log.adi'):
        self.filepath = Path(filepath)
        self.logs = []
        self._load()
    
    def _load(self):
        """加载 wsjtx_log.adi 文件"""
        if not self.filepath.exists():
            return
        
        parser = ADIFParser()
        records, _ = parser.parse_file(str(self.filepath))
        self.logs = [r.to_dict() for r in records]
    
    def get_logs(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """获取日志，支持日期筛选"""
        if not start_date and not end_date:
            return self.logs
        
        filtered = []
        for log in self.logs:
            qso_date = log.get('qso_date', '')
            if start_date and qso_date < start_date:
                continue
            if end_date and qso_date > end_date:
                continue
            filtered.append(log)
        
        return filtered
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计摘要"""
        if not self.logs:
            return {'total_qso': 0, 'unique_calls': 0, 'unique_dxcc': 0, 'unique_grids': 0}
        
        unique_calls = set()
        unique_dxcc = set()
        unique_grids = set()
        
        for log in self.logs:
            if log.get('call'):
                unique_calls.add(log['call'])
            if log.get('dxcc'):
                unique_dxcc.add(log['dxcc'])
            if log.get('gridsquare'):
                unique_grids.add(log['gridsquare'])
        
        return {
            'total_qso': len(self.logs),
            'unique_calls': len(unique_calls),
            'unique_dxcc': len(unique_dxcc),
            'unique_grids': len(unique_grids)
        }
    
    def export_adif(self) -> str:
        """导出为 ADIF"""
        lines = [
            "<ADIF_VER:5>5.0",
            "<EOH>",
        ]
        
        for log in self.logs:
            record = self._log_to_adif(log)
            lines.append(record)
        
        return '\n'.join(lines)
    
    def _log_to_adif(self, log: Dict) -> str:
        """将单条日志转换为 ADIF 格式"""
        parts = []
        
        if log.get('call'):
            parts.append(f"<CALL:{len(log['call'])}>{log['call']}")
        if log.get('freq'):
            freq_mhz = float(log['freq']) / 1000 if float(log['freq']) < 1000 else float(log['freq'])
            parts.append(f"<FREQ:{len(str(freq_mhz))}>{freq_mhz}")
        if log.get('mode'):
            parts.append(f"<MODE:{len(log['mode'])}>{log['mode'].upper()}")
        if log.get('qso_date'):
            parts.append(f"<QSO_DATE:{len(log['qso_date'])}>{log['qso_date']}")
        if log.get('time_on'):
            parts.append(f"<TIME_ON:{len(log['time_on'])}>{log['time_on']}")
        
        parts.append("<EOR>")
        return ' '.join(parts)


class WavelogAdapter(LogSourceInterface):
    """
    Wavelog API 适配器（预留接口）
    
    配置项:
    - WAVELOG_LOG_API_URL: Wavelog API 端点
    - WAVELOG_LOG_API_KEY: API 密钥
    - WAVELOG_LOG_CALLSIGN: 操作员呼号
    """
    
    def __init__(self, api_url: str = '', api_key: str = '', callsign: str = ''):
        self.api_url = api_url
        self.api_key = api_key
        self.callsign = callsign
        self.logs = []
        # TODO: 实现 API 连接
    
    def get_logs(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """从 Wavelog API 获取日志"""
        # TODO: 实现 API 调用
        # response = requests.get(
        #     f"{self.api_url}/api/contacts",
        #     params={'start': start_date, 'end': end_date},
        #     headers={'Authorization': f'Bearer {self.api_key}'}
        # )
        # self.logs = response.json()
        return self.logs
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计摘要"""
        # TODO: 实现统计计算
        return {'total_qso': len(self.logs)}
    
    def export_adif(self) -> str:
        """导出为 ADIF"""
        # TODO: 实现 ADIF 导出
        return ""


class LogAnalyzer:
    """日志分析引擎"""
    
    def __init__(self):
        self.cq_zones = {}  # 从 cty.dat 加载
        self.itu_zones = {}
    
    def analyze_all(self, logs: List[Dict]) -> Dict[str, Any]:
        """完整分析"""
        if not logs:
            return self._empty_analysis()
        
        analysis = {
            'summary': self._analyze_summary(logs),
            'date_range': self._analyze_date_range(logs),
            'dxcc_distribution': self._analyze_dxcc(logs),
            'band_distribution': self._analyze_bands(logs),
            'mode_distribution': self._analyze_modes(logs),
            'time_distribution': self._analyze_time(logs),
        }
        
        return analysis
    
    def _analyze_summary(self, logs: List[Dict]) -> Dict:
        """基础统计"""
        unique_calls = set()
        unique_dxcc = set()
        unique_grids = set()
        bands = set()
        modes = set()
        
        for log in logs:
            if log.get('call'):
                unique_calls.add(log['call'])
            if log.get('dxcc'):
                unique_dxcc.add(log['dxcc'])
            if log.get('gridsquare'):
                unique_grids.add(log['gridsquare'])
            
            freq = float(log.get('freq', 0))
            if freq > 0:
                band = freq_to_band(freq)
                if band:
                    bands.add(band)
            
            if log.get('mode'):
                modes.add(log['mode'].upper())
        
        return {
            'total_qso': len(logs),
            'unique_calls': len(unique_calls),
            'unique_dxcc': len(unique_dxcc),
            'unique_grids': len(unique_grids),
            'unique_bands': len(bands),
            'unique_modes': len(modes),
        }
    
    def _analyze_date_range(self, logs: List[Dict]) -> Dict:
        """日期范围"""
        dates = []
        for log in logs:
            qso_date = log.get('qso_date', '')
            time_on = log.get('time_on', '0000')
            if qso_date and len(qso_date) == 8:
                dates.append(f"{qso_date[:4]}-{qso_date[4:6]}-{qso_date[6:8]} {time_on[:2]}:{time_on[2:4]}")
        
        if not dates:
            return {'first': None, 'last': None}
        
        dates.sort()
        return {
            'first': dates[0],
            'last': dates[-1],
            'total_days': 1  # 简化计算
        }
    
    def _analyze_dxcc(self, logs: List[Dict]) -> Dict:
        """DXCC 分布"""
        dxcc_counts = defaultdict(int)
        continent_counts = defaultdict(int)
        
        for log in logs:
            dxcc = log.get('dxcc', 'Unknown')
            dxcc_counts[dxcc] += 1
        
        # 大洲分布（简化版，后续可从 cty.dat 获取）
        continent_map = {
            'United States': 'NA',
            'Hawaii': 'NA',
            'Puerto Rico': 'NA',
            'Japan': 'AS',
            'Australia': 'OC',
            'Germany': 'EU',
            'Wales': 'EU',
            'Netherlands': 'EU',
            'Belgium': 'EU',
            'Switzerland': 'EU',
        }
        
        for dxcc, count in dxcc_counts.items():
            continent = continent_map.get(dxcc, 'Other')
            continent_counts[continent] += count
        
        # Top 10 DXCC
        top_dxcc = sorted(dxcc_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_dxcc': len(dxcc_counts),
            'by_continent': dict(continent_counts),
            'top_10': [{'dxcc': dxcc, 'count': count} for dxcc, count in top_dxcc]
        }
    
    def _analyze_bands(self, logs: List[Dict]) -> Dict:
        """波段分布"""
        band_counts = defaultdict(int)
        
        for log in logs:
            freq = float(log.get('freq', 0))
            if freq > 0:
                band = freq_to_band(freq)
                if band:
                    band_counts[band] += 1
        
        # 按常用波段排序
        band_order = ['160m', '80m', '60m', '40m', '30m', '20m', '17m', '15m', '12m', '10m', '6m', '2m']
        sorted_bands = {band: band_counts.get(band, 0) for band in band_order if band in band_counts}
        
        return {
            'by_band': sorted_bands,
            'total_bands': len(band_counts),
            'most_used': max(band_counts.items(), key=lambda x: x[1])[0] if band_counts else None
        }
    
    def _analyze_modes(self, logs: List[Dict]) -> Dict:
        """模式分布"""
        mode_counts = defaultdict(int)
        
        for log in logs:
            mode = log.get('mode', '').upper()
            if mode:
                mode_counts[mode] += 1
        
        sorted_modes = sorted(mode_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'by_mode': dict(sorted_modes),
            'total_modes': len(mode_counts),
            'most_used': sorted_modes[0][0] if sorted_modes else None
        }
    
    def _analyze_time(self, logs: List[Dict]) -> Dict:
        """时间分布（24 小时）"""
        hour_counts = defaultdict(int)
        
        for log in logs:
            time_on = log.get('time_on', '')
            if len(time_on) >= 2:
                try:
                    hour = int(time_on[:2])
                    hour_counts[hour] += 1
                except:
                    pass
        
        return {
            'by_hour': dict(hour_counts),
            'peak_hour': max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else None
        }
    
    def _empty_analysis(self) -> Dict:
        """空数据分析结果"""
        return {
            'summary': {
                'total_qso': 0,
                'unique_calls': 0,
                'unique_dxcc': 0,
                'unique_grids': 0
            },
            'date_range': {'first': None, 'last': None},
            'dxcc_distribution': {'total_dxcc': 0, 'by_continent': {}, 'top_10': []},
            'band_distribution': {'by_band': {}, 'total_bands': 0},
            'mode_distribution': {'by_mode': {}, 'total_modes': 0},
            'time_distribution': {'by_hour': {}, 'peak_hour': None}
        }


# 全局单例
_analyzer = None

def get_analyzer() -> LogAnalyzer:
    """获取分析器实例"""
    global _analyzer
    if _analyzer is None:
        _analyzer = LogAnalyzer()
    return _analyzer
