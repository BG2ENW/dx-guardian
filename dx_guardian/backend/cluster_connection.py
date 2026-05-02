"""
Cluster Telnet 连接模块
使用 socket 连接（不依赖废弃的 telnetlib）
"""
import socket
import time
import re
import threading
import queue
from datetime import datetime, timezone
from config import CLUSTER_SERVERS, MY_CALL, RECONNECT_DELAYS, MAX_RECONNECT_ATTEMPTS

class ClusterClient:
    """DX Cluster 客户端"""
    
    SPOT_PATTERN = re.compile(
        r'DX\s+de\s+(?P<reporter>.+?)\s*:\s*'
        r'(?P<callsign>[A-Z0-9/]+)\s+on\s+'
        r'(?P<freq>[\d.]+)\s+'
        r'(?P<mode>[A-Z0-9]+)(?:\s+(?P<comment>.*?))?'
        r'(?:\s+(?P<time>\d{4}Z))?'
    )
    
    def __init__(self, spot_queue=None):
        """
        初始化 Cluster 客户端
        
        Args:
            spot_queue: Spot 队列（用于线程间通信）
        """
        self.spot_queue = spot_queue if spot_queue else queue.Queue()
        self.connected = False
        self.running = False
        self.socket = None
        self.current_server_index = 0
        self.reconnect_attempts = 0
        
        import sys
        sys.path.insert(0, '..')
        
    def connect(self):
        """连接到 Cluster 服务器"""
        self.running = True
        
        # 启动连接线程
        self.thread = threading.Thread(target=self._connection_loop, daemon=True)
        self.thread.start()
        
    def _connection_loop(self):
        """连接循环（包含重连逻辑）"""
        while self.running:
            try:
                self._connect_to_server()
                self.reconnect_attempts = 0  # 连接成功，重置重连次数
                self._receive_loop()
            except Exception as e:
                print(f'连接断开: {e}')
                self.connected = False
                self._handle_reconnect()
            
            time.sleep(1)
    
    def _connect_to_server(self):
        """
        连接到当前服务器
        
        Raises:
            Exception: 连接失败
        """
        server = CLUSTER_SERVERS[self.current_server_index]
        print(f'正在连接到 {server["host"]}:{server["port"]}...')
        
        # 创建 socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(30)  # 30秒超时
        
        # 连接
        self.socket.connect((server['host'], server['port']))
        
        # 登录
        self._login()
        
        self.connected = True
        print(f'✅ 已连接到 Cluster 服务器')
    
    def _login(self):
        """登录到 Cluster"""
        # 等待提示
        data = self._receive_line().decode().strip()
        print(f'服务器提示: {data}')
        
        # 发送呼号
        login_msg = f'{MY_CALL}\n'
        self.socket.send(login_msg.encode())
        print(f'已发送登录信息: {MY_CALL}')
        
        # 等待欢迎消息
        time.sleep(1)
        data = self._receive_line().decode()
        print(f'欢迎消息: {data.strip()}')
        
        # 设置一些常用命令
        self._send_cluster_command('SET/USER DXCluster')
        self._send_cluster_command('SET/DXCOUNT 20')
    
    def _receive_loop(self):
        """
        接收数据循环
        
        Raises:
            Exception: 接收错误或断开连接
        """
        buffer = b''
        
        while self.running and self.connected:
            try:
                # 接收数据
                data = self.socket.recv(4096)
                if not data:
                    raise Exception('连接已关闭')
                
                buffer += data
                
                # 按行处理
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    line_str = line.decode('utf-8', errors='ignore').strip()
                    
                    if line_str:
                        self._process_line(line_str)
                        
            except socket.timeout:
                # 超时，发送心跳
                self._send_heartbeat()
            except Exception as e:
                raise e
    
    def _receive_line(self):
        """
        接收一行数据
        
        Returns:
            bytes: 接收到的数据
        """
        buffer = b''
        while True:
            data = self.socket.recv(1)
            if not data:
                raise Exception('连接已关闭')
            buffer += data
            if data == b'\n':
                return buffer
    
    def _process_line(self, line):
        """
        处理一行 Cluster 数据
        
        Args:
            line: 一行文本
        """
        # 尝试解析 Spot
        match = self.SPOT_PATTERN.search(line)
        if match:
            spot = self._parse_spot(match.groupdict(), line)
            if spot:
                self.spot_queue.put(spot)
                # 导入 app 并广播
                self._broadcast_spot(spot)
        else:
            # 其他消息（如果是 DX 开头的，打印出来方便调试）
            if line.startswith('DX de'):
                print(f'未解析的 Spot: {line}')
    
    def _parse_spot(self, match_groups, original_line):
        """
        解析 Spot 数据
        
        Args:
            match_groups: 正则匹配的组
            original_line: 原始行
            
        Returns:
            dict: Spot 数据字典，或 None
        """
        try:
            callsign = match_groups['callsign'].upper()
            freq = float(match_groups['freq'])
            reporter = match_groups['reporter']
            mode = match_groups.get('mode', 'CW').upper()
            
            # 计算波段
            band = self._freq_to_band(freq)
            
            # 尝试解析 Grid（从注释中）
            grid = None
            comment = match_groups.get('comment', '').upper()
            grid_match = re.search(r'([A-Z]{2}\d{2}[A-Z]{0,2})', comment)
            if grid_match:
                grid = grid_match.group(1)
            
            spot = {
                'callsign': callsign,
                'freq': freq,
                'band': band,
                'mode': mode,
                'reporter': reporter,
                'grid': grid,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'raw': original_line,
                'lat': None,  # 待坐标解析模块处理
                'lon': None,
                'dxcc': None
            }
            
            # 简单的坐标解析（只根据呼号前缀）
            spot['lat'], spot['lon'], spot['dxcc'] = self._resolve_coordinates(callsign, grid)
            
            return spot
            
        except Exception as e:
            print(f'解析 Spot 失败: {e}')
            return None
    
    def _freq_to_band(self, freq_mhz):
        """
        频率转波段
        """
        freq_mhz = float(freq_mhz)
        
        if freq_mhz < 2:
            return '160m'
        elif freq_mhz < 4:
            return '80m'
        elif freq_mhz < 6:
            return '60m'
        elif freq_mhz < 8:
            return '40m'
        elif freq_mhz < 11:
            return '30m'
        elif freq_mhz < 15:
            return '20m'
        elif freq_mhz < 19:
            return '17m'
        elif freq_mhz < 22:
            return '15m'
        elif freq_mhz < 25:
            return '12m'
        elif freq_mhz < 30:
            return '10m'
        elif freq_mhz < 55:
            return '6m'
        elif freq_mhz < 145:
            return '2m'
        elif freq_mhz < 440:
            return '70cm'
        elif freq_mhz < 1300:
            return '23cm'
        else:
            return 'unknown'
    
    def _resolve_coordinates(self, callsign, grid):
        """
        解析坐标（简化版，只根据呼号前缀）
        
        Args:
            callsign: 呼号
            grid: Grid（如果有）
        
        Returns:
            tuple: (lat, lon, dxcc)
        """
        # TODO: 实现完整的三级坐标解析
        # 这里先用一个简单的映射，后续要整合 coordinate_resolver 模块
        
        # 提取前缀
        prefix = callsign[:2]
        
        # 简单的默认坐标（应该是0,0表示未知）
        return 0.0, 0.0, prefix
    
    def _broadcast_spot(self, spot):
        """
        广播 Spot 到前端
        
        Args:
            spot: Spot 数据
        """
        # 导入 app 并调用 broadcast_spot
        # 由于在独立线程中，需要使用线程安全的方式
        pass  # TODO: 实现广播
    
    def _send_heartbeat(self):
        """发送心跳保持连接"""
        try:
            self.socket.send(b'\n')
        except:
            pass
    
    def _send_cluster_command(self, command):
        """
        发送命令到 Cluster
        
        Args:
            command: 命令字符串
        """
        try:
            self.socket.send(f'{command}\n'.encode())
            time.sleep(0.5)
        except Exception as e:
            print(f'发送命令失败: {e}')
    
    def _handle_reconnect(self):
        """处理重连"""
        if self.reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
            print(f'❌ 重连失败次数过多({MAX_RECONNECT_ATTEMPTS})，停止尝试')
            self.running = False
            return
        
        # 获取重连延迟
        delay_index = min(self.reconnect_attempts, len(RECONNECT_DELAYS) - 1)
        delay = RECONNECT_DELAYS[delay_index]
        
        print(f'⏰ {delay}秒后重连... (尝试 {self.reconnect_attempts + 1}/{MAX_RECONNECT_ATTEMPTS})')
        time.sleep(delay)
        
        self.reconnect_attempts += 1
        
        # 切换到下一个服务器（如果有）
        if self.reconnect_attempts > 2:
            self.current_server_index = (self.current_server_index + 1) % len(CLUSTER_SERVERS)
    
    def disconnect(self):
        """断开连接"""
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass


if __name__ == '__main__':
    # 测试连接
    client = ClusterClient()
    client.connect()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n断开连接...')
        client.disconnect()
