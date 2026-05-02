"""
ADIF 文件解析器
支持 ADIF 3.1 标准（https://www.adif.org/3.1/）
"""
import re
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path


@dataclass
class ADIFField:
    """ADIF 字段"""
    name: str
    value: str
    length: int
    data_type: str


@dataclass
class QSORecord:
    """QSO 记录"""
    call: str                    # 呼号
    band: str                    # 波段
    mode: str                    # 模式
    qso_date: str                # QSO 日期 (YYYY-MM-DD)
    time_on: str                 # 时间 (HH:MM:SS)
    band_rx: Optional[str] = None      # 接收波段（卫星用）
    freq: Optional[float] = None      # 频率 (MHz)
    freq_rx: Optional[float] = None   # 接收频率（卫星用）
    rst_sent: Optional[str] = None    # 发送 RST
    rst_rcvd: Optional[str] = None    # 接收 RST
    name: Optional[str] = None        # 对方姓名
    grid: Optional[str] = None        # Grid 定位
    cq_zone: Optional[int] = None     # CQ 区域
    itu_zone: Optional[int] = None    # ITU 区域
    dxcc: Optional[str] = None        # DXCC 实体
    cqz: Optional[int] = None         # CQ 区域（简写）
    ituz: Optional[int] = None        # ITU 区域（简写）
    county: Optional[str] = None      # 州/县（美国用）
    state: Optional[str] = None       # 州（美国用）
    country: Optional[str] = None     # 国家
    iota: Optional[str] = None        # IOTA 代号
    cont: Optional[str] = None        # 大洲
    lat: Optional[float] = None       # 纬度
    lon: Optional[float] = None       # 经度
    my_grid: Optional[str] = None     # 我方 Grid
    notes: Optional[str] = None       # 备注
    operator: Optional[str] = None    # 操作员呼号
    station_callsign: Optional[str] = None  # 台站呼号
    
    # 转换为字典
    def to_dict(self) -> dict:
        result = {
            'call': self.call,
            'band': self.band,
            'mode': self.mode,
            'qso_date': self.qso_date,
            'time_on': self.time_on,
        }
        # 添加可选字段
        optional_fields = [
            'band_rx', 'freq', 'freq_rx', 'rst_sent', 'rst_rcvd', 'name', 'grid',
            'cq_zone', 'itu_zone', 'dxcc', 'cqz', 'ituz', 'county', 'state',
            'country', 'iota', 'cont', 'lat', 'lon', 'my_grid', 'notes',
            'operator', 'station_callsign'
        ]
        for field in optional_fields:
            value = getattr(self, field)
            if value is not None:
                result[field] = value
        return result


class ADIFParserError(Exception):
    """ADIF 解析错误"""
    pass


