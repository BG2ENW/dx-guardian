"""
DX Guardian - 真实Cluster版（threading模式）
Flask + SocketIO + Cluster Telnet + Spot解析 + 坐标解析 + 去重
"""
from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO
from pathlib import Path
import sys
import os
import time
import socket as sock_module
import threading
import traceback
from datetime import datetime, timezone

BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / 'frontend'
BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))

from config import (
    CLUSTER_SERVERS, MY_CALL, RECONNECT_DELAYS, MAX_RECONNECT_ATTEMPTS,
    SPOT_CACHE_SIZE, ALL_BANDS, WAVELOG_URL, WAVELOG_API_KEY, SECRET_KEY,
    SOCKETIO_CORS_ALLOWED_ORIGINS, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY_PEM,
    VAPID_EMAIL
)
from spot_parser import SpotParser, SpotDeduplicator, SpotRateLimiter
from coordinate_resolver import resolve_coordinates
from adif_parser import ADIFParser
from dxcc_translator import get_dxcc_cn, translate_dxcc_list
from csv_parser import CSVParser
from alert_engine_v2 import AlertEngineV2, init_alert_engine, get_alert_engine
from wavelog_routes import register_wavelog_routes
from push_routes import register_push_routes
from watchlist_routes import register_watchlist_routes
from station_routes import register_station_routes, load_station_config
from log_routes import register_log_routes
from score_routes import register_score_routes

# ========== 预警引擎（V2增强版）===========
# 旧 AlertEngine 已迁移到 alert_engine_v2.py，使用 AlertEngineV2


# =========== 太阳数据模块 ===========
SOLAR_DATA = {}
SOLAR_LAST_UPDATE = 0
SOLAR_CACHE_TIMEOUT = 300  # 5分钟

