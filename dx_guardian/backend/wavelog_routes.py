"""Wavelog related HTTP routes."""

from flask import jsonify


def register_wavelog_routes(app, deps):
    log = deps['log']
    external_api_error = deps['external_api_error']
    external_failure_payload = deps['external_failure_payload']
    my_call = deps['my_call']
    wavelog_url = deps['wavelog_url']
    wavelog_api_key = deps['wavelog_api_key']

    @app.route('/api/wavelog_station')
    def api_wavelog_station():
        """从 Wavelog 获取台站配置信息"""
        try:
            import urllib.request
            import json

            url = f'{wavelog_url}/api/station_info/{wavelog_api_key}'
            req = urllib.request.Request(url, method='GET')
            req.add_header('Accept', 'application/json')

            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    if isinstance(data, list):
                        active = next(
                            (
                                s
                                for s in data
                                if s.get('station_active') == '1' or s.get('station_active') == 1
                            ),
                            data[0] if data else None,
                        )
                        if active:
                            return jsonify(
                                {
                                    'callsign': active.get('station_callsign', my_call),
                                    'grid': active.get('station_gridsquare', ''),
                                    'location': active.get('station_city', ''),
                                    'station_profile_name': active.get('station_profile_name', ''),
                                }
                            )
            return jsonify({'callsign': my_call, 'grid': 'PN35HS', 'location': 'Unknown'})
        except Exception as e:
            external_api_error('Wavelog', e)
            return jsonify({'callsign': my_call, 'grid': 'PN35HS', 'location': 'Unknown'})

    @app.route('/api/wavelog_stats')
    def api_wavelog_stats():
        """从 Wavelog 获取 QSO 统计"""
        try:
            import urllib.request
            import json as _json

            url = f'{wavelog_url}/index.php/api/statistics/cl{wavelog_api_key}'
            req = urllib.request.Request(url, method='GET')
            req.add_header('Accept', 'application/json')

            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    data = _json.loads(resp.read().decode('utf-8'))
                    return jsonify({'ok': True, 'data': data})
            return jsonify({'ok': False})
        except Exception as e:
            external_api_error('Wavelog', e)
            return jsonify(external_failure_payload())

    @app.route('/api/wavelog_lookup/<callsign>')
    def api_wavelog_lookup(callsign):
        """查询呼号是否已在 Wavelog 中通联过"""
        try:
            import urllib.request
            import json as _json

            url = f'{wavelog_url}/index.php/api/private_lookup'
            payload = _json.dumps({'key': wavelog_api_key, 'callsign': callsign.upper()}).encode('utf-8')
            req = urllib.request.Request(url, data=payload, method='POST')
            req.add_header('Content-Type', 'application/json')
            req.add_header('Accept', 'application/json')

            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    data = _json.loads(resp.read().decode('utf-8'))
                    return jsonify({'ok': True, 'callsign': callsign.upper(), 'worked': bool(data)})
            return jsonify({'ok': False, 'callsign': callsign.upper(), 'worked': False})
        except Exception as e:
            external_api_error('Wavelog', e)
            return jsonify({'ok': False, 'callsign': callsign.upper(), 'worked': False})

    log('[Route] Wavelog routes registered')
