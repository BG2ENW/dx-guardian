"""Opportunity scoring API routes."""

import json
from pathlib import Path

from flask import jsonify, request


def register_score_routes(app, deps):
    log = deps['log']
    get_scorer = deps['get_scorer']
    init_scorer = deps.get('init_scorer', lambda: None)
    lock = deps['lock']
    get_spot_history = deps['get_spot_history']
    get_band_counts = deps['get_band_counts']
    get_total_spots = deps['get_total_spots']
    get_solar_data = deps['get_solar_data']
    get_dxcc_cn = deps['get_dxcc_cn']
    get_logs_dir = deps.get('get_logs_dir', lambda: Path(__file__).parent / 'logs')

    @app.route('/api/score/spot', methods=['POST'])
    def api_score_spot():
        """为单个 Spot 计算机会评分"""
        try:
            scorer = get_scorer()
            if scorer is None:
                init_scorer()
                scorer = get_scorer()

            spot_data = request.get_json(silent=True) or {}
            # 兼容两种入参：
            # 1) {"spot": {...}, "band_counts": ..., ...}
            # 2) 扁平 spot 字段直接放在请求体根级
            spot = spot_data.get('spot')
            if not isinstance(spot, dict):
                spot = {
                    'callsign': spot_data.get('callsign'),
                    'band': spot_data.get('band'),
                    'mode': spot_data.get('mode'),
                    'snr': spot_data.get('snr'),
                    'distance_km': spot_data.get('distance_km'),
                    'frequency': spot_data.get('frequency'),
                    'freq': spot_data.get('freq', spot_data.get('frequency')),
                    'timestamp': spot_data.get('timestamp'),
                    'lat': spot_data.get('lat', 0),
                    'lon': spot_data.get('lon', 0),
                    'dxcc': spot_data.get('dxcc', ''),
                }

            if not spot.get('callsign'):
                return jsonify({'error': 'invalid spot payload: callsign required'}), 400

            band_counts = spot_data.get('band_counts', {})
            total_spots = spot_data.get('total_spots', 0)
            solar_data = spot_data.get('solar_data', {})

            score_result = scorer.score(
                spot, band_counts, total_spots, solar_data,
                spot_data.get('dxcc_count', 0)
            )

            return jsonify({'success': True, 'score': score_result})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/score/missing', methods=['GET'])
    def api_score_missing_dxcc():
        """为所有缺失的 DXCC 计算机会评分（基于当前位置实时 Spot）"""
        try:
            logs_dir = get_logs_dir()
            logs_file = logs_dir / 'logs.json'
            try:
                with open(logs_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except Exception:
                return jsonify({'error': '未找到日志数据'}), 404

            missing_dxcc = set()
            for log_entry in logs:
                stats = log_entry.get('dxcc_stats', {})
                missing_list = stats.get('missing_dxcc_list', [])
                missing_dxcc.update(missing_list)

            if not missing_dxcc:
                return jsonify({'success': True, 'scores': []})

            with lock:
                bc = dict(get_band_counts())
                ts = get_total_spots()

            solar = get_solar_data()

            from dxcc_stats import DXCCStats

            results = []
            for dxcc in sorted(missing_dxcc)[:20]:
                spot_history = get_spot_history()
                recent_spots = [s for s in spot_history[-500:] if s.get('dxcc') == dxcc]

                if recent_spots:
                    spot = recent_spots[-1]
                    dxcc_count = len(recent_spots)
                    scorer = get_scorer()
                    if scorer is None:
                        continue
                    score_result = scorer.score(spot, bc, ts, solar, dxcc_count)
                    results.append({
                        'dxcc': dxcc,
                        'dxcc_cn': get_dxcc_cn(dxcc),
                        'score': score_result,
                        'recommendation_score': score_result['total'],
                        'spot': spot,
                    })

            results.sort(key=lambda x: x['score']['total'], reverse=True)
            return jsonify({'success': True, 'scores': results})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/score/top', methods=['GET'])
    def api_score_top():
        """获取当前实时评分最高的 Spot 推荐列表"""
        try:
            scorer = get_scorer()
            if scorer is None:
                init_scorer()
                scorer = get_scorer()

            limit = request.args.get('limit', 15, type=int)
            min_score = request.args.get('min_score', 50, type=int)

            with lock:
                bc = dict(get_band_counts())
                ts = get_total_spots()

            solar = get_solar_data() or {}
            spot_history = get_spot_history()

            results = []
            seen_callsigns = set()

            for spot in reversed(spot_history[-300:]):
                callsign = spot.get('callsign', '')
                if not callsign or callsign in seen_callsigns:
                    continue

                if spot.get('lat', 0) == 0 and spot.get('lon', 0) == 0:
                    continue

                dxcc = spot.get('dxcc', '')
                dxcc_count = (
                    len([s for s in spot_history[-200:] if s.get('dxcc') == dxcc])
                    if dxcc
                    else 0
                )

                try:
                    score_result = scorer.score(spot, bc, ts, solar, dxcc_count)
                except Exception:
                    continue

                if score_result['total'] >= min_score:
                    results.append(
                        {
                            'callsign': callsign,
                            'dxcc': spot.get('dxcc', ''),
                            'dxcc_cn': get_dxcc_cn(spot.get('dxcc', '')),
                            'band': spot.get('band', ''),
                            'mode': spot.get('mode', ''),
                            'freq': spot.get('freq', 0),
                            'lat': spot.get('lat', 0),
                            'lon': spot.get('lon', 0),
                            'grid': spot.get('grid', ''),
                            'score': score_result['total'],
                            'recommendation': score_result['recommendation'],
                            'factors': score_result['factors'],
                            'time': spot.get('time', ''),
                        }
                    )
                    seen_callsigns.add(callsign)

                if len(results) >= limit:
                    break

            results.sort(key=lambda x: x['score'], reverse=True)
            return jsonify({'success': True, 'top': results})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    log('[Route] Score routes registered')