def update_solar_data():
    """获取太阳数据（从 hamqsl.com 和 NOAA）"""
    global SOLAR_DATA, SOLAR_LAST_UPDATE
    
    now = time.time()
    if SOLAR_LAST_UPDATE > 0 and (now - SOLAR_LAST_UPDATE) < SOLAR_CACHE_TIMEOUT:
        return SOLAR_DATA
    
    # 默认值
    SOLAR_DATA = {
        'sfi': 0,
        'sn': 0,
        'k': 0,
        'a_index': 0,
        'k_index': 0,
        'updated_at': None
    }
    
    try:
        # 从 HamQSL 获取数据
        import urllib.request
        URL_HAMQSL = 'https://www.hamqsl.com/solarxml.php'
        req = urllib.request.Request(URL_HAMQSL, headers={'User-Agent': 'DXGuardian/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                data = resp.read().decode('utf-8')
                # 简单解析（实际应用建议用 xml.etree）
                import xml.etree.ElementTree as ET
                root = ET.fromstring(data)
                
                solardata = root.find('solardata')
                if solardata is not None:
                    try:
                        sfi_node = solardata.find('sfi')
                        sn_node = solardata.find('sn')
                        a_node = solardata.find('aindex')
                        k_node = solardata.find('kindex')
                        
                        SOLAR_DATA['sfi'] = int(sfi_node.text) if sfi_node is not None and sfi_node.text else 0
                        SOLAR_DATA['sn'] = int(sn_node.text) if sn_node is not None and sn_node.text else 0
                        SOLAR_DATA['a_index'] = int(a_node.text) if a_node is not None and a_node.text else 0
                        SOLAR_DATA['k_index'] = int(k_node.text) if k_node is not None and k_node.text else 0
                        SOLAR_DATA['k'] = SOLAR_DATA['k_index']
                        SOLAR_DATA['updated_at'] = datetime.now(timezone.utc).isoformat()
                        
                        log(f'[太阳数据] SFI={SOLAR_DATA["sfi"]} SN={SOLAR_DATA["sn"]} K={SOLAR_DATA["k"]} A={SOLAR_DATA["a_index"]}')
                    except Exception as e:
                        log(f'[太阳数据解析错误] {e}')
    
    except Exception as e:
        log(f'[太阳数据获取失败] {e}')
    
    SOLAR_LAST_UPDATE = now
    return SOLAR_DATA

# 定时更新太阳数据的线程
solar_thread = None

def solar_update_thread():
    """定期更新太阳数据"""
    global solar_thread
    time.sleep(30)  # 等待启动完成
    log('[太阳数据] 更新服务启动')
    while True:
        try:
            update_solar_data()
            # 推送到前端
            socketio.emit('solar_update', SOLAR_DATA)
        except Exception as e:
            log(f'[太阳数据更新失败] {e}')
        time.sleep(SOLAR_CACHE_TIMEOUT)


# 创建全局预警引擎实例（V2增强版）
alert_engine = init_alert_engine(BACKEND_DIR / 'data')

# 创建评分引擎实例（全局）
scorer = None

def init_scorer():
    """延迟初始化评分器（依赖 load_station_config）"""
    global scorer
    if scorer is None:
        scorer = OpportunityScorer()
        try:
            sc = load_station_config()
            scorer.update_station(
                sc.get('lat', 45.8),
                sc.get('lon', 126.5),
                ['FT8', 'CW', 'SSB']
            )
            log('[评分引擎] 初始化成功')
        except Exception as e:
            log(f'[评分引擎] 初始化失败: {e}')

# ========== Flask ==========
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
socketio = SocketIO(
    app,
    cors_allowed_origins=SOCKETIO_CORS_ALLOWED_ORIGINS,
    async_mode='threading'
)

# ========== 全局状态 ==========
parser = SpotParser()
dedup = SpotDeduplicator(max_size=SPOT_CACHE_SIZE, window_seconds=300)
limiter = SpotRateLimiter(max_per_second=20)
band_counts = {band: 0 for band in ALL_BANDS}
total_spots = 0
cluster_connected = False
lock = threading.Lock()
scorer = None

# 数据源健康状态跟踪
last_psk_success = 0  # PSKReporter最后成功时间
last_cluster_success = 0  # Cluster最后成功时间
cluster_should_run = False  # Cluster是否应该运行（备用模式）

# 后端 Spot 缓存（持续积累，不受前端连接影响）
SPOT_HISTORY_MAX = 10000  # 改为 1 万条缓存
spot_history = []  # 所有处理过的 Spot（含时间戳）

# PSKReporter 配置
PSKREPORTER_URL = 'https://retrieve.pskreporter.info/query'
PSKREPORTER_INTERVAL = 310  # 官方要求不超过5分钟一次，加10秒余量
PSKREPORTER_LIMIT = 100  # 官方默认返回100条，用rptlimit参数

# 数据源优先级配置（PSKReporter为主，Cluster为备用）
PRIMARY_SOURCE = 'pskreporter'  # 主数据源
FALLBACK_SOURCE_ENABLED = True  # 是否启用备用数据源
CLUSTER_FALLBACK_INTERVAL = 600  # 当PSKReporter超时多长时间后启用Cluster备用（秒）

import re as re_module
import json

def log(msg):
    """带flush的日志"""
    print(msg, flush=True)


def _external_api_error(service: str, err: Exception):
    """统一记录外部依赖异常，避免向前端透出内部细节。"""
    log(f'[{service}] 外部调用失败: {type(err).__name__}: {err}')


def _external_failure_payload(message: str = '外部服务暂时不可用') -> dict:
    return {'ok': False, 'error': message}


register_wavelog_routes(
    app,
    {
        'log': log,
        'external_api_error': _external_api_error,
        'external_failure_payload': _external_failure_payload,
        'my_call': MY_CALL,
        'wavelog_url': WAVELOG_URL,
        'wavelog_api_key': WAVELOG_API_KEY,
    },
)

register_push_routes(
    app,
    {
        'log': log,
        'external_api_error': _external_api_error,
        'vapid_public_key': VAPID_PUBLIC_KEY,
        'vapid_private_key_pem': VAPID_PRIVATE_KEY_PEM,
        'vapid_email': VAPID_EMAIL,
    },
)

register_watchlist_routes(
    app,
    {
        'log': log,
    },
)

register_station_routes(
    app,
    {
        'log': log,
        're_module': re_module,
        'get_scorer': lambda: scorer,
    },
)

register_log_routes(
    app,
    {
        'log': log,
        'get_scorer': lambda: scorer,
        'lock': lock,
        'get_spot_history': lambda: spot_history,
        'get_band_counts': lambda: band_counts,
        'get_total_spots': lambda: total_spots,
        'solar_data_getter': lambda: SOLAR_DATA,
        'get_dxcc_cn': get_dxcc_cn,
    },
)

register_score_routes(
    app,
    {
        'log': log,
        'get_scorer': lambda: scorer,
        'init_scorer': init_scorer,
        'lock': lock,
        'get_spot_history': lambda: spot_history,
        'get_band_counts': lambda: band_counts,
        'get_total_spots': lambda: total_spots,
        'get_solar_data': lambda: SOLAR_DATA,
        'get_dxcc_cn': get_dxcc_cn,
        'get_logs_dir': lambda: Path(__file__).parent / 'logs',
    },
)

# ========== 路由 ==========
@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/css/<path:f>')
def css(f):
    return send_from_directory(FRONTEND_DIR / 'css', f)

@app.route('/js/<path:f>')
def js(f):
    return send_from_directory(FRONTEND_DIR / 'js', f)

@app.route('/images/<path:f>')
def images(f):
    return send_from_directory(FRONTEND_DIR / 'images', f)

@app.route('/health')
def health():
    with lock:
        bc = dict(band_counts)
        ts = total_spots
        cc = cluster_connected
    return jsonify({
        'ok': True,
        'cluster_connected': cc,
        'total_spots': ts,
        'band_counts': bc,
        'history_count': len(spot_history)
    })

@app.route('/api/history')
def api_history():
    """返回后端缓存的所有 Spot 历史（前端打开页面时加载）"""
    with lock:
        return jsonify({
            'spots': spot_history.copy(),
            'total': total_spots,
            'band_counts': dict(band_counts)
        })


# =========== 预警 API（V2增强版）===========
@app.route('/api/user/alerts', methods=['GET'])
def api_alerts():
    """获取预警列表，支持筛选"""
    limit = request.args.get('limit', 50, type=int)
    limit = min(limit, 200)
    priority = request.args.get('priority', None)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    alerts = alert_engine.get_alerts(limit=limit, priority=priority, unread_only=unread_only)
    return jsonify({'success': True, 'alerts': alerts})

@app.route('/api/user/alerts/<alert_id>/read', methods=['PUT'])
def api_alert_mark_read(alert_id):
    """标记单个预警为已读"""
    ok = alert_engine.mark_as_read(alert_id)
    return jsonify({'success': ok})

@app.route('/api/user/alerts/read-all', methods=['PUT'])
def api_alert_read_all():
    """标记所有预警为已读"""
    count = alert_engine.mark_all_as_read()
    return jsonify({'success': True, 'marked': count})

@app.route('/api/user/alerts/<alert_id>', methods=['DELETE'])
def api_alert_delete(alert_id):
    """删除单个预警"""
    ok = alert_engine.delete_alert(alert_id)
    return jsonify({'success': ok})

@app.route('/api/user/alerts/clear', methods=['DELETE'])
def api_alert_clear_all():
    """清空所有预警"""
    count = alert_engine.clear_all_alerts()
    return jsonify({'success': True, 'cleared': count})

@app.route('/api/user/alerts/silence', methods=['GET'])
def api_alert_silence_list():
    """获取静默呼号列表"""
    silenced = alert_engine.get_silenced_callsigns()
    return jsonify({'success': True, 'silenced': silenced})

@app.route('/api/user/alerts/silence', methods=['POST'])
def api_alert_silence_add():
    """添加静默呼号"""
    data = request.get_json(force=True, silent=True) or {}
    callsign = (data.get('callsign') or '').strip().upper()
    if not callsign:
        return jsonify({'success': False, 'error': 'callsign required'}), 400
    ok = alert_engine.silence_callsign(callsign)
    return jsonify({'success': ok, 'callsign': callsign})

@app.route('/api/user/alerts/silence/<callsign>', methods=['DELETE'])
def api_alert_silence_remove(callsign):
    """取消静默呼号"""
    ok = alert_engine.unsilence_callsign(callsign)
    return jsonify({'success': ok})

@app.route('/api/user/alerts/stats', methods=['GET'])
def api_alert_stats():
    """获取预警统计"""
    stats = alert_engine.get_stats()
    return jsonify({'success': True, 'stats': stats})

@app.route('/api/stats/solar', methods=['GET'])
def api_solar_data():
    """获取太阳数据"""
    solar = update_solar_data()
    return jsonify({'success': True, 'data': solar})

# ========== WebSocket ==========
@socketio.on('connect')
def on_connect():
    with lock:
        bc = dict(band_counts)
        ts = total_spots
        cc = cluster_connected
    socketio.emit('server_status', {
        'cluster_connected': cc,
        'band_counts': bc,
        'total_spots': ts
    })
    
    # 推送太阳数据
    solar = update_solar_data()
    socketio.emit('solar_update', solar)

# ========== Cluster 连接线程 ==========
def cluster_thread():
    """原生 threading.Thread 运行 Cluster 连接"""
    global cluster_connected, total_spots

    server_index = 0
    reconnect_attempts = 0

    while True:
        s = None
        try:
            server = CLUSTER_SERVERS[server_index]
            log(f'[Cluster] 连接 {server["host"]}:{server["port"]}...')

            s = sock_module.socket(sock_module.AF_INET, sock_module.SOCK_STREAM)
            s.settimeout(10)
            s.connect((server['host'], server['port']))
            log(f'[Cluster] TCP连接成功')

            # 循环读取欢迎信息，直到看到登录提示
            welcome_buf = ''
            while True:
                try:
                    chunk = s.recv(4096).decode('utf-8', errors='ignore')
                    if not chunk:
                        raise Exception('连接关闭')
                    welcome_buf += chunk
                    if 'enter your call' in welcome_buf.lower() or 'login:' in welcome_buf.lower() or 'please enter' in welcome_buf.lower():
                        break
                except sock_module.timeout:
                    log('[Cluster] 等待登录提示超时，尝试发送呼号')
                    break

            # 发送呼号登录
            s.send(f'{MY_CALL}\n'.encode())
            log(f'[Cluster] 已发送呼号: {MY_CALL}')
            time.sleep(2)

            # 读取登录确认
            login_buf = ''
            while True:
                try:
                    chunk = s.recv(4096).decode('utf-8', errors='ignore')
                    if not chunk:
                        raise Exception('连接关闭')
                    login_buf += chunk
                    if '>' in login_buf:
                        break
                except sock_module.timeout:
                    break

            log(f'[Cluster] ✅ 登录成功!')

            with lock:
                cluster_connected = True
            reconnect_attempts = 0
            socketio.emit('server_status', {'cluster_connected': True})
            # 发送命令启用 Spot 推送
            log("[Cluster] 发送配置命令...")
            try:
                s.send(b"SET/USER DXCluster\n")
                s.send(b"SET/DXCOUNT 50\n")
                time.sleep(0.5)
            except Exception as e:
                log(f"[Cluster] 配置命令失败：{e}")


            # 接收循环
            s.settimeout(30)
            buffer = ''
            while True:
                try:
                    data = s.recv(4096).decode('utf-8', errors='ignore')
                    if not data:
                        raise Exception('连接关闭')

                    buffer += data
                    if len(data) > 0:
                        log(f"[Cluster 数据] 收到 {len(data)} 字节")
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        log(f"[Cluster 行] {line[:100]}")
                        if line:
                            try:
                                process_spot(line)
                            except Exception as e:
                                log(f'[Spot处理异常] {e}: {line[:60]}')

                except sock_module.timeout:
                    # 心跳
                    try:
                        s.send(b'\n')
                    except:
                        raise Exception('心跳失败')

        except Exception as e:
            log(f'[Cluster] ❌ 断开: {e}')
            with lock:
                cluster_connected = False
            try:
                socketio.emit('server_status', {'cluster_connected': False})
            except:
                pass

            if s:
                try:
                    s.close()
                except:
                    pass

            delay_idx = min(reconnect_attempts, len(RECONNECT_DELAYS) - 1)
            delay = RECONNECT_DELAYS[delay_idx]
            log(f'[Cluster] {delay}s 后重连 ({reconnect_attempts + 1}/{MAX_RECONNECT_ATTEMPTS})')
            time.sleep(delay)

            reconnect_attempts += 1
            if reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
                reconnect_attempts = 0
                server_index = (server_index + 1) % len(CLUSTER_SERVERS)
                log(f'[Cluster] 切换到服务器 {CLUSTER_SERVERS[server_index]["host"]}')


def add_to_history(spot):
    """添加 Spot 到后端缓存（线程安全，自动清理24小时外的数据）"""
    with lock:
        log(f"[历史缓存]存入 spot: {spot['callsign']} {spot['freq']} {spot['mode']}")
        spot['_server_ts'] = time.time()
        spot_history.append(spot)
        
        # 清理逻辑：数量限制 + 24小时时间限制
        now = time.time()
        
        # 先删除超过24小时的数据
        while spot_history and now - spot_history[0].get('_server_ts', 0) > 86400:
            spot_history.pop(0)
        
        # 再检查数量限制
        while len(spot_history) > SPOT_HISTORY_MAX:
            spot_history.pop(0)


def process_spot(line):
    """处理一行Cluster数据"""
    global total_spots

    spot = parser.parse(line)
    if len(line) > 5:
        print(f"[process_spot] {line[:80]}", flush=True)
    if not spot:
        return

    if not limiter.allow():
        return

    if dedup.is_duplicate(spot):
        return

    # 坐标解析（安全包裹）
    try:
        coords = resolve_coordinates(spot['callsign'], spot.get('grid'))
        spot['lat'] = coords.get('lat', 0)
        spot['lon'] = coords.get('lon', 0)
        spot['precision'] = coords.get('precision', 'dxcc')
        spot['dxcc'] = coords.get('dxcc', '')
    except Exception as e:
        log(f"[坐标解析异常] {spot['callsign']}: {e}")
        spot['lat'] = 0
        spot['lon'] = 0
        spot['precision'] = 'dxcc'
        spot['dxcc'] = ''
    # 跳过无坐标的 (已禁用)
    # if spot["lat"] == 0 and spot["lon"] == 0:
    #     return
    # if spot['lat'] == 0 and spot['lon'] == 0:
    # 更新统计
    with lock:
        total_spots += 1
        band = spot.get('band')
        if band in band_counts:
            band_counts[band] += 1
        ts = total_spots
        bc = dict(band_counts)

    # 存入后端缓存
    add_to_history(spot)

    # ============ 预警检查 ============
    watchlist = load_watchlist()
    alerts = alert_engine.check_spot(spot, watchlist)
    if alerts:
        for alert in alerts:
            try:
                socketio.emit('alert:new', alert)
                log(f'[预警] {alert["message"]}')
                # Web Push 推送
                try:
                    send_push_notification('🔔 DX Guardian', alert.get('message', ''), 'alert-' + alert.get('type', 'spot'))
                except Exception:
                    pass
            except Exception as e:
                log(f'[预警推送失败] {e}')

    # 计算机会评分
    score_result = None
    try:
        if scorer is None:
            init_scorer()
        if scorer is not None:
            # 计算该 DXCC 当前 Spot 数量
            dxcc = spot.get('dxcc', '')
            dxcc_count = len([s for s in spot_history[-200:] if s.get('dxcc') == dxcc]) if dxcc else 0
            score_result = scorer.score(spot, bc, ts, SOLAR_DATA, dxcc_count)
            spot['score'] = score_result['total']
            spot['score_total'] = score_result['total']
            spot['score_factors'] = score_result['factors']
            spot['recommendation'] = score_result['recommendation']
    except Exception as e:
        log(f'[评分异常] {e}')

    # 广播
    try:
        socketio.emit('new_spot', spot)
        socketio.emit('band_update', {
            'band': band,
            'total': ts,
            'band_counts': bc
        })
        # 如果是高分 spot，额外推送推荐事件
        if score_result and score_result['total'] >= 70:
            try:
                socketio.emit('score:opportunity', {
                    'spot': spot,
                    'score': score_result
                })
            except Exception:
                pass
    except Exception as e:
        pass

    log("[Spot] {} {} {} {} lat:{} lon:{} {}".format(spot["callsign"], spot["freq"], spot["band"], spot["mode"], spot["lat"], spot["lon"], spot.get("dxcc","")))


# ========== PSKReporter 数据源 ==========
def pskreporter_thread():
    """定时从 PSKReporter 获取全球接收报告（不限定呼号）
    
    官方API规则：
    - 查询间隔不少于5分钟
    - 不带senderCallsign时返回全球最近接收报告
    - 参数用rptlimit不是limit
    - 建议加appcontact参数方便管理员联系
    - flowStartSeconds不能超过-86400(24小时)
    """
    import urllib.request
    import urllib.error
    import xml.etree.ElementTree as ET

    time.sleep(15)  # 等待启动完成
    log('[PSKReporter] 全球数据源启动（5分钟间隔，遵守官方限制）')

    while True:
        try:
            # 全球查询：不带senderCallsign，获取所有接收报告
            # flowStartSeconds=-300: 最近5分钟的数据
            # noactive=1: 不返回活跃监听台列表（减少数据量）
            # ronly=1: 只返回接收报告
            # rptlimit=100: 官方默认100条
            # appcontact: 官方建议添加，方便管理员联系
            url = (f'{PSKREPORTER_URL}?flowStartSeconds=-300'
                   f'&noactive=1&rronly=1&rptlimit={PSKREPORTER_LIMIT}'
                   f'&appcontact=bg2enw@163.com')
            req = urllib.request.Request(url, headers={'User-Agent': 'DXGuardian/1.0 (BG2ENW)'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read().decode('utf-8', errors='ignore')

            root = ET.fromstring(data)
            count = 0
            last_seq = root.get('lastSeqNo', '')

            for recv in root.findall('.//receptionReport'):
                try:
                    # PSKReporter的receptionReport中：
                    # - 发送台（被接收到的台）= senderCallsign
                    # - 接收台（收到信号的台）= receiverCallsign / callsign
                    # 地图上应显示发送台的位置（被spot的台）
                    sender_callsign = recv.get('senderCallsign', '').strip().upper()
                    receiver_callsign = recv.get('callsign', '').strip().upper()  # XML中callsign是接收台
                    
                    # 地图标记用发送台呼号（被spot的台）
                    callsign = sender_callsign if sender_callsign else receiver_callsign
                    if not callsign:
                        continue

                    freq_hz = int(recv.get('frequency', '0'))
                    if freq_hz == 0:
                        continue
                    freq_mhz = freq_hz / 1e6

                    mode = recv.get('mode', 'FT8')
                    # 发送台的Grid locator
                    grid = recv.get('senderLocator', '') or recv.get('locator', '')
                    snr = recv.get('sNR', '')
                    
                    # 时间信息
                    flow_start = recv.get('flowStartSeconds', '')
                    
                    # 接收台信息
                    receiver_grid = recv.get('receiverLocator', '')
                    
                    # 设备和天线信息
                    decoder_software = recv.get('decoderSoftware', '')
                    antenna_info = recv.get('antennaInformation', '')
                    rig_info = recv.get('rigInformation', '')
                    
                    # 格式化时间
                    display_time = ''
                    if flow_start:
                        try:
                            dt = time.gmtime(int(flow_start))
                            display_time = time.strftime('%H:%M:%S UTC', dt)
                        except:
                            display_time = flow_start

                    # 频率转波段
                    band = freq_to_band(freq_mhz)
                    if not band:
                        continue

                    # 构建 Spot 数据
                    spot = {
                        'callsign': callsign,
                        'freq': freq_mhz,
                        'band': band,
                        'mode': mode,
                        'grid': grid,
                        'snr': snr,
                        'source': 'pskreporter',
                        'time': display_time,
                        'timestamp': flow_start,
                        # 接收台信息
                        'receiver': receiver_callsign,
                        'receiver_grid': receiver_grid,
                        # 设备信息
                        'decoder_software': decoder_software,
                        'antenna_info': antenna_info,
                        'rig_info': rig_info,
                    }

                    # 去重
                    if dedup.is_duplicate(spot):
                        continue

                    # 坐标解析
                    coords = resolve_coordinates(callsign, grid)
                    spot['lat'] = coords.get('lat', 0)
                    spot['lon'] = coords.get('lon', 0)
                    spot['precision'] = coords.get('precision', 'dxcc')
                    spot['dxcc'] = coords.get('dxcc', '')

                    if spot['lat'] == 0 and spot['lon'] == 0:
                        continue

                    # 更新统计
                    with lock:
                        total_spots += 1
                        if band in band_counts:
                            band_counts[band] += 1

                    add_to_history(spot)

                    # 计算机会评分
                    try:
                        if scorer is None:
                            init_scorer()
                        if scorer is not None:
                            with lock:
                                bc = dict(band_counts)
                                ts = total_spots
                            dxcc = spot.get('dxcc', '')
                            dxcc_count = len([s for s in spot_history[-200:] if s.get('dxcc') == dxcc]) if dxcc else 0
                            score_result = scorer.score(spot, bc, ts, SOLAR_DATA, dxcc_count)
                            spot['score'] = score_result['total']
                            spot['score_total'] = score_result['total']
                            spot['score_factors'] = score_result['factors']
                            spot['recommendation'] = score_result['recommendation']
                    except Exception:
                        pass

                    # ============ 预警检查 ============
                    try:
                        psk_watchlist = load_watchlist()
                        alerts = alert_engine.check_spot(spot, psk_watchlist)
                        if alerts:
                            for alert in alerts:
                                try:
                                    socketio.emit('alert:new', alert)
                                    log(f'[预警] {alert["message"]}')
                                    # Web Push 推送
                                    try:
                                        send_push_notification('🔔 DX Guardian', alert.get('message', ''), 'alert-' + alert.get('type', 'spot'))
                                    except Exception:
                                        pass
                                except Exception as e:
                                    log(f'[预警推送失败] {e}')
                    except Exception as e:
                        log(f'[预警检查异常] {e}')

                    try:
                        socketio.emit('new_spot', spot)
                    except:
                        pass

                    count += 1

                except Exception as e:
                    continue

            if count > 0:
                last_psk_success = time.time()
                log(f'[PSKReporter] ✅ {count} 条全球接收报告')

        except urllib.error.HTTPError as e:
            if e.code == 429:
                log(f'[PSKReporter] ⏳ 被限流，等待10分钟后重试')
                time.sleep(600)
            else:
                log(f'[PSKReporter] ❌ 查询失败 {e.code}: {e}')
                time.sleep(60)
        except Exception as e:
            log(f'[PSKReporter] ❌ 查询失败: {e}')
            time.sleep(60)

        # 遵守官方5分钟间隔限制
        time.sleep(PSKREPORTER_INTERVAL)


def freq_to_band(freq_mhz):
    """频率(MHz)转波段"""
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



# =========== 趋势预测 API ===========
@app.route('/api/trends', methods=['GET'])
def api_trends():
    """获取波段趋势分析"""
    try:
        from trend_analyzer import TrendAnalyzer
        analyzer = TrendAnalyzer()
        result = analyzer.analyze(spot_history)
        return jsonify({'success': True, 'trends': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =========== 传播预测 API ===========
@app.route('/api/propagation', methods=['GET'])
def api_propagation():
    """获取 HF 传播预测"""
    try:
        from propagation import PropagationPredictor
        predictor = PropagationPredictor()
        band = request.args.get('band')
        if band:
            result = predictor.get_band_condition(band)
            return jsonify({'success': True, 'band': band, 'condition': result})
        else:
            result = predictor.get_all_band_summary()
            return jsonify({'success': True, 'propagation': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/propagation/solar', methods=['GET'])
def api_propagation_solar():
    """获取完整太阳数据（含传播预测）"""
    try:
        import urllib.request
        import xml.etree.ElementTree as ET
        url = 'https://www.hamqsl.com/solarxml.php'
        xml_data = urllib.request.urlopen(url, timeout=10).read().decode('utf-8')
        root = ET.fromstring(xml_data)
        solardata = root.find('.//solardata')
        
        result = {}
        for child in solardata:
            result[child.tag] = child.text.strip() if child.text else ''
        
        return jsonify({'success': True, 'solar': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =========== 灰线 API ===========
@app.route('/api/terminator', methods=['GET'])
def api_terminator():
    """获取灰线（昼夜分界线）数据"""
    try:
        from terminator import TerminatorCalculator
        calc = TerminatorCalculator()
        geojson = calc.get_terminator_geojson()
        return jsonify({'success': True, 'terminator': geojson})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =========== VOACAP 传播预测 API ===========
@app.route('/api/voacap/predict', methods=['GET'])
def api_voacap_predict():
    """VOACAP 风格传播预测"""
    try:
        from voacap_predictor import VOACAPPredictor

        # 获取参数
        from_lat = float(request.args.get('from_lat', 39.9))
        from_lon = float(request.args.get('from_lon', 116.4))
        to_lat = float(request.args.get('to_lat', 40.7))
        to_lon = float(request.args.get('to_lon', -74.0))
        sfi = float(request.args.get('sfi', SOLAR_DATA.get('sfi', 100)))
        k_index = float(request.args.get('k_index', SOLAR_DATA.get('k', 2)))

        predictor = VOACAPPredictor()
        result = predictor.predict_propagation(
            from_lat=from_lat, from_lon=from_lon,
            to_lat=to_lat, to_lon=to_lon,
            sfi=sfi, k_index=k_index
        )

        return jsonify({'success': True, 'prediction': result})
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/api/voacap/best-bands', methods=['GET'])
def api_voacap_best_bands():
    """获取当前最佳波段（基于我的台站位置）"""
    try:
        from voacap_predictor import VOACAPPredictor

        # 使用我的台站位置
        station_cfg = load_station_config()
        my_lat = station_cfg.get('lat', 45.8)
        my_lon = station_cfg.get('lon', 126.5)

        # 目标：全球主要 DXCC 区域中心
        targets = [
            {'name': '欧洲', 'lat': 50.0, 'lon': 10.0, 'dxcc': 'Europe'},
            {'name': '北美东岸', 'lat': 40.0, 'lon': -75.0, 'dxcc': 'USA'},
            {'name': '北美西岸', 'lat': 37.0, 'lon': -122.0, 'dxcc': 'USA'},
            {'name': '南美', 'lat': -23.0, 'lon': -46.0, 'dxcc': 'Brazil'},
            {'name': '非洲', 'lat': -1.0, 'lon': 37.0, 'dxcc': 'Kenya'},
            {'name': '东南亚', 'lat': 1.0, 'lon': 104.0, 'dxcc': 'Singapore'},
            {'name': '澳洲', 'lat': -33.0, 'lon': 151.0, 'dxcc': 'Australia'},
            {'name': '日本', 'lat': 35.0, 'lon': 139.0, 'dxcc': 'Japan'},
        ]

        sfi = SOLAR_DATA.get('sfi', 100)
        k_index = SOLAR_DATA.get('k', 2)

        predictor = VOACAPPredictor()

        # 计算到每个目标的最佳波段
        results = []
        for target in targets:
            pred = predictor.predict_propagation(
                from_lat=my_lat, from_lon=my_lon,
                to_lat=target['lat'], to_lon=target['lon'],
                sfi=sfi, k_index=k_index
            )

            results.append({
                'target': target['name'],
                'dxcc': target['dxcc'],
                'distance_km': pred['distance_km'],
                'best_bands': pred['best_bands'][:2],
                'grayline': pred['grayline_path']
            })

        # 汇总各波段出现次数
        band_counts = {}
        for r in results:
            for b in r['best_bands']:
                band = b['band']
                band_counts[band] = band_counts.get(band, 0) + b['score']

        top_bands = sorted(band_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return jsonify({
            'success': True,
            'my_station': {'lat': my_lat, 'lon': my_lon},
            'solar': {'sfi': sfi, 'k_index': k_index},
            'targets': results,
            'recommended_bands': [{'band': b, 'total_score': s} for b, s in top_bands]
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

# =========== 波段开放预测 API ===========
@app.route('/api/band-opening', methods=['GET'])
def api_band_opening():
    """未来24小时波段开放预测"""
    try:
        from band_opening import BandOpeningPredictor
        predictor = BandOpeningPredictor()
        station_cfg = load_station_config()
        forecast = predictor.predict_24h(
            sfi=SOLAR_DATA.get('sfi', 100),
            k_index=SOLAR_DATA.get('k', 2),
            lat=station_cfg.get('lat', 45.8)
        )
        return jsonify({'success': True, 'forecast': forecast})
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

if __name__ == '__main__':
    log(f'Frontend: {FRONTEND_DIR}')
    log(f'Cluster: {[s["host"] for s in CLUSTER_SERVERS]}')
    log(f'PSKReporter: {PSKREPORTER_URL}')

    # Cluster 连接线程
    t = threading.Thread(target=cluster_thread, daemon=True)
    t.start()

    # PSKReporter 数据源线程
    t2 = threading.Thread(target=pskreporter_thread, daemon=True)
    t2.start()

    # 太阳数据更新线程
    t3 = threading.Thread(target=solar_update_thread, daemon=True)
    t3.start()

    log('\n🚀 DX Guardian 启动!')
    log(f'   http://0.0.0.0:5000')
    log(f'   数据源: DX Cluster + PSKReporter')
    log(f'   后端缓存: {SPOT_HISTORY_MAX} 条')

    # 初始化评分引擎
    pass  # scorer 暂缓

    # 启动 Flask-SocketIO 服务器
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
