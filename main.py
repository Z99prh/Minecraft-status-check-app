
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.utils import platform
from mcstatus import JavaServer
from plyer import notification
import threading
import traceback

# Register Minecraft-style font (needs font file in project)
LabelBase.register(name="Minecraft", fn_regular="minecraft.ttf")

class StatusApp(App):
    def build(self):
        self.server_addr = ""
        self.last_status = None  # ONLINE / OFFLINE
        self.monitoring = False

        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        self.title = Label(
            text="[b]Minecraft Server Status[/b]",
            font_name="Minecraft",
            font_size='26sp',
            markup=True,
            color=(0.2, 1, 0.2, 1)
        )

        self.input = TextInput(
            hint_text="Enter server IP:PORT (e.g., mc.hypixel.net:25565)",
            multiline=False,
            font_size='18sp',
            size_hint_y=None,
            height=50,
            background_color=(0.05, 0.05, 0.05, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0, 1, 0, 1)
        )

        self.btn = Button(
            text="START MONITORING",
            font_name="Minecraft",
            font_size='18sp',
            size_hint_y=None,
            height=60,
            background_color=(0, 0.4, 0, 1)
        )
        self.btn.bind(on_press=self.toggle_monitor)

        self.output = Label(
            text="Enter server address and tap START",
            font_name="Minecraft",
            font_size='18sp',
            markup=True,
            color=(1, 1, 1, 1)
        )

        self.layout.add_widget(self.title)
        self.layout.add_widget(self.input)
        self.layout.add_widget(self.btn)
        self.layout.add_widget(self.output)

        # Request notification permissions on Android 13+
        if platform == 'android':
            self.request_android_permissions()

        return self.layout

    def request_android_permissions(self):
        """Request necessary Android permissions"""
        from android.permissions import request_permissions, Permission
        
        # Request POST_NOTIFICATIONS permission (required for Android 13+)
        def callback(permissions, grant_results):
            if all(grant_results):
                print("All permissions granted")
            else:
                print("Some permissions denied")
        
        request_permissions([
            Permission.POST_NOTIFICATIONS,
            Permission.INTERNET,
            Permission.ACCESS_NETWORK_STATE
        ], callback)

    def toggle_monitor(self, instance):
        """Start or stop monitoring"""
        if not self.monitoring:
            self.server_addr = self.input.text.strip()
            if not self.server_addr:
                self.output.text = "[color=ff0000]Please enter a server address[/color]"
                return
            
            self.monitoring = True
            self.btn.text = "STOP MONITORING"
            self.btn.background_color = (0.6, 0, 0, 1)
            self.output.text = "[color=ffff00][b]Starting monitoring...[/b][/color]"
            
            # Start monitoring with Clock (will continue even when app is backgrounded with service)
            Clock.schedule_interval(self.check_server_scheduled, 120)
            self.check_server_scheduled(0)
            
            # Start Android foreground service if on Android
            if platform == 'android':
                self.start_foreground_service()
        else:
            self.stop_monitoring()

    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        self.btn.text = "START MONITORING"
        self.btn.background_color = (0, 0.4, 0, 1)
        self.output.text = "[color=ffff00]Monitoring stopped[/color]"
        Clock.unschedule(self.check_server_scheduled)
        
        # Stop Android foreground service if on Android
        if platform == 'android':
            self.stop_foreground_service()

    def start_foreground_service(self):
        """Start Android foreground service for background monitoring"""
        try:
            from android import mActivity
            from jnius import autoclass
            
            PythonService = autoclass('org.kivy.android.PythonService')
            PythonService.mService.setAutoRestartService(True)
            
            print("Foreground service started")
        except Exception as e:
            print(f"Could not start foreground service: {e}")
            traceback.print_exc()

    def stop_foreground_service(self):
        """Stop Android foreground service"""
        try:
            from jnius import autoclass
            
            PythonService = autoclass('org.kivy.android.PythonService')
            PythonService.mService.setAutoRestartService(False)
            
            print("Foreground service stopped")
        except Exception as e:
            print(f"Could not stop foreground service: {e}")

    def check_server_scheduled(self, dt):
        """Called by Clock - runs check in background thread"""
        if not self.monitoring:
            return
        
        # Run the actual check in a background thread to avoid freezing UI
        thread = threading.Thread(target=self.check_server_thread)
        thread.daemon = True
        thread.start()

    def check_server_thread(self):
        """Check server status in background thread"""
        try:
            server = JavaServer.lookup(self.server_addr)
            status = server.status()
            current = "ONLINE"

            # Update UI from main thread using Clock
            Clock.schedule_once(lambda dt: self.update_ui_online(status), 0)

            if self.last_status != current:
                self.notify_change("ONLINE", f"Players {status.players.online}/{status.players.max}")
                self.last_status = current

        except Exception as e:
            current = "OFFLINE"
            error_msg = str(e)
            
            # Log the error for debugging
            print(f"Server check failed: {error_msg}")
            traceback.print_exc()
            
            # Update UI from main thread using Clock
            Clock.schedule_once(lambda dt: self.update_ui_offline(error_msg), 0)

            if self.last_status != current:
                self.notify_change("OFFLINE", "Server not reachable")
                self.last_status = current

    def update_ui_online(self, status):
        """Update UI with online status (called from main thread)"""
        self.output.text = (
            "[color=00ff00][b]ONLINE[/b][/color]\n"
            f"Version: {status.version.name}\n"
            f"Players: {status.players.online}/{status.players.max}\n"
            f"Latency: {status.latency:.1f}ms"
        )

    def update_ui_offline(self, error_msg):
        """Update UI with offline status (called from main thread)"""
        self.output.text = (
            "[color=ff0000][b]OFFLINE[/b][/color]\n"
            f"[size=14sp]{error_msg}[/size]"
        )

    def notify_change(self, status, extra=""):
        """Send notification when status changes"""
        try:
            notification.notify(
                title=f"MC Server {status}",
                message=f"{self.server_addr}\n{extra}",
                app_name="MC Status",
                timeout=10
            )
        except Exception as e:
            print(f"Notification failed: {e}")

    def on_pause(self):
        """Allow app to pause (continue running in background)"""
        return True

    def on_resume(self):
        """Handle app resume"""
        pass

if __name__ == '__main__':
    StatusApp().run()