class ADIFParser:
    """ADIF 文件解析器"""
    
    # 必需字段
    REQUIRED_FIELDS = ['CALL', 'BAND', 'MODE', 'QSO_DATE', 'TIME_ON']
    
    # 日期格式：YYYYMMDD -> YYYY-MM-DD
    # 时间格式：HHMMSS -> HH:MM:SS
    
    def __init__(self):
        self.stats = {
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'errors': []
        }
    
    def parse_file(self, file_path: str) -> tuple[List[QSORecord], List[str]]:
        """
        解析 ADIF 文件
        
        Args:
            file_path: ADIF 文件路径
            
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
                content = f.read()
        except FileNotFoundError:
            raise ADIFParserError(f"文件不存在: {file_path}")
        except Exception as e:
            raise ADIFParserError(f"读取文件失败: {e}")
        
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> tuple[List[QSORecord], List[str]]:
        """
        解析 ADIF 内容
        
        Returns:
            (QSO 记录列表, 错误列表)
        """
        records = []
        
        # 跳过 ADIF 头部（EOH 之前）
        eoh_pos = content.upper().find('<EOH>')
        if eoh_pos != -1:
            content = content[eoh_pos + 5:]
        
        # 解析 QSO 记录（<EOR> 分隔）
        records_text = content.split('<EOR>')
        
        for record_text in records_text:
            record_text = record_text.strip()
            if not record_text:
                continue
            
            self.stats['total_records'] += 1
            
            try:
                record = self._parse_record(record_text)
                if record:
                    records.append(record)
                    self.stats['valid_records'] += 1
            except Exception as e:
                self.stats['invalid_records'] += 1
                self.stats['errors'].append(str(e))
        
        return records, self.stats['errors']
    
    def _parse_record(self, record_text: str) -> Optional[QSORecord]:
        """解析单条 QSO 记录"""
        # 提取所有字段: <NAME:LENGTH>VALUE
        field_pattern = re.compile(r'<([A-Z_0-9]+):(\d+)(:\d+)?>([^<]*)', re.IGNORECASE)
        matches = field_pattern.findall(record_text)
        
        fields = {}
        for match in matches:
            name = match[0].upper()
            length = int(match[1])
            value = match[3]
            fields[name] = value
        
        # 验证必需字段
        for field in self.REQUIRED_FIELDS:
            if field not in fields:
                raise ADIFParserError(f"缺少必需字段: {field}")
        
        # 构建对象
        return QSORecord(
            call=fields['CALL'],
            band=fields['BAND'],
            mode=fields['MODE'],
            qso_date=self._format_date(fields['QSO_DATE']),
            time_on=self._format_time(fields['TIME_ON']),
            band_rx=fields.get('BAND_RX'),
            freq=self._parse_freq(fields.get('FREQ')),
            freq_rx=self._parse_freq(fields.get('FREQ_RX')),
            rst_sent=fields.get('RST_SENT'),
            rst_rcvd=fields.get('RST_RCVD'),
            name=fields.get('NAME'),
            grid=fields.get('GRIDSQUARE'),
            cq_zone=self._parse_int(fields.get('CQZ', fields.get('CQ_ZONE'))),
            itu_zone=self._parse_int(fields.get('ITUZ', fields.get('ITU_ZONE'))),
            dxcc=fields.get('DXCC'),
            cqz=self._parse_int(fields.get('CQZ')),
            ituz=self._parse_int(fields.get('ITUZ')),
            county=fields.get('COUNTY'),
            state=fields.get('STATE'),
            country=fields.get('COUNTRY'),
            iota=fields.get('IOTA'),
            cont=fields.get('CONT'),
            lat=self._parse_float(fields.get('LAT')),
            lon=self._parse_float(fields.get('LON')),
            my_grid=fields.get('MY_GRIDSQUARE'),
            notes=fields.get('NOTES', fields.get('COMMENT')),
            operator=fields.get('OPERATOR'),
            station_callsign=fields.get('STATION_CALLSIGN')
        )
    
    def _format_date(self, adif_date: str) -> str:
        """日期格式化: YYYYMMDD -> YYYY-MM-DD"""
        if not adif_date or len(adif_date) != 8:
            return adif_date
        return f"{adif_date[0:4]}-{adif_date[4:6]}-{adif_date[6:8]}"
    
    def _format_time(self, adif_time: str) -> str:
        """时间格式化: HHMMSS -> HH:MM:SS"""
        if not adif_time:
            return "00:00:00"
        if len(adif_time) >= 6:
            return f"{adif_time[0:2]}:{adif_time[2:4]}:{adif_time[4:6]}"
        elif len(adif_time) == 4:
            return f"{adif_time[0:2]}:{adif_time[2:4]}:00"
        return adif_time
    
    def _parse_freq(self, freq_str: Optional[str]) -> Optional[float]:
        """解析频率"""
        if not freq_str:
            return None
        try:
            # ADIF 中的频率通常是 MHz
            return float(freq_str)
        except ValueError:
            return None
    
    def _parse_int(self, int_str: Optional[str]) -> Optional[int]:
        """解析整数"""
        if not int_str:
            return None
        try:
            return int(int_str)
        except ValueError:
            return None
    
    def _parse_float(self, float_str: Optional[str]) -> Optional[float]:
        """解析浮点数"""
        if not float_str:
            return None
        try:
            return float(float_str)
        except ValueError:
            return None


# 测试代码
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("用法: python adif_parser.py <ADIF文件路径>")
        sys.exit(1)
    
    parser = ADIFParser()
    file_path = sys.argv[1]
    
    try:
        records, errors = parser.parse_file(file_path)
        print(f"✅ 解析完成")
        print(f"总记录数: {parser.stats['total_records']}")
        print(f"有效记录: {parser.stats['valid_records']}")
        print(f"无效记录: {parser.stats['invalid_records']}")
        
        if errors:
            print(f"\\n错误 ({len(errors)}):")
            for err in errors[:10]:  # 只显示前10个错误
                print(f"  - {err}")
        
        # 打印前5条记录
        if records:
            print(f"\\n前5条记录:")
            for i, record in enumerate(records[:5]):
                print(f"{i+1}. {record.call} @ {record.band} {record.mode} {record.qso_date} {record.time_on}")
    
    except ADIFParserError as e:
        print(f"❌ 解析失败: {e}")
        sys.exit(1)
