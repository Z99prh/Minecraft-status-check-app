from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.utils import platform
from kivy.graphics import Color, Rectangle, RoundedRectangle
from plyer import notification
import socket
import struct
import threading
import json
import re

# Register Minecraft font
LabelBase.register(name="Minecraft", fn_regular="minecraft.ttf")

class MinecraftServerPinger:
    """Minecraft Server Status Protocol implementation"""
    
    @staticmethod
    def ping(host, port=25565, timeout=5):
        """Get full server status"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            
            # Send handshake
            handshake = b'\x00'
            handshake += MinecraftServerPinger._pack_varint(47)
            handshake += MinecraftServerPinger._pack_data(host.encode('utf8'))
            handshake += struct.pack('>H', port)
            handshake += MinecraftServerPinger._pack_varint(1)
            MinecraftServerPinger._send_packet(sock, handshake)
            
            # Request status
            MinecraftServerPinger._send_packet(sock, b'\x00')
            
            # Read response
            MinecraftServerPinger._unpack_varint(sock)
            MinecraftServerPinger._unpack_varint(sock)
            data_length = MinecraftServerPinger._unpack_varint(sock)
            data = b''
            while len(data) < data_length:
                chunk = sock.recv(data_length - len(data))
                if not chunk:
                    break
                data += chunk
            
            sock.close()
            
            response = json.loads(data.decode('utf8'))
            
            # Parse MOTD (can be string or dict)
            motd_raw = response.get('description', '')
            if isinstance(motd_raw, dict):
                motd = motd_raw.get('text', '')
                if 'extra' in motd_raw:
                    for extra in motd_raw['extra']:
                        if isinstance(extra, dict) and 'text' in extra:
                            motd += extra['text']
            else:
                motd = str(motd_raw)
            
            # Clean MOTD (remove color codes)
            motd = re.sub(r'§[0-9a-fk-or]', '', motd)
            
            return {
                'online': True,
                'version': response.get('version', {}).get('name', 'Unknown'),
                'players_online': response.get('players', {}).get('online', 0),
                'players_max': response.get('players', {}).get('max', 0),
                'motd': motd.strip() if motd else 'No MOTD'
            }
            
        except socket.timeout:
            return {'online': False, 'error': 'Connection timeout'}
        except ConnectionRefusedError:
            return {'online': False, 'error': 'Connection refused'}
        except Exception as e:
            return {'online': False, 'error': str(e)}
    
    @staticmethod
    def _pack_varint(value):
        result = b''
        while True:
            temp = value & 0x7F
            value >>= 7
            if value != 0:
                result += struct.pack('B', temp | 0x80)
            else:
                result += struct.pack('B', temp)
                break
        return result
    
    @staticmethod
    def _pack_data(data):
        return MinecraftServerPinger._pack_varint(len(data)) + data
    
    @staticmethod
    def _send_packet(sock, data):
        sock.send(MinecraftServerPinger._pack_varint(len(data)) + data)
    
    @staticmethod
    def _unpack_varint(sock):
        result = 0
        for i in range(5):
            data = sock.recv(1)
            if not data:
                break
            byte = struct.unpack('B', data)[0]
            result |= (byte & 0x7F) << 7 * i
            if not byte & 0x80:
                break
        return result


class GlowingButton(Button):
    """Custom button with glowing effect"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        
        with self.canvas.before:
            Color(0, 0.5, 0, 1)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[15])
        
        self.bind(pos=self.update_bg, size=self.update_bg)
    
    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


