"""User station configuration routes and storage helpers."""

from pathlib import Path
from datetime import datetime, timezone
import json

from flask import jsonify, request


STATION_FILE = Path(__file__).parent / 'settings' / 'stations.json'


def load_station_config():
    """加载台站配置"""
    if not STATION_FILE.exists():
        return {
            'callsign': 'BG2ENW',
            'grid': 'PN35HS',
            'lat': 45.8,
            'lon': 126.5,
            'power': 100,
            'antenna': '3 Element Yagi',
            'updated_at': None,
        }
    with open(STATION_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


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
        if request.method == 'GET':
            return jsonify(load_station_config())

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
