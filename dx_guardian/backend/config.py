"""
DX Guardian 配置文件
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent


def _is_production() -> bool:
    flask_env = os.environ.get('FLASK_ENV', '').strip().lower()
    app_env = os.environ.get('APP_ENV', '').strip().lower()
    return flask_env == 'production' or app_env == 'production'


def _get_env(
    key: str,
    default: str = '',
    required_in_production: bool = False,
) -> str:
    value = os.environ.get(key, default)
    if required_in_production and _is_production() and not value:
        raise RuntimeError(f'Missing required environment variable: {key}')
    return value

# Flask 配置
SECRET_KEY = _get_env(
    'SECRET_KEY',
    'dx-guardian-dev-secret-key',
    required_in_production=True,
)
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
SOCKETIO_CORS_ALLOWED_ORIGINS = _get_env('SOCKETIO_CORS_ALLOWED_ORIGINS', '*')

# Cluster Telnet 配置
CLUSTER_SERVERS = [
    {'host': 'bh3bbj.rfsec.cn', 'port': 7373},   # BH3BBJ AR-Cluster (天津，亚洲最近)
    {'host': 'dxc.n4zkf.com', 'port': 7373},     # N4ZKF DXCluster (美国，数据量大)
    {'host': 'k1ttt.net', 'port': 7373},          # K1TTT AR-Cluster (美国)
    {'host': 'w3lpl.net', 'port': 7373},          # W3LPL AR-Cluster (美国)
    {'host': 'dxc.kf7h.net', 'port': 7300},       # KF7H DXCluster (美国)
    {'host': 'dxcc.g7vjr.org', 'port': 23},       # G7VJR DXCluster (英国)
    {'host': 'dxc.ve3te.net', 'port': 7300},      # VE3TE DXCluster (加拿大)
    {'host': 'cluster.dxheat.com', 'port': 7000}, # DXHeat Cluster (欧洲)
]
MY_CALL = 'BG2ENW'  # 登录 Cluster 使用的呼号

# 数据缓存配置
SPOT_CACHE_SIZE = 10000  # Spot 缓存最大数量（FIFO，增加至 1 万条）
SPOT_DEDUPE_WINDOW = 300  # Spot 去重时间窗口（秒）

# 重连策略
RECONNECT_DELAYS = [5, 15, 30, 60]  # 重连退避时间（秒）
MAX_RECONNECT_ATTEMPTS = 5  # 最大重连尝试次数

# 心跳检测
HEARTBEAT_INTERVAL = 60  # 心跳间隔（秒）
HEARTBEAT_TIMEOUT = 120  # 心跳超时（秒）

# 太阳数据缓存
SOLAR_DATA_CACHE_TTL = 300  # 太阳数据缓存时间（秒）
NOAA_DATA_CACHE_TTL = 3600  # NOAA 数据缓存时间（秒）

# 数据文件路径
DXCC_PREFIX_FILE = BASE_DIR / 'data' / 'prefix_to_dxcc.json'

# Wavelog 集成配置
WAVELOG_URL = _get_env('WAVELOG_URL', '', required_in_production=True)
WAVELOG_API_KEY = _get_env('WAVELOG_API_KEY', '', required_in_production=True)

# ClubLog Application Password（用于 callbook 查询）
# 获取方式：登录 ClubLog -> Settings -> App Passwords
CLUBLOG_APP_PASSWORD = _get_env('CLUBLOG_APP_PASSWORD', '', required_in_production=True)

# QRZ.com XML API 配置（用于呼号 Grid 查询）
QRZ_USERNAME = _get_env('QRZ_USERNAME', '', required_in_production=True)
QRZ_PASSWORD = _get_env('QRZ_PASSWORD', '', required_in_production=True)

# HamQTH API 配置（备用呼号 Grid 查询）
HAMQTH_USERNAME = _get_env('HAMQTH_USERNAME', '', required_in_production=True)
HAMQTH_PASSWORD = _get_env('HAMQTH_PASSWORD', '', required_in_production=True)

# Web Push (VAPID)
VAPID_PUBLIC_KEY = _get_env('VAPID_PUBLIC_KEY', '', required_in_production=True)
VAPID_PRIVATE_KEY_PEM = _get_env('VAPID_PRIVATE_KEY_PEM', '', required_in_production=True)
VAPID_EMAIL = _get_env('VAPID_EMAIL', '', required_in_production=True)

# 波段列表（用于统计和过滤）
ALL_BANDS = ['160m', '80m', '60m', '40m', '30m', '20m', '17m', '15m', '12m', '10m', '6m', '2m', '70cm', '23cm']

# 模式列表（用于统计和过滤）
ALL_MODES = ['CW', 'SSB', 'FT8', 'FT4', 'RTTY', 'PSK31', 'AM', 'FM']

# 颜色映射（地图标记）
MODE_COLORS = {
    'CW': '#FF5733',      # 红色
    'SSB': '#2196F3',     # 蓝色
    'FT8': '#4CAF50',     # 绿色
    'FT4': '#8BC34A',     # 浅绿
    'RTTY': '#FF9800',    # 橙色
    'PSK31': '#9C27B0',   # 紫色
    'AM': '#795548',      # 棕色
    'FM': '#607D8B',      # 灰蓝
    'UNKNOWN': '#999999'  # 灰色
}

# 坐标精度标记
COORDINATE_PRECISION_GRID = 'grid'       # Grid 方格精确
COORDINATE_PRECISION_CALLSIGN = 'callsign'  # 呼号查询
COORDINATE_PRECISION_DXCC = 'dxcc'       # DXCC 区域中心

# 用户默认配置
DEFAULT_USER_CONFIG = {
    'callsign': 'BG2ENW',
    'grid': 'PN35HS',
    'lat': 45.8,
    'lon': 126.5,
    'power': 100,
    'antenna_type': 'GP',
    'antenna_height': 10,
    'antenna_gain': 0,
}
# ===== Cluster 去重配置 =====
# 去重时间窗口 (秒) - 同一呼号 + 频率 + 模式在此窗口内视为重复
DEDUP_WINDOW_SECONDS = int(os.getenv('DEDUP_WINDOW_SECONDS', '300'))

# 去重缓存最大大小
DEDUP_MAX_SIZE = int(os.getenv('DEDUP_MAX_SIZE', '10000'))

# ===== Wavelog OnlineLog 配置 =====
# Wavelog 实例 URL (如 https://log.example.com)
WAVELOG_URL = os.getenv('WAVELOG_URL', 'https://cqcqcq.com.cn/')

# Wavelog API 密钥 (在 Wavelog 设置中生成)
WAVELOG_API_KEY = os.getenv('WAVELOG_API_KEY', '***REMOVED***')

# 站台呼号 (可选，用于多站台站点)
WAVELOG_STATION_CALLSIGN = os.getenv('WAVELOG_STATION_CALLSIGN', '')

# 日志分析配置
LOG_ANALYSIS_MAX_DAYS = int(os.getenv('LOG_ANALYSIS_MAX_DAYS', '365'))  # 默认分析最近 365 天
LOG_ANALYSIS_CACHE_TTL = int(os.getenv('LOG_ANALYSIS_CACHE_TTL', '300'))  # 缓存 5 分钟
