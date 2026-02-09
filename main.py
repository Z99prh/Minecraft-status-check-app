
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.text import LabelBase
from mcstatus import JavaServer
from plyer import notification

# Register Minecraft-style font (needs font file in project)
LabelBase.register(name="Minecraft", fn_regular="minecraft.ttf")

class StatusApp(App):
    def build(self):
        self.server_addr = ""
        self.last_status = None  # ONLINE / OFFLINE

        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        self.title = Label(
            text="[b]Minecraft Server Status[/b]",
            font_name="Minecraft",
            font_size='26sp',
            markup=True,
            color=(0.2, 1, 0.2, 1)
        )

        self.input = TextInput(
            hint_text="Enter server IP:PORT",
            multiline=False,
            font_size='18sp',
            size_hint_y=None,
            height=50,
            background_color=(0.05, 0.05, 0.05, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0, 1, 0, 1)
        )

        self.btn = Button(
            text="START FOREGROUND MONITOR",
            font_name="Minecraft",
            font_size='18sp',
            size_hint_y=None,
            height=60,
            background_color=(0, 0.4, 0, 1)
        )
        self.btn.bind(on_press=self.start_monitor)

        self.output = Label(
            text="Waiting...",
            font_name="Minecraft",
            font_size='18sp',
            markup=True,
            color=(1, 1, 1, 1)
        )

        self.layout.add_widget(self.title)
        self.layout.add_widget(self.input)
        self.layout.add_widget(self.btn)
        self.layout.add_widget(self.output)

        return self.layout

    def start_monitor(self, instance):
        self.server_addr = self.input.text.strip()
        if not self.server_addr:
            return
        self.output.text = "[b]Monitoring started[/b]"
        Clock.unschedule(self.check_server)
        Clock.schedule_interval(self.check_server, 120)
        self.check_server(0)

    def notify_change(self, status, extra=""):
        notification.notify(
            title=f"MC Server {status}",
            message=f"{self.server_addr}\n{extra}",
            timeout=6
        )

    def check_server(self, dt):
        try:
            server = JavaServer.lookup(self.server_addr)
            status = server.status()
            current = "ONLINE"

            self.output.text = (
                "[color=00ff00][b]ONLINE[/b][/color]\n"
                f"Version: {status.version.name}\n"
                f"Players: {status.players.online}/{status.players.max}"
            )

            if self.last_status != current:
                self.notify_change("ONLINE", f"Players {status.players.online}/{status.players.max}")
                self.last_status = current

        except Exception:
            current = "OFFLINE"
            self.output.text = "[color=ff0000][b]OFFLINE[/b][/color]"

            if self.last_status != current:
                self.notify_change("OFFLINE", "Server not reachable")
                self.last_status = current

StatusApp().run()
