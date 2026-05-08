"""LoTW 相关 HTTP 路由"""

from flask import jsonify, request


def register_lotw_routes(app, deps):
    """注册 LoTW 路由"""
    log = deps['log']
    
    @app.route('/api/lotw/status', methods=['GET'])
    def api_lotw_status():
        """
        查询 LoTW 缓存状态
        
        Returns:
            {
                'cache_size': int,          # 缓存中的活跃呼号数量
                'cache_timestamp': str,     # 最后刷新时间 (ISO 格式)
                'age_hours': float,         # 缓存年龄（小时）
                'is_fresh': bool,           # 缓存是否新鲜（< 24 小时）
                'thread_running': bool      # 后台线程是否运行
            }
        """
        try:
            from lotw_refresh import get_lotw_cache_status
            status = get_lotw_cache_status()
            return jsonify({'success': True, 'status': status})
        except Exception as e:
            log(f'[API] /api/lotw/status 失败：{e}')
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/lotw/active', methods=['GET'])
    def api_lotw_active():
        """
        批量查询呼号的 LoTW 活跃状态
        
        Query Parameters:
            callsigns: 逗号分隔的呼号列表（例：BG2ENW,JG1ABC,JA1AAA）
        
        Returns:
            {
                'success': True,
                'results': {
                    'BG2ENW': True,
                    'JG1ABC': False,
                    ...
                }
            }
        """
        from lotw_refresh import get_lotw_active_status
        
        callsigns_param = request.args.get('callsigns', '')
        if not callsigns_param:
            return jsonify({'error': 'callsigns 参数必填'}), 400
        
        callsigns = [c.strip().upper() for c in callsigns_param.split(',') if c.strip()]
        if not callsigns:
            return jsonify({'error': '无效的呼号列表'}), 400
        
        # 限制查询数量
        if len(callsigns) > 100:
            return jsonify({'error': '最多查询 100 个呼号'}), 400
        
        try:
            results = get_lotw_active_status(callsigns)
            return jsonify({'success': True, 'results': results})
        except Exception as e:
            log(f'[API] /api/lotw/active 失败：{e}')
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/lotw/refresh', methods=['POST'])
    def api_lotw_refresh():
        """
        手动触发 LoTW 缓存刷新
        
        Returns:
            {'success': True, 'message': '刷新已触发'}
        """
        try:
            from lotw_refresh import _refresh_lotw_cache
            
            # 异步刷新（不阻塞响应）
            import threading
            thread = threading.Thread(target=_refresh_lotw_cache)
            thread.daemon = True
            thread.start()
            
            return jsonify({
                'success': True,
                'message': '后台刷新已触发，请稍后查询状态'
            })
        except Exception as e:
            log(f'[API] /api/lotw/refresh 失败：{e}')
            return jsonify({'error': str(e)}), 500
    
    log('[Route] LoTW routes registered')
