"""
DX Guardian - Wavelog 数据库适配器
直接连接 Wavelog MySQL 获取用户、日志、DXCC 数据
"""
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
import logging
from backend.config import (
    WAVELOG_DB_HOST,
    WAVELOG_DB_PORT,
    WAVELOG_DB_USER,
    WAVELOG_DB_PASSWORD,
    WAVELOG_DB_DATABASE,
)

logger = logging.getLogger(__name__)

# Wavelog 数据库配置（从环境变量读取）
WAVELOG_CONFIG = {
    'host': WAVELOG_DB_HOST,
    'port': WAVELOG_DB_PORT,
    'user': WAVELOG_DB_USER,
    'password': WAVELOG_DB_PASSWORD,
    'database': WAVELOG_DB_DATABASE,
    'charset': 'utf8mb4',
    'cursorclass': DictCursor,
    'connect_timeout': 10,
    'read_timeout': 30,
    'write_timeout': 30,
}

# 连接池（简单实现）
_connection = None

def get_connection():
    """获取 Wavelog 数据库连接"""
    global _connection
    try:
        if _connection is None or not _connection.open:
            _connection = pymysql.connect(**WAVELOG_CONFIG)
            logger.info("[Wavelog] 数据库连接成功")
        else:
            # 检查连接是否有效
            _connection.ping(reconnect=True)
        return _connection
    except Exception as e:
        logger.error(f"[Wavelog] 数据库连接失败：{e}")
        return None

@contextmanager
def get_cursor():
    """获取数据库游标的上下文管理器"""
    conn = get_connection()
    if conn is None:
        yield None
        return
    
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"[Wavelog] 数据库操作失败：{e}")
        raise
    finally:
        cursor.close()

def get_user_by_callsign(callsign: str) -> Optional[Dict]:
    """根据呼号获取用户信息"""
    with get_cursor() as cursor:
        if cursor is None:
            return None
        cursor.execute(
            "SELECT * FROM user WHERE user_callsign = %s",
            (callsign.upper(),)
        )
        return cursor.fetchone()

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """根据用户 ID 获取用户信息"""
    with get_cursor() as cursor:
        if cursor is None:
            return None
        cursor.execute(
            "SELECT * FROM user WHERE user_id = %s",
            (user_id,)
        )
        return cursor.fetchone()

def get_user_stations(user_id: int) -> List[Dict]:
    """获取用户的所有台站"""
    with get_cursor() as cursor:
        if cursor is None:
            return []
        cursor.execute(
            "SELECT * FROM station WHERE station_user_id = %s",
            (user_id,)
        )
        return cursor.fetchall()

def get_station_by_id(station_id: int) -> Optional[Dict]:
    """根据台站 ID 获取台站信息"""
    with get_cursor() as cursor:
        if cursor is None:
            return None
        cursor.execute(
            "SELECT * FROM station WHERE station_id = %s",
            (station_id,)
        )
        return cursor.fetchone()

def get_user_qsos(user_id: int, station_id: Optional[int] = None, 
                  limit: int = 100, offset: int = 0) -> List[Dict]:
    """获取用户的 QSO 记录"""
    with get_cursor() as cursor:
        if cursor is None:
            return []
        
        # 获取用户的台站 ID 列表
        stations = get_user_stations(user_id)
        station_ids = [s['station_id'] for s in stations]
        
        if not station_ids:
            return []
        
        # 如果指定了 station_id，只查询该台站的 QSO
        if station_id:
            station_ids = [station_id]
        
        placeholders = ','.join(['%s'] * len(station_ids))
        query = f"""
            SELECT * FROM logs
            WHERE station_id IN ({placeholders})
            ORDER BY COL_TIME_ON DESC
            LIMIT %s OFFSET %s
        """
        
        cursor.execute(query, [*station_ids, limit, offset])
        return cursor.fetchall()

def get_user_confirmed_dxcc(user_id: int) -> List[str]:
    """获取用户已确认的 DXCC 实体（LoTW QSL 确认）"""
    with get_cursor() as cursor:
        if cursor is None:
            return []
        
        stations = get_user_stations(user_id)
        station_ids = [s['station_id'] for s in stations]
        
        if not station_ids:
            return []
        
        placeholders = ','.join(['%s'] * len(station_ids))
        cursor.execute(f"""
            SELECT DISTINCT COL_DXCC
            FROM logs
            WHERE station_id IN ({placeholders})
            AND COL_LOTW_QSL_RCVD = 'Y'
        """, station_ids)
        
        return [str(row['COL_DXCC']) for row in cursor.fetchall()]

def get_lotw_users() -> List[Dict]:
    """获取 LoTW 活跃用户列表"""
    with get_cursor() as cursor:
        if cursor is None:
            return []
        cursor.execute("SELECT callsign, last_upload FROM lotw_users WHERE callsign IS NOT NULL")
        return cursor.fetchall()

def get_dxcc_entities() -> List[Dict]:
    """获取 DXCC 实体列表"""
    with get_cursor() as cursor:
        if cursor is None:
            return []
        cursor.execute("SELECT * FROM dxcc_entities ORDER BY dxcc")
        return cursor.fetchall()

def get_dxcc_by_id(dxcc: int) -> Optional[Dict]:
    """根据 DXCC ID 获取实体信息"""
    with get_cursor() as cursor:
        if cursor is None:
            return None
        cursor.execute("SELECT * FROM dxcc_entities WHERE dxcc = %s", (dxcc,))
        return cursor.fetchone()

def get_themes() -> List[Dict]:
    """获取所有主题"""
    with get_cursor() as cursor:
        if cursor is None:
            return []
        cursor.execute("SELECT * FROM theme ORDER BY theme_name")
        return cursor.fetchall()

def get_theme_by_id(theme_id: int) -> Optional[Dict]:
    """根据主题 ID 获取主题信息"""
    with get_cursor() as cursor:
        if cursor is None:
            return None
        cursor.execute("SELECT * FROM theme WHERE theme_id = %s", (theme_id,))
        return cursor.fetchone()

def verify_user(callsign: str, password: str) -> Optional[Dict]:
    """验证用户登录"""
    with get_cursor() as cursor:
        if cursor is None:
            return None
        cursor.execute(
            "SELECT * FROM user WHERE user_callsign = %s AND user_password = %s",
            (callsign.upper(), password)
        )
        return cursor.fetchone()

def test_connection() -> bool:
    """测试数据库连接"""
    try:
        conn = get_connection()
        return conn is not None and conn.open
    except:
        return False