class StatusCard(FloatLayout):
    """Card widget to display server status"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 0.45)
        
        with self.canvas.before:
            Color(0.05, 0.05, 0.05, 1)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[20])
        
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        # Center container for all text
        center_container = FloatLayout(size_hint=(1, 1))
        
        # Status indicator (circle)
        self.status_indicator = FloatLayout(size_hint=(None, None), size=(20, 20),
                                           pos_hint={'center_x': 0.5, 'top': 0.95})
        with self.status_indicator.canvas:
            self.indicator_color = Color(0.5, 0.5, 0.5, 1)
            self.indicator_circle = RoundedRectangle(
                pos=self.status_indicator.pos,
                size=self.status_indicator.size,
                radius=[10]
            )
        self.status_indicator.bind(pos=self.update_indicator, size=self.update_indicator)
        center_container.add_widget(self.status_indicator)
        
        # Status label
        self.status_label = Label(
            text='OFFLINE',
            font_name='Minecraft',
            font_size='28sp',
            bold=True,
            color=(0.7, 0.7, 0.7, 1),
            pos_hint={'center_x': 0.5, 'top': 0.95},
            size_hint=(0.9, 0.15),
            halign='center',
            valign='middle'
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))
        center_container.add_widget(self.status_label)
        
        # Version label - centered with spacing
        self.version_label = Label(
            text='Version: ---',
            font_name='Minecraft',
            font_size='20sp',
            color=(0.6, 0.9, 1, 1),
            pos_hint={'center_x': 0.5, 'top': 0.75},
            size_hint=(0.9, 0.15),
            halign='center',
            valign='middle'
        )
        self.version_label.bind(size=self.version_label.setter('text_size'))
        center_container.add_widget(self.version_label)
        
        # Players label - centered with spacing
        self.players_label = Label(
            text='Players: 0/0',
            font_name='Minecraft',
            font_size='20sp',
            color=(1, 0.85, 0, 1),
            pos_hint={'center_x': 0.5, 'top': 0.6},
            size_hint=(0.9, 0.15),
            halign='center',
            valign='middle'
        )
        self.players_label.bind(size=self.players_label.setter('text_size'))
        center_container.add_widget(self.players_label)
        
        # MOTD label - centered with proper spacing
        self.motd_label = Label(
            text='MOTD: ---',
            font_name='Minecraft',
            font_size='18sp',
            color=(0.8, 0.8, 0.8, 1),
            pos_hint={'center_x': 0.5, 'top': 0.35},
            size_hint=(0.9, 0.4),
            halign='center',
            valign='top',
            markup=True
        )
        self.motd_label.bind(size=self.motd_label.setter('text_size'))
        center_container.add_widget(self.motd_label)
        
        self.add_widget(center_container)
    
    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
    
    def update_indicator(self, *args):
        self.indicator_circle.pos = self.status_indicator.pos
        self.indicator_circle.size = self.status_indicator.size
    
    def set_online(self, version, players_online, players_max, motd):
        """Update card with online status"""
        self.status_label.text = 'ONLINE'
        self.status_label.color = (0.2, 1, 0.2, 1)
        self.indicator_color.rgba = (0.2, 1, 0.2, 1)
        
        self.version_label.text = f'Version: {version}'
        self.players_label.text = f'Players: {players_online}/{players_max}'
        self.motd_label.text = f'[b]MOTD:[/b]\n{motd}'
    
    def set_offline(self, error=''):
        """Update card with offline status"""
        self.status_label.text = 'OFFLINE'
        self.status_label.color = (1, 0.2, 0.2, 1)
        self.indicator_color.rgba = (1, 0.2, 0.2, 1)
        
        self.version_label.text = 'Version: ---'
        self.players_label.text = 'Players: 0/0'
        self.motd_label.text = f'[b]Error:[/b]\n{error}' if error else 'MOTD: ---'


class MCStatusApp(App):
    def build(self):
        self.title = 'MC Server Status'
        self.server_addr = ""
        self.server_port = 25565
        self.last_status = None
        self.monitoring = False
        
        # Main layout
        root = FloatLayout()
        
        # AMOLED Black background
        with root.canvas.before:
            Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self.update_bg, size=self.update_bg)
        
        # Main content layout - now without the title
        main_content = BoxLayout(
            orientation='vertical',
            padding=20,
            spacing=20,
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            size_hint=(1, 0.85)
        )
        
        # Top bar for the title
        top_bar = FloatLayout(
            size_hint=(1, 0.15),
            pos_hint={'top': 1}
        )
        
        with top_bar.canvas.before:
            Color(0.05, 0.15, 0.05, 1)
            top_bar.bg_rect = Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(pos=lambda instance, value: setattr(top_bar.bg_rect, 'pos', instance.pos))
        top_bar.bind(size=lambda instance, value: setattr(top_bar.bg_rect, 'size', instance.size))
        
        # Title in the top bar
        title = Label(
            text='MINECRAFT\nServer Status Checker',
            font_name='Minecraft',
            font_size='24sp',
            bold=True,
            color=(0.3, 1, 0.3, 1),
            size_hint=(1, 1),
            halign='center',
            valign='middle'
        )
        title.bind(size=title.setter('text_size'))
        top_bar.add_widget(title)
        
        root.add_widget(top_bar)
        
        # Input field
        self.input = TextInput(
            hint_text='Enter server IP:PORT (e.g., mc.hypixel.net)',
            multiline=False,
            font_name='Minecraft',
            font_size='16sp',
            size_hint=(1, None),
            height=60,
            background_color=(0.1, 0.1, 0.1, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.3, 1, 0.3, 1),
            hint_text_color=(0.5, 0.5, 0.5, 1),
            padding=[15, 15]
        )
        
        # Check button
        self.check_btn = GlowingButton(
            text='CHECK SERVER',
            font_name='Minecraft',
            font_size='20sp',
            bold=True,
            size_hint=(1, None),
            height=70,
            color=(1, 1, 1, 1)
        )
        self.check_btn.bind(on_press=self.check_server)
        
        # Monitor toggle button
        self.monitor_btn = GlowingButton(
            text='START MONITORING',
            font_name='Minecraft',
            font_size='18sp',
            bold=True,
            size_hint=(1, None),
            height=60,
            color=(1, 1, 1, 1)
        )
        self.monitor_btn.bind(on_press=self.toggle_monitoring)
        
        # Status card - now takes more space
        self.status_card = StatusCard()
        
        # Add widgets to main content
        main_content.add_widget(self.input)
        main_content.add_widget(self.check_btn)
        main_content.add_widget(self.monitor_btn)
        main_content.add_widget(self.status_card)
        
        root.add_widget(main_content)
        
        # Request Android permissions
        if platform == 'android':
            self.request_permissions()
        
        return root
    
    def update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
    
    def request_permissions(self):
        """Request Android permissions"""
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.INTERNET,
                Permission.ACCESS_NETWORK_STATE,
                Permission.POST_NOTIFICATIONS
            ])
        except Exception as e:
            print(f"Permission error: {e}")
    
    def parse_address(self):
        """Parse server address and port"""
        addr = self.input.text.strip()
        if not addr:
            return False
        
        if ':' in addr:
            parts = addr.split(':')
            self.server_addr = parts[0]
            try:
                self.server_port = int(parts[1])
            except:
                self.server_port = 25565
        else:
            self.server_addr = addr
            self.server_port = 25565
        
        return True
    
    def check_server(self, instance):
        """Single server check"""
        if not self.parse_address():
            self.status_card.set_offline('Please enter a server address')
            return
        
        self.check_btn.disabled = True
        self.check_btn.text = 'CHECKING...'
        
        thread = threading.Thread(target=self.check_server_thread)
        thread.daemon = True
        thread.start()
    
    def check_server_thread(self):
        """Check server in background thread"""
        result = MinecraftServerPinger.ping(self.server_addr, self.server_port)
        Clock.schedule_once(lambda dt: self.update_status(result), 0)
    
    def update_status(self, result):
        """Update UI with server status"""
        if result['online']:
            self.status_card.set_online(
                result['version'],
                result['players_online'],
                result['players_max'],
                result['motd']
            )
        else:
            self.status_card.set_offline(result.get('error', 'Server unreachable'))
        
        self.check_btn.disabled = False
        self.check_btn.text = 'CHECK SERVER'
    
    def toggle_monitoring(self, instance):
        """Toggle server monitoring"""
        if not self.monitoring:
            if not self.parse_address():
                self.status_card.set_offline('Please enter a server address')
                return
            
            self.monitoring = True
            self.monitor_btn.text = 'STOP MONITORING'
            with self.monitor_btn.canvas.before:
                Color(0.5, 0, 0, 1)
            
            Clock.schedule_interval(self.monitor_check, 60)
            self.monitor_check(0)
        else:
            self.monitoring = False
            self.monitor_btn.text = 'START MONITORING'
            with self.monitor_btn.canvas.before:
                Color(0, 0.5, 0, 1)
            
            Clock.unschedule(self.monitor_check)
    
    def monitor_check(self, dt):
        """Periodic monitoring check"""
        if not self.monitoring:
            return
        
        thread = threading.Thread(target=self.monitor_thread)
        thread.daemon = True
        thread.start()
    
    def monitor_thread(self):
        """Monitor server and send notifications on status change"""
        result = MinecraftServerPinger.ping(self.server_addr, self.server_port)
        
        current_status = "ONLINE" if result['online'] else "OFFLINE"
        
        # Update UI
        Clock.schedule_once(lambda dt: self.update_status(result), 0)
        
        # Send notification if status changed
        if self.last_status is not None and self.last_status != current_status:
            if result['online']:
                self.send_notification(
                    "Server ONLINE",
                    f"{self.server_addr}:{self.server_port}\nPlayers: {result['players_online']}/{result['players_max']}"
                )
            else:
                self.send_notification(
                    "Server OFFLINE",
                    f"{self.server_addr}:{self.server_port}\nServer is now unreachable"
                )
        
        self.last_status = current_status
    
    def send_notification(self, title, message):
        """Send Android notification"""
        try:
            notification.notify(
                title=title,
                message=message,
                app_name='MC Status',
                timeout=10
            )
        except Exception as e:
            print(f"Notification error: {e}")
    
    def on_pause(self):
        """Allow app to run in background"""
        return True
    
    def on_resume(self):
        """Handle app resume"""
        pass


if __name__ == '__main__':
    MCStatusApp().run()