"""
机会评分系统（增强版）
新增: LoTW 认证加分 (+5 分)
"""
from scorer import OpportunityScorer

class EnhancedOpportunityScorer(OpportunityScorer):
    """增强版评分器"""
    
    def score(self, spot: dict, band_counts: dict, total_spots: int,
              solar_data: dict, spot_dxcc_count: int = 0) -> dict:
        """增强版评分（增加 LoTW 认证）"""
        
        # 基础评分
        result = super().score(spot, band_counts, total_spots, solar_data, spot_dxcc_count)
        
        # LoTW 认证加分
        lotw_verified = spot.get('lotw_verified', False)
        if lotw_verified:
            result['total'] = min(100, result['total'] + 5)
            result['factors']['lotw_verified'] = 5
            result['factors']['lotw_note'] = '✓ LoTW 认证用户 (+5)'
        
        return result

# 单例
_enhanced_scorer = None

def get_enhanced_scorer():
    if _enhanced_scorer is None:
        _enhanced_scorer = EnhancedOpportunityScorer()
    return _enhanced_scorer
