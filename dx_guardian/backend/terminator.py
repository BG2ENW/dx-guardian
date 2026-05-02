"""
DX Guardian - 灰线（Terminator）计算模块
计算地球上昼夜分界线位置，用于地图展示
"""
import math
from datetime import datetime, timezone


class TerminatorCalculator:
    """灰线计算器 - 基于太阳直射点位置计算昼夜分界线"""

    def __init__(self):
        self.earth_tilt = 23.44  # 地轴倾角（度）

    def get_sun_declination(self, utc_now: datetime = None) -> float:
        """计算太阳赤纬（度）
        基于 NOAA 简化公式
        """
        if utc_now is None:
            utc_now = datetime.now(timezone.utc)

        # 一年中的天数（1月1日=1）
        day_of_year = utc_now.timetuple().tm_yday

        # 太阳赤纬公式
        declination = self.earth_tilt * math.sin(math.radians((360 / 365) * (day_of_year - 81)))

        return declination

    def get_sun_hour_angle(self, lat_deg: float, decl_deg: float) -> float:
        """计算太阳时角（度）
        用于确定给定纬度的昼夜分界
        """
        lat_rad = math.radians(lat_deg)
        decl_rad = math.radians(decl_deg)

        # cos(hour_angle) = -tan(lat) * tan(decl)
        cos_ha = -math.tan(lat_rad) * math.tan(decl_rad)

        # 限制在 [-1, 1] 范围内
        cos_ha = max(-1.0, min(1.0, cos_ha))

        return math.degrees(math.acos(cos_ha))

    def calculate_terminator_points(self, utc_now: datetime = None) -> dict:
        """计算灰线坐标点

        返回:
            'sunrise': 日出线坐标 [(lat, lon), ...]
            'sunset': 日落线坐标 [(lat, lon), ...]
            'sun_declination': 太阳赤纬
            'subsolar_lat': 太阳直射纬度
            'subsolar_lon': 太阳直射经度
        """
        if utc_now is None:
            utc_now = datetime.now(timezone.utc)

        decl = self.get_sun_declination(utc_now)

        # 太阳直射点经度（基于 UTC 时间）
        # 太阳在 UTC 12:00 位于本初子午线
        hour_angle_sun = (utc_now.hour + utc_now.minute / 60.0 - 12.0) * 15.0
        subsolar_lon = -hour_angle_sun  # 经度 = -时角
        subsolar_lat = decl

        sunrise_points = []
        sunset_points = []

        # 从南极到北极计算灰线
        for lat_deg in range(-90, 91, 2):
            ha = self.get_sun_hour_angle(lat_deg, decl)

            if ha > 0:
                # 日出线和日落线的经度
                sunrise_lon = subsolar_lon - ha
                sunset_lon = subsolar_lon + ha

                # 归一化到 [-180, 180]
                sunrise_lon = ((sunrise_lon + 180) % 360) - 180
                sunset_lon = ((sunset_lon + 180) % 360) - 180

                sunrise_points.append((lat_deg, sunrise_lon))
                sunset_points.append((lat_deg, sunset_lon))

        return {
            'sunrise': sunrise_points,
            'sunset': sunset_points,
            'sun_declination': round(decl, 2),
            'subsolar_lat': round(subsolar_lat, 2),
            'subsolar_lon': round(subsolar_lon, 2),
            'timestamp': utc_now.isoformat()
        }

    def get_day_night_polygon(self, utc_now: datetime = None) -> dict:
        """计算白天和黑夜区域的多边形坐标
        用于 Leaflet 多边形绘制
        """
        terminator = self.calculate_terminator_points(utc_now)

        # 夜晚区域：从日出线南端 → 日出线北端 → 北极 → 日落线北端 → 日落线南端 → 南极
        night_polygon = []
        sunrise = terminator['sunrise']
        sunset = terminator['sunset']

        if sunrise and sunset:
            # 日出线（从南到北）
            night_polygon.extend(sunrise)
            # 北极
            night_polygon.append((90, sunset[-1][1] if sunset else 180))
            # 日落线（从北到南）
            night_polygon.extend(reversed(sunset))
            # 南极
            night_polygon.append((-90, sunrise[0][1] if sunrise else -180))

        # 白天区域 = 整个世界 - 夜晚区域
        # 简化：取夜晚区域的反面
        day_polygon = []
        if sunrise and sunset:
            # 日出线（从北到南）
            day_polygon.extend(reversed(sunrise))
            # 南极
            day_polygon.append((-90, sunset[0][1] if sunset else 180))
            # 日落线（从南到北）
            day_polygon.extend(sunset)
            # 北极
            day_polygon.append((90, sunrise[-1][1] if sunrise else -180))

        return {
            'night': night_polygon,
            'day': day_polygon,
            'sun_declination': terminator['sun_declination'],
            'subsolar_lat': terminator['subsolar_lat'],
            'subsolar_lon': terminator['subsolar_lon'],
            'timestamp': terminator['timestamp']
        }

    def get_terminator_geojson(self, utc_now: datetime = None) -> dict:
        """生成 GeoJSON 格式的灰线数据
        可直接用于 Leaflet GeoJSON 图层
        """
        terminator = self.calculate_terminator_points(utc_now)
        sunrise = terminator['sunrise']
        sunset = terminator['sunset']

        features = []

        # 日出线
        if sunrise:
            features.append({
                'type': 'Feature',
                'properties': {'type': 'sunrise', 'name': '日出线'},
                'geometry': {
                    'type': 'LineString',
                    'coordinates': [[lon, lat] for lat, lon in sunrise]
                }
            })

        # 日落线
        if sunset:
            features.append({
                'type': 'Feature',
                'properties': {'type': 'sunset', 'name': '日落线'},
                'geometry': {
                    'type': 'LineString',
                    'coordinates': [[lon, lat] for lat, lon in sunset]
                }
            })

        return {
            'type': 'FeatureCollection',
            'features': features
        }


if __name__ == '__main__':
    calc = TerminatorCalculator()
    geojson = calc.get_terminator_geojson()
    print(f"Sun Declination: {geojson['features'][0]['properties']}")
    print(f"Features: {len(geojson['features'])}")

    for f in geojson['features']:
        coords = f['geometry']['coordinates']
        print(f"{f['properties']['name']}: {len(coords)} points")
