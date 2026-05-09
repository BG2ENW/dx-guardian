"""
Spot 历史数据库模块
使用 SQLite 持久化存储所有 Spot 记录
"""
import sqlite3
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / 'dx_spots.db'

class SpotDatabase:
    """Spot 历史数据库管理类"""
    
    def __init__(self, db_path=None):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径，默认使用 dx_spots.db
        """
        self.db_path = db_path or DATABASE_PATH
        self.lock = threading.Lock()
        self._init_db()
    
    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库表结构"""
        with self.lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 创建 spot 历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS spot_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    callsign TEXT NOT NULL,
                    reporter TEXT NOT NULL,
                    freq REAL NOT NULL,
                    mode TEXT NOT NULL,
                    band TEXT,
                    comment TEXT,
                    grid TEXT,
                    lat REAL,
                    lon REAL,
                    dxcc TEXT,
                    cq INTEGER,
                    itu INTEGER,
                    time TEXT,
                    _server_ts REAL NOT NULL,
                    source TEXT DEFAULT 'cluster',
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            ''')
            
            # 创建索引加速查询
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_callsign 
                ON spot_history(callsign)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_reporter 
                ON spot_history(reporter)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_time 
                ON spot_history(_server_ts)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_band 
                ON spot_history(band)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON spot_history(time)
            ''')
            
            # 创建组合索引（查询我的 spot 用）
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_callsign_time 
                ON spot_history(callsign, _server_ts DESC)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_reporter_time 
                ON spot_history(reporter, _server_ts DESC)
            ''')
            
            conn.commit()
            conn.close()
    
    def insert(self, spot):
        """
        插入一条 spot 记录
        
        Args:
            spot: spot 字典对象
            
        Returns:
            int: 插入的记录 ID
        """
        with self.lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO spot_history (
                    callsign, reporter, freq, mode, band, comment, 
                    grid, lat, lon, dxcc, cq, itu, time, _server_ts, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                spot.get('callsign', ''),
                spot.get('reporter', ''),
                spot.get('freq', 0),
                spot.get('mode', ''),
                spot.get('band', ''),
                spot.get('comment', ''),
                spot.get('grid', ''),
                spot.get('lat', 0),
                spot.get('lon', 0),
                spot.get('dxcc', ''),
                spot.get('cq'),
                spot.get('itu'),
                spot.get('time', ''),
                spot.get('_server_ts', time.time()),
                spot.get('source', 'cluster')
            ))
            
            row_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return row_id
    
    def get_related_spots(self, callsign, limit=500, hours=168):
        """
        获取与指定呼号相关的所有 spot
        
        Args:
            callsign: 呼号
            limit: 返回数量限制
            hours: 时间范围（小时），默认 168 小时（7 天）
            
        Returns:
            tuple: (i_spotted 列表，they_spotted_me 列表)
        """
        callsign = callsign.upper()
        cutoff_ts = time.time() - (hours * 3600)
        
        with self.lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 查询我上报的 DX 电台（reporter = mycall）
            cursor.execute('''
                SELECT * FROM spot_history 
                WHERE reporter = ? AND _server_ts >= ?
                ORDER BY _server_ts DESC
                LIMIT ?
            ''', (callsign, cutoff_ts, limit))
            i_spotted = [dict(row) for row in cursor.fetchall()]
            
            # 查询别人上报我的（callsign = mycall）
            cursor.execute('''
                SELECT * FROM spot_history 
                WHERE callsign = ? AND _server_ts >= ?
                ORDER BY _server_ts DESC
                LIMIT ?
            ''', (callsign, cutoff_ts, limit))
            they_spotted_me = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            return i_spotted, they_spotted_me
    
    def get_recent_spots(self, limit=1000, hours=24):
        """
        获取最近的 spot 记录（用于前端 history API）
        
        Args:
            limit: 返回数量限制
            hours: 时间范围（小时）
            
        Returns:
            list: spot 记录列表
        """
        cutoff_ts = time.time() - (hours * 3600)
        
        with self.lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM spot_history 
                WHERE _server_ts >= ?
                ORDER BY _server_ts DESC
                LIMIT ?
            ''', (cutoff_ts, limit))
            
            spots = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return spots
    
    def count_total(self, hours=None):
        """
        统计记录总数
        
        Args:
            hours: 时间范围（小时），None 表示全部
            
        Returns:
            int: 总记录数
        """
        with self.lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            if hours is None:
                cursor.execute('SELECT COUNT(*) FROM spot_history')
            else:
                cutoff_ts = time.time() - (hours * 3600)
                cursor.execute(
                    'SELECT COUNT(*) FROM spot_history WHERE _server_ts >= ?',
                    (cutoff_ts,)
                )
            
            count = cursor.fetchone()[0]
            conn.close()
            return count
    
    def cleanup(self, max_age_hours=168, max_records=100000):
        """
        清理过期和超量的记录
        
        Args:
            max_age_hours: 最大保留时间（小时）
            max_records: 最大记录数
        """
        cutoff_ts = time.time() - (max_age_hours * 3600)
        
        with self.lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 删除过期记录
            cursor.execute('''
                DELETE FROM spot_history 
                WHERE _server_ts < ?
            ''', (cutoff_ts,))
            deleted_by_time = cursor.rowcount
            
            # 如果记录数超过上限，删除最老的
            cursor.execute('SELECT COUNT(*) FROM spot_history')
            count = cursor.fetchone()[0]
            
            deleted_by_count = 0
            if count > max_records:
                excess = count - max_records
                cursor.execute('''
                    DELETE FROM spot_history 
                    WHERE id IN (
                        SELECT id FROM spot_history 
                        ORDER BY _server_ts ASC 
                        LIMIT ?
                    )
                ''', (excess,))
                deleted_by_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return deleted_by_time, deleted_by_count
    
    def close(self):
        """关闭数据库连接（通常不需要手动调用）"""
        pass  # SQLite 连接在每次操作后自动关闭


# 全局单例
_db_instance = None

def get_database():
    """获取数据库全局实例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = SpotDatabase()
    return _db_instance


if __name__ == '__main__':
    # 测试
    db = SpotDatabase(':memory:')  # 内存数据库测试
    print("数据库初始化成功")
    
    # 测试插入
    test_spot = {
        'callsign': 'JA1ABC',
        'reporter': 'BG2ENW',
        'freq': 14074.0,
        'mode': 'FT8',
        'band': '20m',
        'comment': 'CQ',
        'grid': 'PM96',
        'lat': 35.6762,
        'lon': 139.6503,
        'dxcc': 'Japan',
        'time': '0830Z',
        '_server_ts': time.time()
    }
    
    row_id = db.insert(test_spot)
    print(f"插入记录 ID: {row_id}")
    
    # 测试查询
    i_spotted, they_spotted_me = db.get_related_spots('BG2ENW')
    print(f"我上报：{len(i_spotted)} 条")
    print(f"上报我：{len(they_spotted_me)} 条")
