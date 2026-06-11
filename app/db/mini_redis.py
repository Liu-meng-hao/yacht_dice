"""
轻量级内存 Redis 服务器（Windows 友好）
完全使用 Python 实现，不需要外部依赖
"""
import socket
import threading
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class MiniRedisServer:
    """轻量级内存 Redis 服务器（兼容基础功能）"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379):
        self.host = host
        self.port = port
        self._data: Dict[str, Dict[str, Any]] = {}
        self._server_socket: Optional[socket.socket] = None
        self._running = False
        self._server_thread: Optional[threading.Thread] = None
        self._clients = []
        
    def start(self):
        """启动服务器"""
        try:
            # 先尝试关闭可能的旧连接
            try:
                import redis
                r = redis.Redis(host=self.host, port=self.port, socket_timeout=1)
                r.ping()
                logger.info(f"Redis 服务器已在运行，端口 {self.port}")
                return True
            except:
                pass
                
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(5)
            self._running = True
            
            self._server_thread = threading.Thread(target=self._run_server, daemon=True)
            self._server_thread.start()
            
            logger.info(f"✅ 轻量级 Redis 服务器已启动: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"启动 Redis 服务器失败: {e}")
            return False
    
    def _run_server(self):
        """服务器主循环"""
        while self._running:
            try:
                self._server_socket.settimeout(1.0)
                try:
                    client_socket, client_address = self._server_socket.accept()
                    client_socket.settimeout(30.0)
                    self._clients.append(client_socket)
                    
                    client_thread = threading.Thread(
                        target=self._handle_client, 
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                except socket.timeout:
                    continue
            except Exception as e:
                if self._running:
                    logger.error(f"接受连接出错: {e}")
    
    def _handle_client(self, client_socket: socket.socket, client_address):
        """处理客户端请求"""
        try:
            while self._running:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    
                    response = self._process_command(data.decode('utf-8', errors='ignore'))
                    client_socket.send(response.encode('utf-8'))
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.debug(f"处理客户端出错: {e}")
                    break
        finally:
            try:
                client_socket.close()
            except:
                pass
            if client_socket in self._clients:
                self._clients.remove(client_socket)
    
    def _process_command(self, command: str):
        """处理 Redis 命令"""
        lines = [line.strip() for line in command.split('\r\n') if line.strip()]
        if not lines:
            return "-ERR empty command\r\n"
        
        # 简单的 RESP 协议解析
        try:
            parts = []
            i = 0
            while i < len(lines):
                if lines[i].startswith('*'):
                    num_args = int(lines[i][1:])
                    i += 1
                    for _ in range(num_args):
                        if i < len(lines) and lines[i].startswith('$'):
                            i += 1
                            if i < len(lines):
                                parts.append(lines[i])
                                i += 1
                    break
                i += 1
            
            if not parts:
                # 尝试简单命令格式
                cmd_line = lines[0].split()
                if cmd_line:
                    parts = cmd_line
        except:
            parts = lines[0].split() if lines else []
        
        if not parts:
            return "-ERR no command\r\n"
        
        cmd = parts[0].upper()
        
        if cmd == 'PING':
            return "+PONG\r\n"
        
        elif cmd == 'SET':
            if len(parts) < 3:
                return "-ERR wrong number of arguments for 'set' command\r\n"
            key = parts[1]
            value = parts[2]
            
            # 检查是否有 ex 参数
            expire = None
            for j in range(3, len(parts)):
                if parts[j].upper() == 'EX' and j + 1 < len(parts):
                    expire = int(parts[j + 1])
                    break
            
            self._data[key] = {
                'value': value,
                'expire_at': datetime.now() + timedelta(seconds=expire) if expire else None
            }
            return "+OK\r\n"
        
        elif cmd == 'GET':
            if len(parts) < 2:
                return "-ERR wrong number of arguments for 'get' command\r\n"
            key = parts[1]
            if key in self._data:
                item = self._data[key]
                if item.get('expire_at') and datetime.now() > item['expire_at']:
                    del self._data[key]
                    return "$-1\r\n"
                return f"${len(item['value'])}\r\n{item['value']}\r\n"
            return "$-1\r\n"
        
        elif cmd == 'SETEX':
            if len(parts) < 4:
                return "-ERR wrong number of arguments for 'setex' command\r\n"
            key = parts[1]
            expire = int(parts[2])
            value = parts[3]
            
            self._data[key] = {
                'value': value,
                'expire_at': datetime.now() + timedelta(seconds=expire)
            }
            return "+OK\r\n"
        
        elif cmd == 'DEL':
            count = 0
            for key in parts[1:]:
                if key in self._data:
                    del self._data[key]
                    count += 1
            return f":{count}\r\n"
        
        elif cmd == 'EXISTS':
            count = 0
            for key in parts[1:]:
                if key in self._data:
                    item = self._data[key]
                    if not item.get('expire_at') or datetime.now() < item['expire_at']:
                        count += 1
                    else:
                        del self._data[key]
            return f":{count}\r\n"
        
        elif cmd == 'HSET':
            if len(parts) < 4:
                return "-ERR wrong number of arguments for 'hset' command\r\n"
            key = parts[1]
            if key not in self._data:
                self._data[key] = {'value': '{}', 'expire_at': None}
            
            hset_data = {}
            try:
                hset_data = json.loads(self._data[key]['value'])
            except:
                pass
            
            field = parts[2]
            val = parts[3]
            new_field = field not in hset_data
            hset_data[field] = val
            self._data[key]['value'] = json.dumps(hset_data)
            return f":{1 if new_field else 0}\r\n"
        
        elif cmd == 'HGET':
            if len(parts) < 3:
                return "-ERR wrong number of arguments for 'hget' command\r\n"
            key = parts[1]
            field = parts[2]
            if key in self._data:
                item = self._data[key]
                if item.get('expire_at') and datetime.now() > item['expire_at']:
                    del self._data[key]
                    return "$-1\r\n"
                
                try:
                    hset_data = json.loads(item['value'])
                    if field in hset_data:
                        return f"${len(hset_data[field])}\r\n{hset_data[field]}\r\n"
                except:
                    pass
            return "$-1\r\n"
        
        elif cmd == 'HGETALL':
            if len(parts) < 2:
                return "-ERR wrong number of arguments for 'hgetall' command\r\n"
            key = parts[1]
            if key in self._data:
                item = self._data[key]
                if item.get('expire_at') and datetime.now() > item['expire_at']:
                    del self._data[key]
                    return "*0\r\n"
                try:
                    hset_data = json.loads(item['value'])
                    response = f"*{len(hset_data) * 2}\r\n"
                    for k, v in hset_data.items():
                        response += f"${len(k)}\r\n{k}\r\n${len(v)}\r\n{v}\r\n"
                    return response
                except:
                    pass
            return "*0\r\n"
        
        elif cmd == 'HDEL':
            if len(parts) < 3:
                return "-ERR wrong number of arguments for 'hdel' command\r\n"
            key = parts[1]
            if key not in self._data:
                return ":0\r\n"
            
            count = 0
            try:
                hset_data = json.loads(self._data[key]['value'])
                for field in parts[2:]:
                    if field in hset_data:
                        del hset_data[field]
                        count += 1
                self._data[key]['value'] = json.dumps(hset_data)
            except:
                pass
            return f":{count}\r\n"
        
        elif cmd == 'EXPIRE':
            if len(parts) < 3:
                return "-ERR wrong number of arguments for 'expire' command\r\n"
            key = parts[1]
            if key in self._data:
                self._data[key]['expire_at'] = datetime.now() + timedelta(seconds=int(parts[2]))
                return ":1\r\n"
            return ":0\r\n"
        
        elif cmd == 'QUIT':
            return "+OK\r\n"
        
        else:
            return f"-ERR unknown command '{cmd}'\r\n"
    
    def stop(self):
        """停止服务器"""
        self._running = False
        
        for client in self._clients[:]:
            try:
                client.close()
            except:
                pass
        
        if self._server_socket:
            try:
                self._server_socket.close()
            except:
                pass
        
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=2.0)


# 全局服务器实例
_server: Optional[MiniRedisServer] = None


def start_server() -> bool:
    """启动嵌入式 Redis 服务器"""
    global _server
    if _server and _server._running:
        return True
    
    _server = MiniRedisServer()
    return _server.start()


def stop_server():
    """停止服务器"""
    global _server
    if _server:
        _server.stop()
        _server = None
