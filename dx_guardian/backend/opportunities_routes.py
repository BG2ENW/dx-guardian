"""
DX Guardian - 推荐机会路由
基于当前活跃的 spot 和评分系统，生成推荐机会列表
"""

def register_routes(app, deps):
    """注册推荐机会相关路由"""
    log = deps.get('log', print)
    
    @app.route('/api/opportunities', methods=['GET'])
    def api_opportunities():
        """获取推荐机会列表"""
        try:
            import app as app_module
            
            # 确保 scorer 已初始化
            if app_module.scorer is None:
                app_module.init_scorer()
            
            # 重新获取 scorer
            current_scorer = app_module.scorer
            if current_scorer is None:
                return {'success': True, 'opportunities': [], 'message': '评分系统未初始化'}
            
            # 获取依赖
            get_history = deps.get('get_spot_history', lambda: [])
            get_band_counts_dep = deps.get('get_band_counts', lambda: {})
            get_total_spots_dep = deps.get('get_total_spots', lambda: 0)
            get_solar_dep = deps.get('get_solar_data', lambda: {})
            get_dxcc_cn = deps.get('get_dxcc_cn', lambda x: '')
            
            from app import lock
            
            with lock:
                history = get_history().copy() if callable(get_history) else list(get_history)
                bc = get_band_counts_dep().copy() if callable(get_band_counts_dep) else dict(get_band_counts_dep)
                ts = get_total_spots_dep() if callable(get_total_spots_dep) else get_total_spots_dep
                solar = get_solar_dep().copy() if callable(get_solar_dep) else dict(get_solar_dep)
            
            if not history:
                return {'success': True, 'opportunities': []}
            
            log(f'[opportunities] scorer={type(current_scorer).__name__} history={len(history)}')
            
            opportunities = []
            seen_calls = set()
            
            recent_spots = history[-100:]
            
            for spot in recent_spots:
                call = spot.get('callsign', '')
                if call in seen_calls:
                    continue
                seen_calls.add(call)
                
                dxcc = spot.get('dxcc', '')
                dxcc_count = len([s for s in history[-200:] if s.get('dxcc') == dxcc]) if dxcc else 0
                
                score_result = current_scorer.score(
                    spot=spot,
                    band_counts=bc,
                    total_spots=ts,
                    solar_data=solar,
                    spot_dxcc_count=dxcc_count
                )
                
                total_score = score_result.get('total', 0)
                
                if total_score >= 30:
                    log(f'[opportunities] 添加机会：{call} score={total_score}')
                    opportunities.append({
                        'call': call,
                        'band': spot.get('band', ''),
                        'mode': spot.get('mode', ''),
                        'freq': spot.get('freq', 0),
                        'dxcc': spot.get('dxcc', ''),
                        'dxcc_cn': get_dxcc_cn(spot.get('dxcc', '')),
                        'score': total_score,
                        'recommendation': score_result.get('recommendation', ''),
                        'timestamp': spot.get('timestamp', ''),
                    })
            
            opportunities.sort(key=lambda x: x['score'], reverse=True)
            
            return {
                'success': True,
                'opportunities': opportunities[:20],
                'total': len(opportunities)
            }
            
        except Exception as e:
            log(f'获取推荐机会失败：{e}')
            import traceback
            log(traceback.format_exc())
            return {'success': False, 'error': str(e)}, 500
