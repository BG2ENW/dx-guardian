"""
DX Guardian - 预警引擎 V2
完整功能：持久化、优先级、去重、静默、统计
"""
import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional
import threading

# 优先级定义
PRIORITY_URGENT = 'urgent'      # 呼号精确匹配
PRIORITY_IMPORTANT = 'important'  # 前缀/DXCC匹配
PRIORITY_NORMAL = 'normal'      # 波段/模式匹配

PRIORITY_ORDER = {PRIORITY_URGENT: 0, PRIORITY_IMPORTANT: 1, PRIORITY_NORMAL: 2}
PRIORITY_LABELS = {
    PRIORITY_URGENT: '紧急',
    PRIORITY_IMPORTANT: '重要',
    PRIORITY_NORMAL: '普通'
}

class AlertEngineV2:
    """增强版预警引擎"""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / 'backend' / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.alerts_file = self.data_dir / 'alerts.json'
        self.silence_file = self.data_dir / 'silenced_callsigns.json'
        self.stats_file = self.data_dir / 'alert_stats.json'
        
        self.alerts = []  # 内存中的预警列表
        self.silenced_callsigns = set()  # 静默呼号集合
        self.alert_history_max = 1000
        self.dedup_window_seconds = 300  # 5分钟去重窗口
        
        self.lock = threading.Lock()
        
        # 加载持久化数据
        self._load_alerts()
        self._load_silenced()
        
    def _load_alerts(self):
        """从文件加载预警历史"""
        try:
            if self.alerts_file.exists():
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.alerts = data.get('alerts', [])
                    # 清理过期数据（保留7天）
                    self._cleanup_old_alerts()
        except Exception as e:
            print(f'[预警引擎] 加载预警历史失败: {e}')
            self.alerts = []
    
    def _save_alerts(self):
        """保存预警到文件"""
        try:
            with self.lock:
                with open(self.alerts_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'alerts': self.alerts[-self.alert_history_max:],
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'[预警引擎] 保存预警失败: {e}')
    
    def _load_silenced(self):
        """加载静默呼号列表"""
        try:
            if self.silence_file.exists():
                with open(self.silence_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.silenced_callsigns = set(data.get('silenced', []))
        except Exception as e:
            print(f'[预警引擎] 加载静默列表失败: {e}')
            self.silenced_callsigns = set()
    
    def _save_silenced(self):
        """保存静默呼号列表"""
        try:
            with self.lock:
                with open(self.silence_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'silenced': list(self.silenced_callsigns),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'[预警引擎] 保存静默列表失败: {e}')
    
    def _cleanup_old_alerts(self):
        """清理7天前的预警"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        self.alerts = [
            a for a in self.alerts 
            if datetime.fromisoformat(a['created_at']) > cutoff
        ]
    
    def _get_priority(self, target_type: str) -> str:
        """根据匹配类型确定优先级"""
        priority_map = {
            'callsign': PRIORITY_URGENT,
            'prefix': PRIORITY_IMPORTANT,
            'dxcc': PRIORITY_IMPORTANT,
            'band': PRIORITY_NORMAL,
            'mode': PRIORITY_NORMAL
        }
        return priority_map.get(target_type, PRIORITY_NORMAL)
    
    def _is_duplicate(self, spot: dict) -> bool:
        """检查是否重复（同一呼号+波段在5分钟内）"""
        callsign = spot.get('callsign', '').upper()
        band = spot.get('band', '')
        now = datetime.now(timezone.utc)
        
        for alert in self.alerts:
            alert_spot = alert.get('spot', {})
            if (alert_spot.get('callsign', '').upper() == callsign and 
                alert_spot.get('band') == band):
                alert_time = datetime.fromisoformat(alert['created_at'])
                if (now - alert_time).total_seconds() < self.dedup_window_seconds:
                    return True
        return False
    
    def _is_silenced(self, callsign: str) -> bool:
        """检查呼号是否被静默"""
        return callsign.upper() in self.silenced_callsigns
    
    def check_spot(self, spot: dict, watchlist: list) -> list:
        """检查 Spot 是否匹配关注列表"""
        alerts = []
        callsign = spot.get('callsign', '')
        
        # 检查是否被静默
        if self._is_silenced(callsign):
            return alerts
        
        # 检查是否重复
        if self._is_duplicate(spot):
            return alerts
        
        if not watchlist:
            return alerts
        
        for item in watchlist:
            if not item.get('enabled', True):
                continue
            
            if self._match_item(spot, item):
                priority = self._get_priority(item['target_type'])
                alert = {
                    'id': f"alert_{int(time.time() * 1000)}_{len(alerts)}",
                    'type': item['target_type'],
                    'priority': priority,
                    'priority_label': PRIORITY_LABELS[priority],
                    'target_value': item['target_value'],
                    'message': self._generate_alert_message(spot, item),
                    'spot': spot,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'is_read': False,
                    'matched_item': item
                }
                alerts.append(alert)
                self._cache_alert(alert)
        
        return alerts
    
    def _match_item(self, spot: dict, item: dict) -> bool:
        """检查 Spot 是否匹配单个关注项"""
        target_type = item['target_type']
        target_value = item['target_value'].upper()
        spot_callsign = spot.get('callsign', '').upper()
        spot_band = spot.get('band', '')
        spot_mode = spot.get('mode', '').upper()
        spot_dxcc = spot.get('dxcc', '').upper()
        
        # 波段和模式限定条件检查
        if item.get('band_preference'):
            if spot_band != item['band_preference']:
                return False
        if item.get('mode_preference'):
            if spot_mode != item['mode_preference'].upper():
                return False
        
        # 根据类型匹配
        if target_type == 'callsign':
            return spot_callsign == target_value
        elif target_type == 'prefix':
            return spot_callsign.startswith(target_value)
        elif target_type == 'dxcc':
            if spot_dxcc == target_value:
                return True
            return spot_callsign.startswith(target_value)
        elif target_type == 'band':
            return spot_band == target_value
        elif target_type == 'mode':
            return spot_mode == target_value.upper()
        
        return False
    
    def _generate_alert_message(self, spot: dict, item: dict) -> str:
        """生成预警消息文本"""
        callsign = spot.get('callsign', '?')
        freq = spot.get('freq', 0)
        band = spot.get('band', '?')
        mode = spot.get('mode', '?')
        dxcc = spot.get('dxcc', '')
        
        type_labels = {
            'callsign': '呼号',
            'prefix': '前缀',
            'dxcc': 'DXCC',
            'band': '波段',
            'mode': '模式'
        }
        
        msg = f"{type_labels.get(item['target_type'], item['target_type'])} {item['target_value']}"
        if dxcc:
            msg += f" ({dxcc})"
        msg += f" 出现在 {band} {mode}"
        if freq > 0:
            msg += f" {freq:.3f}MHz"
        
        return msg
    
    def _cache_alert(self, alert: dict):
        """缓存预警记录"""
        with self.lock:
            self.alerts.append(alert)
            if len(self.alerts) > self.alert_history_max:
                self.alerts = self.alerts[-self.alert_history_max:]
        self._save_alerts()
    
    def get_alerts(self, limit: int = 50, priority: str = None, unread_only: bool = False) -> list:
        """获取预警列表，支持筛选"""
        result = self.alerts.copy()
        
        # 按优先级筛选
        if priority:
            result = [a for a in result if a.get('priority') == priority]
        
        # 只显示未读
        if unread_only:
            result = [a for a in result if not a.get('is_read', False)]
        
        # 按优先级和时间排序
        result.sort(key=lambda x: (
            PRIORITY_ORDER.get(x.get('priority', PRIORITY_NORMAL), 2),
            x.get('created_at', '')
        ), reverse=True)
        
        return result[-limit:]
    
    def mark_as_read(self, alert_id: str) -> bool:
        """标记预警为已读"""
        with self.lock:
            for alert in self.alerts:
                if alert['id'] == alert_id:
                    alert['is_read'] = True
                    self._save_alerts()
                    return True
        return False
    
    def mark_all_as_read(self) -> int:
        """标记所有预警为已读，返回标记数量"""
        count = 0
        with self.lock:
            for alert in self.alerts:
                if not alert.get('is_read', False):
                    alert['is_read'] = True
                    count += 1
            if count > 0:
                self._save_alerts()
        return count
    
    def silence_callsign(self, callsign: str) -> bool:
        """添加呼号到静默列表"""
        callsign = callsign.upper().strip()
        if callsign:
            self.silenced_callsigns.add(callsign)
            self._save_silenced()
            return True
        return False
    
    def unsilence_callsign(self, callsign: str) -> bool:
        """从静默列表移除呼号"""
        callsign = callsign.upper().strip()
        if callsign in self.silenced_callsigns:
            self.silenced_callsigns.discard(callsign)
            self._save_silenced()
            return True
        return False
    
    def get_silenced_callsigns(self) -> list:
        """获取静默呼号列表"""
        return sorted(list(self.silenced_callsigns))
    
    def get_stats(self) -> dict:
        """获取预警统计"""
        total = len(self.alerts)
        unread = sum(1 for a in self.alerts if not a.get('is_read', False))
        
        # 按优先级统计
        by_priority = {
            PRIORITY_URGENT: 0,
            PRIORITY_IMPORTANT: 0,
            PRIORITY_NORMAL: 0
        }
        for alert in self.alerts:
            p = alert.get('priority', PRIORITY_NORMAL)
            by_priority[p] = by_priority.get(p, 0) + 1
        
        # 按类型统计
        by_type = {}
        for alert in self.alerts:
            t = alert.get('type', 'unknown')
            by_type[t] = by_type.get(t, 0) + 1
        
        # 今日统计
        today = datetime.now(timezone.utc).date()
        today_count = sum(
            1 for a in self.alerts 
            if datetime.fromisoformat(a['created_at']).date() == today
        )
        
        return {
            'total': total,
            'unread': unread,
            'today': today_count,
            'by_priority': {
                'urgent': by_priority[PRIORITY_URGENT],
                'important': by_priority[PRIORITY_IMPORTANT],
                'normal': by_priority[PRIORITY_NORMAL]
            },
            'by_type': by_type,
            'silenced_count': len(self.silenced_callsigns)
        }
    
    def delete_alert(self, alert_id: str) -> bool:
        """删除单个预警"""
        with self.lock:
            original_len = len(self.alerts)
            self.alerts = [a for a in self.alerts if a['id'] != alert_id]
            if len(self.alerts) < original_len:
                self._save_alerts()
                return True
        return False
    
    def clear_all_alerts(self) -> int:
        """清空所有预警，返回删除数量"""
        with self.lock:
            count = len(self.alerts)
            self.alerts = []
            self._save_alerts()
        return count

# 全局实例
alert_engine_v2 = None

def init_alert_engine(data_dir: Path = None):
    """初始化预警引擎"""
    global alert_engine_v2
    alert_engine_v2 = AlertEngineV2(data_dir)
    return alert_engine_v2

def get_alert_engine() -> AlertEngineV2:
    """获取预警引擎实例"""
    global alert_engine_v2
    if alert_engine_v2 is None:
        alert_engine_v2 = AlertEngineV2()
    return alert_engine_v2