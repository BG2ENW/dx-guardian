"""
LoTW 用户活动数据库加载器
加载 /workspace/lotw-user-activity.csv 用于验证呼号有效性
"""
import csv
from datetime import datetime
from pathlib import Path
from typing import Set, Dict, Optional

class LOTWDatabase:
    """LoTW 用户数据库"""
    
    def __init__(self, csv_file: str = '/workspace/lotw-user-activity.csv'):
        """初始化并加载 LoTW 数据库"""
        self.users = set()
        self.activity = {}
        
        # 检查文件
        import os
        if not os.path.exists(csv_file) or os.path.getsize(csv_file) < 100:
            print(f'⚠️  LoTW 数据库不存在或太小 ({csv_file})，使用简化模式')
            return
        
        self._load_csv(csv_file)
    
    def _load_csv(self, filepath: str):
        """加载 CSV 文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 3:
                        callsign = row[0].strip()
                        first_date = row[1].strip()
                        last_time = row[2].strip()
                        
                        self.users.add(callsign)
                        self.activity[callsign] = {
                            'first_activity': first_date,
                            'last_activity': last_time
                        }
            
            print(f'✅ LoTW 数据库已加载：{len(self.users):,} 个活跃呼号')
            
        except Exception as e:
            print(f'❌ LoTW 数据库加载失败：{e}')
    
    def is_active(self, callsign: str) -> bool:
        """检查呼号是否为 LoTW 活跃用户"""
        return callsign.upper().strip() in self.users
    
    def get_activity(self, callsign: str) -> Optional[Dict]:
        """获取呼号活动信息"""
        return self.activity.get(callsign.upper().strip())
    
    def count(self) -> int:
        """返回用户数量"""
        return len(self.users)


# 单例模式
_lotw_instance = None

def get_lotw_database() -> LOTWDatabase:
    """获取 LoTW 数据库单例"""
    global _lotw_instance
    if _lotw_instance is None:
        _lotw_instance = LOTWDatabase()
    return _lotw_instance


# 测试
if __name__ == '__main__':
    lotw = get_lotw_database()
    
    test_callsigns = ['BG2ENW', 'JA1AAA', 'W1AW', '1A0C', 'N7ZPU', 'DL7UAI']
    
    print(f"\n数据库统计:")
    print(f"  总用户数：{lotw.count():,}")
    
    print("\n测试查询:")
    for cs in test_callsigns:
        is_active = lotw.is_active(cs)
        activity = lotw.get_activity(cs)
        
        status = "✓" if is_active else "✗"
        if activity:
            print(f"{status} {cs:12} 首次：{activity['first_activity']:12} 最后：{activity['last_activity']}")
        else:
            print(f"{status} {cs:12} 无记录")
