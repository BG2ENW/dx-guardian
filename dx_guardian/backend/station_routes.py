"""User station configuration routes and storage helpers."""

from pathlib import Path
from datetime import datetime, timezone
import json

from flask import jsonify, request


STATION_FILE = Path(__file__).parent / 'settings' / 'stations.json'

# 加载 Wavelog 配置
WAVELOG_CONFIG_FILE = Path(__file__).parent / 'settings' / 'wavelog_config.json'

def load_wavelog_config():
    """加载 Wavelog 配置"""
    if WAVELOG_CONFIG_FILE.exists():
        with open(WAVELOG_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'enabled': False}

# 尝试导入 Wavelog 适配器
try:
    from wavelog_adapter import get_user_by_callsign, get_user_stations, test_connection as test_wavelog
    WAVELOG_AVAILABLE = True
except ImportError:
    WAVELOG_AVAILABLE = False


def load_station_config(callsign: str = None):
    """加载台站配置，优先从 Wavelog 获取"""
    # 尝试从 Wavelog 获取用户信息
    if WAVELOG_AVAILABLE and callsign:
        try:
            if test_wavelog():
                user = get_user_by_callsign(callsign)
                if user:
                    stations = get_user_stations(user['user_id'])
                    if stations:
                        # 使用第一个活跃电台或默认电台
                        active_station = next(
                            (s for s in stations if s.get('station_active') == 1),
                            stations[0]
                        )
                        wavelog_config = {
                            'callsign': active_station.get('station_callsign', callsign),
                            'grid': active_station.get('station_gridsquare', ''),
                            'city': active_station.get('station_city', ''),
                            'power': active_station.get('station_power', 100),
                            'dxcc': active_station.get('station_dxcc'),
                            'cq': active_station.get('station_cq'),
                            'itu': active_station.get('station_itu'),
                            'station_name': active_station.get('station_profile_name', ''),
                            'source': 'wavelog',
                            'user_id': user['user_id'],
                            'user_name': f"{user.get('user_firstname', '')} {user.get('user_lastname', '')}".strip(),
                            'updated_at': datetime.now(timezone.utc).isoformat(),
                        }
                        # 从 Grid 计算坐标
                        if wavelog_config['grid']:
                            from coordinate_resolver import resolve_coordinates
                            coords = resolve_coordinates(
                                callsign=wavelog_config['callsign'],
                                grid=wavelog_config['grid']
                            )
                            if coords and coords.get('lat'):
                                wavelog_config['lat'] = coords['lat']
                                wavelog_config['lon'] = coords['lon']
                        return wavelog_config
        except Exception as e:
            print(f"[Wavelog] 获取台站信息失败: {e}")
    
    # 回退到本地配置文件
    if not STATION_FILE.exists():
        return {
            'callsign': callsign or 'BG2ENW',
            'grid': 'PN35HS',
            'lat': 45.8,
            'lon': 126.5,
            'power': 100,
            'antenna': '3 Element Yagi',
            'updated_at': None,
            'source': 'local',
        }
    with open(STATION_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
        config['source'] = 'local'
        return config


def save_station_config(config):
    """保存台站配置"""
    config['updated_at'] = datetime.now(timezone.utc).isoformat()
    with open(STATION_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return config


def register_station_routes(app, deps):
    log = deps['log']
    re_module = deps['re_module']
    get_scorer = deps['get_scorer']

    @app.route('/api/user/station', methods=['GET', 'PUT'])
    def api_user_station():
        """获取或更新台站配置"""
        # 从 Wavelog 配置获取默认呼号
        wavelog_cfg = load_wavelog_config()
        default_callsign = wavelog_cfg.get('default_callsign', 'BG2ENW')
        
        if request.method == 'GET':
            return jsonify(load_station_config(default_callsign))

        if request.method == 'PUT':
            try:
                config = request.json
                required = ['callsign', 'grid', 'lat', 'lon']
                for field in required:
                    if field not in config:
                        return jsonify({'error': f'Missing required field: {field}'}), 400

                callsign = config['callsign'].upper().strip()
                if not re_module.match(r'^[A-Z0-9/]{3,10}$', callsign):
                    return jsonify({'error': 'Invalid callsign format'}), 400

                if config['grid']:
                    grid = config['grid'].upper().strip()
                    if not re_module.match(r'^[A-Z]{2}[0-9]{2}[A-Z]{0,2}[0-9]{0,2}$', grid):
                        return jsonify({'error': 'Invalid grid format'}), 400
                    config['grid'] = grid

                config['callsign'] = callsign
                config['lat'] = float(config['lat'])
                config['lon'] = float(config['lon'])
                config['power'] = int(config.get('power', 100))
                config['antenna'] = config.get('antenna', '')

                saved = save_station_config(config)
                log(f'[台站配置更新] {config["callsign"]} / {config["grid"]} / {config["power"]}W')

                scorer = get_scorer()
                if scorer is not None:
                    scorer.update_station(config['lat'], config['lon'], ['FT8', 'CW', 'SSB'])
                return jsonify({'success': True, 'config': saved})
            except Exception as e:
                log(f'[台站配置保存失败] {e}')
                return jsonify({'error': str(e)}), 500

    log('[Route] Station routes registered')
