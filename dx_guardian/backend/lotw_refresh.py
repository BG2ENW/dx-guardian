"""
LoTW 状态自动刷新后台任务

定期从 Wavelog 数据库同步 LoTW 活跃用户列表到本地缓存，
支持批量查询和 TTL 缓存策略。
"""
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Set
import pymysql
from backend.config import (
    WAVELOG_DB_HOST,
    WAVELOG_DB_PORT,
    WAVELOG_DB_USER,
    WAVELOG_DB_PASSWORD,
    WAVELOG_DB_DATABASE,
)
import logging

logger = logging.getLogger(__name__)

# ========== 缓存配置 ==========
LOTW_CACHE_TTL_HOURS = 24  # 缓存有效期（小时）
LOTW_REFRESH_INTERVAL_SECONDS = 3600  # 后台刷新间隔（秒）

# ========== 全局状态 ==========
_lotw_cache: Dict[str, bool] = {}  # callsign -> is_active
_cache_timestamp: datetime = None
_refresh_thread: threading.Thread = None
_running = False


def get_lotw_active_status(callsigns: List[str]) -> Dict[str, bool]:
    """
    批量查询 LoTW 活跃状态
    
    Args:
        callsigns: 呼号列表
    
    Returns:
        {callsign: is_active} 字典
    """
    global _cache_timestamp, _lotw_cache
    
    # 检查缓存是否过期
    now = datetime.now()
    if _cache_timestamp and (now - _cache_timestamp).total_seconds() < LOTW_CACHE_TTL_HOURS * 3600:
        # 缓存有效，直接返回
        return {call: _lotw_cache.get(call.upper(), False) for call in callsigns}
    
    # 缓存过期，触发刷新
    _refresh_lotw_cache()
    
    # 返回缓存结果
    return {call: _lotw_cache.get(call.upper(), False) for call in callsigns}


def is_lotw_active(callsign: str) -> bool:
    """
    检查单个呼号是否 LoTW 活跃
    
    Args:
        callsign: 呼号
    
    Returns:
        True 如果活跃，False 否则
    """
    return get_lotw_active_status([callsign]).get(callsign.upper(), False)


def _refresh_lotw_cache():
    """从数据库刷新 LoTW 缓存"""
    global _lotw_cache, _cache_timestamp
    
    try:
        logger.info('[LoTW] 开始刷新 LoTW 活跃用户列表...')
        
        conn = pymysql.connect(
            host=WAVELOG_DB_HOST,
            port=WAVELOG_DB_PORT,
            user=WAVELOG_DB_USER,
            password=WAVELOG_DB_PASSWORD,
            database=WAVELOG_DB_DATABASE,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT callsign, last_upload FROM lotw_users WHERE callsign IS NOT NULL")
            
            # 构建缓存
            new_cache = {}
            for row in cursor.fetchall():
                callsign = row['callsign']
                if callsign:
                    new_cache[callsign.upper()] = True
            
            _lotw_cache = new_cache
            _cache_timestamp = datetime.now()
            
            cursor.close()
            logger.info(f'[LoTW] 刷新完成，共 {_len(_lotw_cache)} 个活跃用户')
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f'[LoTW] 刷新失败：{e}')
        # 保留旧缓存，避免雪崩


def _len(d: dict) -> int:
    """安全获取字典长度"""
    try:
        return len(d)
    except:
        return 0


def _background_refresh_loop():
    """后台刷新线程主循环"""
    global _running
    
    while _running:
        time.sleep(LOTW_REFRESH_INTERVAL_SECONDS)
        try:
            _refresh_lotw_cache()
        except Exception as e:
            logger.error(f'[LoTW] 后台刷新异常：{e}')


def start_lotw_refresh():
    """
    启动 LoTW 自动刷新后台线程
    
    应在应用启动时调用一次。
    """
    global _refresh_thread, _running
    
    if _refresh_thread is not None and _refresh_thread.is_alive():
        logger.warning('[LoTW] 刷新线程已在运行')
        return
    
    # 首次启动时立即刷新一次
    try:
        _refresh_lotw_cache()
    except Exception as e:
        logger.error(f'[LoTW] 首次刷新失败：{e}')
    
    # 启动后台线程
    _running = True
    _refresh_thread = threading.Thread(
        target=_background_refresh_loop,
        daemon=True,
        name='LoTW-Refresh'
    )
    _refresh_thread.start()
    
    logger.info('[LoTW] 自动刷新线程已启动')


def stop_lotw_refresh():
    """停止 LoTW 自动刷新线程"""
    global _running
    
    _running = False
    if _refresh_thread:
        _refresh_thread.join(timeout=5)
        _refresh_thread = None
    
    logger.info('[LoTW] 自动刷新线程已停止')


def get_lotw_cache_status() -> Dict:
    """
    获取 LoTW 缓存状态（用于监控）
    
    Returns:
        {
            'cache_size': int,
            'cache_timestamp': str (ISO format),
            'is_fresh': bool,
            'thread_running': bool
        }
    """
    now = datetime.now()
    is_fresh = False
    age_hours = None
    
    if _cache_timestamp:
        age_seconds = (now - _cache_timestamp).total_seconds()
        age_hours = age_seconds / 3600
        is_fresh = age_seconds < LOTW_CACHE_TTL_HOURS * 3600
    
    return {
        'cache_size': _len(_lotw_cache),
        'cache_timestamp': _cache_timestamp.isoformat() if _cache_timestamp else None,
        'age_hours': round(age_hours, 2) if age_hours is not None else None,
        'is_fresh': is_fresh,
        'thread_running': _refresh_thread is not None and _refresh_thread.is_alive()
    }
