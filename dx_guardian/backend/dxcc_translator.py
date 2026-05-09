"""
DX Guardian - DXCC 中文翻译模块
"""
import json
from pathlib import Path

DXCC_CN_FILE = Path(__file__).parent.parent / 'data' / 'dxcc_chinese.json'

# 缓存
_dxcc_cn = {}

def load_dxcc_chinese() -> dict:
    global _dxcc_cn
    if not _dxcc_cn and DXCC_CN_FILE.exists():
        with open(DXCC_CN_FILE, 'r', encoding='utf-8') as f:
            _dxcc_cn = json.load(f)
    return _dxcc_cn

def get_dxcc_cn(entity_name: str) -> str:
    """获取 DXCC 中文名称"""
    cn = load_dxcc_chinese()
    return cn.get(entity_name, entity_name)

def translate_spot(spot: dict) -> dict:
    """翻译 Spot 中的 DXCC 名称"""
    dxcc = spot.get('dxcc', '')
    if dxcc:
        spot['dxcc_cn'] = get_dxcc_cn(dxcc)
    return spot

def translate_dxcc_list(items: list) -> list:
    """批量翻译 DXCC 列表（[{dxcc, ...}, ...]）"""
    cn = load_dxcc_chinese()
    for item in items:
        dxcc = item.get('dxcc', '')
        if dxcc and dxcc in cn:
            item['dxcc_cn'] = cn[dxcc]
    return items
