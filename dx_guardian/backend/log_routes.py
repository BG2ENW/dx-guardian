"""Log upload, parsing, and validation routes."""

from pathlib import Path
import json
import time
from datetime import datetime, timezone
import sys

from flask import jsonify, request


LOGS_DIR = Path(__file__).parent / 'logs'


def register_log_routes(app, deps):
    log = deps['log']
    get_scorer = deps['get_scorer']
    lock = deps['lock']
    get_spot_history = deps['get_spot_history']
    get_band_counts = deps['get_band_counts']
    get_total_spots = deps['get_total_spots']
    solar_data_getter = deps['solar_data_getter']
    get_dxcc_cn = deps['get_dxcc_cn']

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    backend_dir = Path(__file__).parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    @app.route('/api/user/logs/upload', methods=['POST'])
    def api_upload_log():
        """上传日志文件（支持 ADIF / CSV）"""
        from adif_parser import ADIFParser
        from csv_parser import CSVParser
        from dxcc_stats import DXCCStats

        if 'file' not in request.files:
            return jsonify({'error': '请选择文件'}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({'error': '文件名为空'}), 400

        filename = file.filename.lower()
        if filename.endswith('.adif'):
            parser = ADIFParser()
        elif filename.endswith('.csv'):
            parser = CSVParser()
        else:
            return jsonify({'error': '不支持的文件格式，请上传 .adif 或 .csv 文件'}), 400

        file_path = LOGS_DIR / filename
        file.save(str(file_path))
        log(f'[日志上传] {filename}')

        try:
            records, errors = parser.parse_file(str(file_path))
        except Exception as e:
            return jsonify({'error': f'解析失败：{str(e)}'}), 500

        dxcc_stats = DXCCStats()
        stats_result = dxcc_stats.analyze_records(records)

        log_record = {
            'id': str(int(time.time() * 1000)),
            'filename': filename,
            'uploaded_at': datetime.now(timezone.utc).isoformat(),
            'record_count': len(records),
            'error_count': len(errors),
            'dxcc_stats': stats_result,
            'errors': errors[:10],
        }

        logs_file = LOGS_DIR / 'logs.json'
        try:
            with open(logs_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except Exception:
            logs = []

        logs.append(log_record)
        if len(logs) > 50:
            logs = logs[-50:]

        with open(logs_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

        log(f'[日志上传] 解析完成：{len(records)} 条记录，{stats_result["worked_dxcc_count"]} 个 DXCC')

        return jsonify({
            'success': True,
            'log_id': log_record['id'],
            'stats': stats_result,
            'errors': errors[:10],
        })

    @app.route('/api/user/logs', methods=['GET'])
    def api_user_logs():
        """获取用户日志列表"""
        logs_file = LOGS_DIR / 'logs.json'
        try:
            with open(logs_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except Exception:
            logs = []

        logs.sort(key=lambda x: x.get('uploaded_at', ''), reverse=True)
        return jsonify({'success': True, 'logs': logs})

    @app.route('/api/user/logs/<log_id>', methods=['DELETE'])
    def api_delete_log(log_id):
        """删除日志记录"""
        logs_file = LOGS_DIR / 'logs.json'
        try:
            with open(logs_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except Exception:
            return jsonify({'error': '日志文件不存在'}), 404

        logs = [lg for lg in logs if lg.get('id') != log_id]
        with open(logs_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

        log(f'[日志删除] {log_id}')
        return jsonify({'success': True})

    @app.route('/api/score/validate', methods=['GET'])
    def api_score_validate():
        """验证历史评分准确性：对比已上传日志和评分历史"""
        from score_validator import ScoreValidator

        validator = ScoreValidator(LOGS_DIR)
        worked_callsigns = validator.get_all_worked_callsigns()
        worked_dxcc = validator.get_worked_dxcc()

        if not worked_callsigns:
            return jsonify({
                'success': True,
                'message': '尚未上传日志，无法验证',
                'validation': None,
            })

        scored_spots = []
        spot_history = get_spot_history()
        for spot in spot_history[-500:]:
            callsign = spot.get('callsign', '').upper()
            score = spot.get('score_total', spot.get('score', 0))
            if callsign and score > 0:
                scored_spots.append({
                    'callsign': callsign,
                    'dxcc': spot.get('dxcc', ''),
                    'dxcc_cn': get_dxcc_cn(spot.get('dxcc', '')),
                    'band': spot.get('band', ''),
                    'score': score,
                })

        if not scored_spots:
            return jsonify({
                'success': True,
                'message': '尚无评分数据',
                'validation': None,
                'worked_dxcc_count': len(worked_dxcc),
            })

        result = validator.validate_prediction(scored_spots, worked_callsigns)
        result['worked_callsigns_count'] = len(worked_callsigns)
        result['worked_dxcc_count'] = len(worked_dxcc)

        for bucket, data in result['score_distribution'].items():
            t = data['total']
            data['rate'] = round(data['worked'] / t * 100, 1) if t > 0 else 0

        log(f'[评分验证] 准确率:{result["accuracy"]}% 精确率:{result["precision"]}% 召回率:{result["recall"]}%')
        return jsonify({'success': True, 'validation': result})

    log('[Route] Log routes registered')
