"""Watchlist related HTTP routes and storage helpers."""

from pathlib import Path
import json
import time
from datetime import datetime, timezone

from flask import jsonify, request


WATCHLIST_FILE = Path(__file__).parent / 'settings' / 'watchlists.json'


def load_watchlist():
    """加载关注列表"""
    if not WATCHLIST_FILE.exists():
        return []
    try:
        with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_watchlist(items):
    """保存关注列表"""
    WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def register_watchlist_routes(app, deps):
    log = deps['log']

    @app.route('/api/user/watchlist', methods=['GET', 'POST'])
    def api_watchlist():
        """获取或添加关注列表项"""
        if request.method == 'GET':
            return jsonify({'success': True, 'items': load_watchlist()})

        if request.method == 'POST':
            try:
                data = request.json
                if not data or not data.get('target_value'):
                    return jsonify({'error': 'target_value is required'}), 400

                target_type = data.get('target_type', 'callsign')
                valid_types = ['dxcc', 'prefix', 'callsign', 'band', 'mode']
                if target_type not in valid_types:
                    return jsonify({'error': f'Invalid target_type. Must be: {valid_types}'}), 400

                items = load_watchlist()

                for item in items:
                    if (
                        item['target_type'] == target_type
                        and item['target_value'].upper() == data['target_value'].upper()
                    ):
                        return jsonify({'error': '该关注项已存在'}), 409

                new_item = {
                    'id': str(int(time.time() * 1000)),
                    'target_type': target_type,
                    'target_value': data['target_value'].upper().strip(),
                    'band_preference': data.get('band_preference', ''),
                    'mode_preference': data.get('mode_preference', ''),
                    'enabled': True,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                }
                items.append(new_item)
                save_watchlist(items)
                log(f'[关注列表] 添加: {target_type}={new_item["target_value"]}')
                return jsonify({'success': True, 'item': new_item})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    @app.route('/api/user/watchlist/<item_id>', methods=['PUT', 'DELETE'])
    def api_watchlist_item(item_id):
        """更新或删除关注列表项"""
        items = load_watchlist()
        item = next((i for i in items if i['id'] == item_id), None)
        if not item:
            return jsonify({'error': 'Item not found'}), 404

        if request.method == 'PUT':
            try:
                data = request.json
                if data.get('target_type'):
                    valid_types = ['dxcc', 'prefix', 'callsign', 'band', 'mode']
                    if data['target_type'] not in valid_types:
                        return jsonify({'error': 'Invalid target_type'}), 400
                    item['target_type'] = data['target_type']
                if data.get('target_value'):
                    item['target_value'] = data['target_value'].upper().strip()
                if 'band_preference' in data:
                    item['band_preference'] = data['band_preference']
                if 'mode_preference' in data:
                    item['mode_preference'] = data['mode_preference']
                if 'enabled' in data:
                    item['enabled'] = bool(data['enabled'])

                save_watchlist(items)
                log(f'[关注列表] 更新: {item["target_type"]}={item["target_value"]}')
                return jsonify({'success': True, 'item': item})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        items = [i for i in items if i['id'] != item_id]
        save_watchlist(items)
        log(f'[关注列表] 删除: {item_id}')
        return jsonify({'success': True})

    @app.route('/api/user/watchlist/import', methods=['POST'])
    def api_watchlist_import():
        """批量导入关注列表"""
        try:
            data = request.json
            if not data or not isinstance(data.get('items', []), list):
                return jsonify({'error': 'items must be a list'}), 400

            items = load_watchlist()
            existing_keys = {(i['target_type'], i['target_value']) for i in items}
            imported = 0
            skipped = 0

            for entry in data['items']:
                target_type = entry.get('target_type', 'callsign')
                target_value = entry.get('target_value', '').upper().strip()
                if not target_value:
                    skipped += 1
                    continue

                key = (target_type, target_value)
                if key in existing_keys:
                    skipped += 1
                    continue

                items.append(
                    {
                        'id': str(int(time.time() * 1000)) + str(imported),
                        'target_type': target_type,
                        'target_value': target_value,
                        'band_preference': entry.get('band_preference', ''),
                        'mode_preference': entry.get('mode_preference', ''),
                        'enabled': True,
                        'created_at': datetime.now(timezone.utc).isoformat(),
                    }
                )
                existing_keys.add(key)
                imported += 1

            save_watchlist(items)
            log(f'[关注列表] 导入: {imported}条新增, {skipped}条跳过')
            return jsonify({'success': True, 'imported': imported, 'skipped': skipped})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    log('[Route] Watchlist routes registered')
