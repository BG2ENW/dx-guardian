"""Web Push related HTTP routes and storage helpers."""

from pathlib import Path
import json
from flask import jsonify, request


def register_push_routes(app, deps):
    log = deps['log']
    external_api_error = deps['external_api_error']
    vapid_public_key = deps['vapid_public_key']
    vapid_private_key_pem = deps['vapid_private_key_pem']
    vapid_email = deps['vapid_email']

    vapid_config_file = Path(__file__).parent / 'settings' / 'vapid.json'
    push_subs_file = Path(__file__).parent / 'settings' / 'push_subscriptions.json'

    def load_vapid_config():
        if vapid_public_key and vapid_private_key_pem and vapid_email:
            return {
                'vapid_public_key': vapid_public_key,
                'vapid_private_key_pem': vapid_private_key_pem,
                'vapid_email': vapid_email,
            }
        if not vapid_config_file.exists():
            return None
        with open(vapid_config_file, 'r') as f:
            return json.load(f)

    def load_push_subs():
        if not push_subs_file.exists():
            return []
        try:
            with open(push_subs_file, 'r') as f:
                return json.load(f)
        except Exception:
            return []

    def save_push_subs(subs):
        push_subs_file.parent.mkdir(parents=True, exist_ok=True)
        with open(push_subs_file, 'w') as f:
            json.dump(subs, f, indent=2)

    def send_push_notification(title, body, tag='dx-alert'):
        vapid = load_vapid_config()
        if not vapid:
            return False
        subs = load_push_subs()
        if not subs:
            return False
        from pywebpush import webpush, WebPushException

        sent = 0
        for sub in subs:
            try:
                webpush(
                    subscription_info=sub,
                    data=json.dumps(
                        {'title': title, 'body': body, 'tag': tag, 'icon': '/images/icon-192.png'}
                    ),
                    vapid_private_key=vapid['vapid_private_key_pem'],
                    vapid_claims={'sub': f'mailto:{vapid["vapid_email"]}'},
                )
                sent += 1
            except WebPushException as e:
                log(f'[WebPush] 推送失败: {e}')
                if e.response and e.response.status_code in [404, 410]:
                    subs.remove(sub)
                    save_push_subs(subs)
            except Exception as e:
                log(f'[WebPush] 异常: {e}')
        if sent > 0:
            log(f'[WebPush] 推送成功: {title} → {sent}个设备')
        return sent > 0

    @app.route('/api/push/public_key', methods=['GET'])
    def api_push_public_key():
        vapid = load_vapid_config()
        if not vapid:
            return jsonify({'error': 'VAPID 未配置'}), 500
        return jsonify({'public_key': vapid['vapid_public_key']})

    @app.route('/api/push/subscribe', methods=['POST'])
    def api_push_subscribe():
        try:
            sub = request.json
            if not sub or 'endpoint' not in sub:
                return jsonify({'error': '无效订阅数据'}), 400
            subs = load_push_subs()
            subs = [s for s in subs if s.get('endpoint') != sub.get('endpoint')]
            subs.append(sub)
            save_push_subs(subs)
            log(f'[WebPush] 新订阅: {sub.get("endpoint", "?")[:50]}')
            return jsonify({'success': True, 'total': len(subs)})
        except Exception as e:
            external_api_error('WebPush', e)
            return jsonify({'error': '订阅保存失败'}), 500

    @app.route('/api/push/unsubscribe', methods=['POST'])
    def api_push_unsubscribe():
        try:
            endpoint = request.json.get('endpoint', '')
            if not endpoint:
                return jsonify({'error': '无效'}), 400
            subs = load_push_subs()
            subs = [s for s in subs if s.get('endpoint') != endpoint]
            save_push_subs(subs)
            return jsonify({'success': True, 'total': len(subs)})
        except Exception as e:
            external_api_error('WebPush', e)
            return jsonify({'error': '取消订阅失败'}), 500

    @app.route('/api/push/test', methods=['POST'])
    def api_push_test():
        send_push_notification('DX Guardian 测试', 'Web Push 推送功能正常！')
        return jsonify({'success': True})

    @app.route('/api/push/status', methods=['GET'])
    def api_push_status():
        vapid = load_vapid_config()
        subs = load_push_subs()
        return jsonify(
            {
                'enabled': bool(vapid),
                'subscribers': len(subs),
                'public_key': vapid['vapid_public_key'][:20] + '...' if vapid else None,
            }
        )

    log('[Route] Web Push routes registered')
