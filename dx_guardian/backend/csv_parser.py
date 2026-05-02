"""
CSV 文件解析器
支持 Wavelog 导出的 CSV 和其他标准日志 CSV 格式
"""
import csv
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
from adif_parser import QSORecord


class CSVParserError(Exception):
    """CSV 解析错误"""
    pass


class CSVParser:
    """CSV 日志文件解析器"""
    
    def __init__(self):
        self.stats = {
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'errors': []
        }
    
    def parse_file(self, file_path: str) -> tuple[List[QSORecord], List[str]]:
        """
        解析 CSV 文件
        
        Args:
            file_path: CSV 文件路径
            
        Returns:
            (QSO 记录列表, 错误列表)
        """
        self.stats = {
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'errors': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 使用 csv.DictReader 读取
                reader = csv.DictReader(f)
                rows = list(reader)
        except FileNotFoundError:
            raise CSVParserError(f"文件不存在: {file_path}")
        except Exception as e:
            raise CSVParserError(f"读取文件失败: {e}")
        
        return self._parse_rows(rows)
    
    def _parse_rows(self, rows: List[dict]) -> tuple[List[QSORecord], List[str]]:
        """解析 CSV 行"""
        records = []
        
        for row in rows:
            self.stats['total_records'] += 1
            
            try:
                record = self._parse_row(row)
                if record:
                    records.append(record)
                    self.stats['valid_records'] += 1
            except Exception as e:
                self.stats['invalid_records'] += 1
                self.stats['errors'].append(str(e))
        
        return records, self.stats['errors']
    
    def _parse_row(self, row: dict) -> Optional[QSORecord]:
        """解析单行 CSV"""
        # 尝试匹配常见的 CSV 列名格式
        
        # 提取 CALL（可能有多种命名方式）
        call = self._get_field(row, ['call', 'callsign', 'CALL', 'CALLSIGN'])
        if not call:
            raise CSVParserError("缺少呼叫号（CALL）字段")
        
        # 提取 BAND
        band = self._get_field(row, ['band', 'Band', 'BAND'])
        if not band:
            # 尝试从频率提取波段
            freq = self._get_field(row, ['freq', 'frequency', 'FREQ', 'FREQUENCY'])
            if freq:
                band = self._freq_to_band(float(freq))
        if not band:
            raise CSVParserError("缺少波段（BAND）字段")
        
        # 提取 MODE
        mode = self._get_field(row, ['mode', 'Mode', 'MODE', 'mode_tx'])
        if not mode:
            raise CSVParserError("缺少模式（MODE）字段")
        
        # 提取 QSO_DATE
        qso_date = self._get_field(row, ['qso_date', 'date', 'Date', 'DATE', 'QSO_DATE', 'COL_QSO_DATE'])
        if not qso_date:
            raise CSVParserError("缺少日期（QSO_DATE）字段")
        qso_date = self._normalize_date(qso_date)
        
        # 提取 TIME_ON
        time_on = self._get_field(row, ['time_on', 'time', 'Time', 'TIME', 'TIME_ON', 'time_on_utc'])
        if not time_on:
            time_on = "000000"
        time_on = self._normalize_time(time_on)
        
        # 构建对象
        return QSORecord(
            call=call,
            band=band,
            mode=mode,
            qso_date=qso_date,
            time_on=time_on,
            band_rx=self._get_field(row, ['band_rx']),
            freq=self._parse_float(self._get_field(row, ['freq', 'FREQ'])),
            freq_rx=self._parse_float(self._get_field(row, ['freq_rx'])),
            rst_sent=self._get_field(row, ['rst_sent', 'rst_s', 'RST_SENT']),
            rst_rcvd=self._get_field(row, ['rst_rcvd', 'rst_r', 'RST_RCVD']),
            name=self._get_field(row, ['name', 'Name', 'NAME']),
            grid=self._get_field(row, ['gridsquare', 'grid', 'GRIDSQUARE']),
            cq_zone=self._parse_int(self._get_field(row, ['cqz', 'cq_zone', 'CQZ'])),
            itu_zone=self._parse_int(self._get_field(row, ['ituz', 'itu_zone', 'ITUZ'])),
            dxcc=self._get_field(row, ['dxcc', 'DXCC']),
            state=self._get_field(row, ['state', 'us_state', 'STATE']),
            county=self._get_field(row, ['county', 'County', 'COUNTY']),
            country=self._get_field(row, ['country', 'Country', 'COUNTRY']),
            cont=self._get_field(row, ['cont', 'continent', 'CONT']),
            lat=self._parse_float(self._get_field(row, ['lat', 'latitude'])),
            lon=self._parse_float(self._get_field(row, ['lon', 'longitude'])),
            my_grid=self._get_field(row, ['my_gridsquare', 'my_grid']),
            notes=self._get_field(row, ['notes', 'comment', 'NOTES', 'COMMENT']),
            operator=self._get_field(row, ['operator', 'OPERATOR']),
            station_callsign=self._get_field(row, ['station_callsign', 'STATION_CALLSIGN'])
        )
    
    def _get_field(self, row: dict, possible_keys: List[str]) -> Optional[str]:
        """获取字段值（支持多种可能的列名）"""
        for key in possible_keys:
            if key in row and row[key] and str(row[key]).strip():
                return str(row[key]).strip()
        return None
    
    def _normalize_date(self, date_str: str) -> str:
        """日期标准化: 支持多种格式 -> YYYY-MM-DD"""
        if not date_str:
            return "0000-00-00"
        
        date_str = date_str.strip()
        
        # YYYY-MM-DD
        if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
            return date_str
        
        # YYYY/MM/DD
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
        
        # DD.MM.YYYY (欧洲格式)
        if '.' in date_str and len(date_str) >= 8:
            parts = date_str.split('.')
            if len(parts) == 3 and len(parts[2]) == 4:
                return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        
        # YYYYMMDD
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        return date_str
    
    def _normalize_time(self, time_str: str) -> str:
        """时间标准化: 支持多种格式 -> HH:MM:SS"""
        if not time_str:
            return "00:00:00"
        
        time_str = time_str.strip()
        
        # HH:MM:SS
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 3:
                return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}"
            elif len(parts) == 2:
                return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:00"
        
        # HHMMSS
        if len(time_str) >= 6:
            if len(time_str) == 6:
                return f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
            elif len(time_str) == 4:
                return f"{time_str[0:2]}:{time_str[2:4]}:00"
        
        return time_str
    
    def _parse_float(self, val: Optional[str]) -> Optional[float]:
        """解析浮点数"""
        if not val:
            return None
        try:
            return float(val)
        except ValueError:
            return None
    
    def _parse_int(self, val: Optional[str]) -> Optional[int]:
        """解析整数"""
        if not val:
            return None
        try:
            return int(val)
        except ValueError:
            return None
    
    def _freq_to_band(self, freq_mhz: float) -> Optional[str]:
        """频率转波段"""
        bands = [
            (1.81, 2.0, '160m'), (3.5, 4.0, '80m'), (5.25, 5.45, '60m'),
            (7.0, 7.3, '40m'), (10.1, 10.15, '30m'), (14.0, 14.35, '20m'),
            (18.068, 18.168, '17m'), (21.0, 21.45, '15m'), (24.89, 24.99, '12m'),
            (28.0, 29.7, '10m'), (50.0, 54.0, '6m'), (144.0, 148.0, '2m'),
        ]
        for low, high, name in bands:
            if low <= freq_mhz <= high:
                return name
        return None


# 测试代码
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("用法: python csv_parser.py <CSV文件路径>")
        sys.exit(1)
    
    parser = CSVParser()
    file_path = sys.argv[1]
    
    try:
        records, errors = parser.parse_file(file_path)
        print(f"✅ 解析完成")
        print(f"总记录数: {parser.stats['total_records']}")
        print(f"有效记录: {parser.stats['valid_records']}")
        print(f"无效记录: {parser.stats['invalid_records']}")
        
        if errors:
            print(f"\\n错误 ({len(errors)}):")
            for err in errors[:10]:
                print(f"  - {err}")
        
        if records:
            print(f"\\n前5条记录:")
            for i, record in enumerate(records[:5]):
                print(f"{i+1}. {record.call} @ {record.band} {record.mode} {record.qso_date} {record.time_on}")
    
    except CSVParserError as e:
        print(f"❌ 解析失败: {e}")
        sys.exit(1)
