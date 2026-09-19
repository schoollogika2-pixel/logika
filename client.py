
import customtkinter as ctk
import tkinter as tk

import socket
import threading
import json
import base64
import io

from datetime import datetime
from tkinter import filedialog, messagebox


# ============================================================
# НАСТРОЙКИ
# ============================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ------------------------------------------------------------
# СЕРВЕР
# ------------------------------------------------------------

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080


# Якщо сервер на іншому ПК:
#
# SERVER_HOST = "192.168.1.100"


# ============================================================
# КОЛЬОРИ
# ============================================================

COLORS = {
    "background": "#0B0D12",
    "sidebar": "#11141B",
    "sidebar_light": "#181D27",
    "panel": "#151923",
    "input": "#202632",
    "message": "#1B2230",

    "accent": "#7C5CFC",
    "accent_hover": "#6847E8",

    "pink": "#FF4FA3",
    "blue": "#42A5FF",
    "green": "#36D399",
    "yellow": "#FFD166",

    "text": "#FFFFFF",
    "secondary": "#8E98A8",
    "border": "#292F3D"
}


class LogiTalk(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("LogiTalk")
        self.geometry("1200x720")
        self.minsize(950, 600)

        # ----------------------------------------------------
        # КОРИСТУВАЧ
        # ----------------------------------------------------

        self.username = "User"

        self.profile_open = False
        self.current_chat = "Загальний чат"

        # ----------------------------------------------------
        # SOCKET
        # ----------------------------------------------------

        self.client_socket = None
        self.connected = False

        # Буфер для отриманих даних
        self.receive_buffer = b""

        # Прапорець роботи програми
        self.running = True

        # ----------------------------------------------------
        # ЧАТИ
        # ----------------------------------------------------

        self.chats = [
            ("💬", "Загальний чат"),
            ("👨‍💻", "Розробники"),
            ("🎨", "Дизайн"),
            ("🎮", "Gaming"),
            ("🎵", "Музика")
        ]

        # ----------------------------------------------------
        # ЗБЕРІГАЄМО ФОТО,
        # ЩОБ PYTHON НЕ ВИДАЛЯВ ЇХ З ПАМ'ЯТІ
        # ----------------------------------------------------

        self.photo_references = []

        # ----------------------------------------------------
        # ВІКНО
        # ----------------------------------------------------

        self.configure(
            fg_color=COLORS["background"]
        )

        self.protocol(
            "WM_DELETE_WINDOW",
            self.close_app
        )

        self.show_login()

    # ========================================================
    # LOGIN
    # ========================================================

    def show_login(self):

        self.login = ctk.CTkFrame(
            self,
            width=450,
            height=500,
            corner_radius=28,
            fg_color=COLORS["sidebar"],
            border_width=1,
            border_color=COLORS["border"]
        )

        self.login.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        ctk.CTkLabel(
            self.login,
            text="💬",
            font=ctk.CTkFont(size=60)
        ).pack(
            pady=(45, 5)
        )

        ctk.CTkLabel(
            self.login,
            text="LogiTalk",
            font=ctk.CTkFont(
                size=36,
                weight="bold"
            )
        ).pack()

        ctk.CTkLabel(
            self.login,
            text="Твій простір для спілкування",
            text_color=COLORS["secondary"],
            font=ctk.CTkFont(size=14)
        ).pack(
            pady=(5, 35)
        )

        self.login_name = ctk.CTkEntry(
            self.login,
            width=330,
            height=50,
            corner_radius=14,
            placeholder_text="Введіть своє ім'я",
            fg_color=COLORS["input"],
            border_color=COLORS["border"]
        )

        self.login_name.pack(
            pady=10
        )

        ctk.CTkButton(
            self.login,
            text="Увійти →",
            width=330,
            height=50,
            corner_radius=14,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont(
                size=15,
                weight="bold"
            ),
            command=self.login_user
        ).pack(
            pady=20
        )

        ctk.CTkLabel(
            self.login,
            text="LogiTalk • Chat everywhere",
            text_color=COLORS["secondary"],
            font=ctk.CTkFont(size=11)
        ).pack(
            pady=15
        )

        self.login_name.bind(
            "",
            lambda event: self.login_user()
        )

    # ========================================================
    # LOGIN USER
    # ========================================================

    def login_user(self):

        name = self.login_name.get().strip()

        if not name:
            name = "User"

        # Символ | і перенос рядка нам не потрібні
        name = name.replace("|", "")
        name = name.replace("\n", "")

        self.username = name

        self.login.destroy()

        self.create_interface()

        # Підключення до сервера
        self.connect_to_server()

    # ========================================================
    # ПІДКЛЮЧЕННЯ ДО СЕРВЕРА
    # ========================================================

    def connect_to_server(self):

        try:

            self.client_socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            self.client_socket.connect(
                (
                    SERVER_HOST,
                    SERVER_PORT
                )
            )

            self.connected = True

            self.update_connection_status(
                True
            )

            print(
                f"Підключено до сервера "
                f"{SERVER_HOST}:{SERVER_PORT}"
            )

            # Окремий потік для отримання
            self.receive_thread = threading.Thread(
                target=self.receive_messages,
                daemon=True
            )

            self.receive_thread.start()

        except Exception as e:

            self.connected = False

            print(
                "Помилка підключення:",
                e
            )

            self.update_connection_status(
                False
            )

    # ========================================================
    # ОТРИМАННЯ ПОВІДОМЛЕНЬ
    # ========================================================

    def receive_messages(self):

        while self.running and self.connected:

            try:

                data = self.client_socket.recv(
                    65536
                )

                if not data:
                    break

                self.receive_buffer += data

                # Шукаємо завершення JSON-повідомлення
                while b"\n" in self.receive_buffer:

                    raw_message, self.receive_buffer = (
                        self.receive_buffer.split(
                            b"\n",
                            1
                        )
                    )

                    if not raw_message:
                        continue

                    try:

                        message = json.loads(
                            raw_message.decode(
                                "utf-8"
                            )
                        )

                        # Передаємо обробку GUI
                        # у головний потік
                        self.after(
                            0,
                            lambda msg=message:
                            self.process_message(msg)
                        )

                    except json.JSONDecodeError as e:

                        print(
                            "Помилка JSON:",
                            e
                        )

            except Exception as e:

                print(
                    "Помилка отримання:",
                    e
                )

                break

        self.connected = False

        if self.running:

            self.after(
                0,
                lambda:
                self.update_connection_status(False)
            )

    # ========================================================
    # ОБРОБКА ОТРИМАНОГО ПОВІДОМЛЕННЯ
    # ========================================================

    def process_message(self, message):

        message_type = message.get(
            "type"
        )

        sender = message.get(
            "username",
            "User"
        )

        time = message.get(
            "time",
            datetime.now().strftime("%H:%M")
        )

        # ----------------------------------------------------
        # ТЕКСТ
        # ----------------------------------------------------

        if message_type == "text":

            text = message.get(
                "text",
                ""
            )

            self.add_message(
                sender=sender,
                text=text,
                time=time
            )

        # ----------------------------------------------------
        # ФОТО
        # ----------------------------------------------------

        elif message_type == "image":

            image_data = message.get(
                "image",
                ""
            )

            self.add_message(
                sender=sender,
                image_base64=image_data,
                time=time
            )

    # ========================================================
    # СТАТУС
    # ========================================================

    def update_connection_status(
        self,
        connected
    ):

        if hasattr(
            self,
            "online_label"
        ):

            if connected:

                self.online_label.configure(
                    text="●  Сервер онлайн",
                    text_color=COLORS["green"]
                )

            else:

                self.online_label.configure(
                    text="○  Сервер недоступний",
                    text_color=COLORS["pink"]
                )

        if hasattr(
            self,
            "online_label_chat"
        ):

            if connected:

                self.online_label_chat.configure(
                    text="●  Сервер онлайн",
                    text_color=COLORS["green"]
                )

            else:

                self.online_label_chat.configure(
                    text="○  Сервер недоступний",
                    text_color=COLORS["pink"]
                )

    # ========================================================
    # ВІДПРАВКА JSON НА СЕРВЕР
    # ========================================================

    def send_json(self, data):

        if not self.connected:

            messagebox.showerror(
                "Помилка",
                "Немає підключення до сервера."
            )

            return False

        try:

            # JSON -> bytes
            json_data = json.dumps(
                data,
                ensure_ascii=False
            )

            # Додаємо \n як роздільник
            json_data += "\n"

            self.client_socket.sendall(
                json_data.encode(
                    "utf-8"
                )
            )

            return True

        except Exception as e:

            print(
                "Помилка відправки:",
                e
            )

            self.connected = False

            self.update_connection_status(
                False
            )

            return False

    # ========================================================
    # ВІДПРАВКА ТЕКСТОВОГО ПОВІДОМЛЕННЯ
    # ========================================================

    def send_message(self):

        if not hasattr(
            self,
            "message_entry"
        ):
            return

        text = self.message_entry.get().strip()

        if not text:
            return

        now = datetime.now().strftime(
            "%H:%M"
        )

        message = {
            "type": "text",
            "username": self.username,
            "text": text,
            "time": now
        }

        if self.send_json(message):

            # Сервер не повертає повідомлення
            # його відправнику.
            #
            # Тому показуємо своє локально.

            self.add_message(
                sender=self.username,
                text=text,
                time=now
            )

            self.message_entry.delete(
                0,
                "end"
            )

    # ========================================================
    # ВИБІР ФОТО
    # ========================================================

    def choose_image(self):

        if not self.connected:

            messagebox.showerror(
                "Помилка",
                "Спочатку підключіться до сервера."
            )

            return

        file_path = filedialog.askopenfilename(
            title="Виберіть зображення",
            filetypes=[
                (
                    "Зображення",
                    "*.png *.gif *.ppm *.pgm"
                ),
                (
                    "PNG",
                    "*.png"
                ),
                (
                    "GIF",
                    "*.gif"
                ),
                (
                    "Усі файли",
                    "*.*"
                )
            ]
        )

        if not file_path:
            return

        self.send_image(
            file_path
        )

    # ========================================================
    # ВІДПРАВКА ФОТО
    # ========================================================

    def send_image(self, file_path):

        try:

            # ------------------------------------------------
            # ВІДКРИВАЄМО ФОТО ЧЕРЕЗ IO
            # ------------------------------------------------

            with open(
                file_path,
                "rb"
            ) as image_file:

                image_bytes = image_file.read()

            # ------------------------------------------------
            # BYTES -> BASE64
            # ------------------------------------------------

            encoded_image = base64.b64encode(
                image_bytes
            ).decode(
                "ascii"
            )

            now = datetime.now().strftime(
                "%H:%M"
            )

            message = {
                "type": "image",
                "username": self.username,
                "image": encoded_image,
                "time": now
            }

            # ------------------------------------------------
            # ВІДПРАВЛЯЄМО НА СЕРВЕР
            # ------------------------------------------------

            if self.send_json(message):

                # Показуємо фото собі
                self.add_message(
                    sender=self.username,
                    image_base64=encoded_image,
                    time=now
                )

        except Exception as e:

            messagebox.showerror(
                "Помилка",
                f"Не вдалося відправити фото:\n{e}"
            )

    # ========================================================
    # ДОДАВАННЯ ПОВІДОМЛЕННЯ
    # ========================================================

    def add_message(
        self,
        sender,
        text=None,
        image_base64=None,
        time=""
    ):

        if not hasattr(
            self,
            "messages"
        ):
            return

        # ----------------------------------------------------
        # ГОЛОВНИЙ FRAME ПОВІДОМЛЕННЯ
        # ----------------------------------------------------

        message_frame = ctk.CTkFrame(
            self.messages,
            fg_color=COLORS["message"],
            corner_radius=15
        )

        message_frame.pack(
            fill="x",
            pady=5,
            padx=5
        )

        # ----------------------------------------------------
        # АВАТАР
        # ----------------------------------------------------

        avatar = ctk.CTkLabel(
            message_frame,
            text="👤",
            font=ctk.CTkFont(size=27),
            width=45
        )

        avatar.pack(
            side="left",
            padx=(12, 5),
            pady=10,
            anchor="n"
        )

        # ----------------------------------------------------
        # CONTENT FRAME
        # ----------------------------------------------------

        content = ctk.CTkFrame(
            message_frame,
            fg_color="transparent"
        )

        content.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(5, 15),
            pady=10
        )

        # ----------------------------------------------------
        # ВЕРХНІЙ РЯДОК:
        # ІМ'Я + ЧАС
        # ----------------------------------------------------

        header = ctk.CTkFrame(
            content,
            fg_color="transparent"
        )

        header.pack(
            fill="x"
        )

        ctk.CTkLabel(
            header,
            text=sender,
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            )
        ).pack(
            side="left"
        )

        ctk.CTkLabel(
            header,
            text=time,
            text_color=COLORS["secondary"],
            font=ctk.CTkFont(size=10)
        ).pack(
            side="left",
            padx=10
        )

        # ----------------------------------------------------
        # ТЕКСТ
        # ----------------------------------------------------

        if text is not None:

            ctk.CTkLabel(
                content,
                text=text,
                text_color="#D9DEE8",
                font=ctk.CTkFont(size=13),
                wraplength=700,
                justify="left"
            ).pack(
                anchor="w",
                pady=(4, 0)
            )

        # ----------------------------------------------------
        # ФОТО
        # ----------------------------------------------------

        if image_base64:

            self.add_image_to_message(
                content,
                image_base64
            )

        # ----------------------------------------------------
        # АВТОМАТИЧНИЙ СКРОЛ ВНИЗ
        # ----------------------------------------------------

        self.after(
            100,
            self.scroll_to_bottom
        )

    # ========================================================
    # ДОДАВАННЯ ФОТО В ПОВІДОМЛЕННЯ
    # ========================================================

    def add_image_to_message(
        self,
        parent,
        image_base64
    ):

        try:

            # ------------------------------------------------
            # BASE64 -> BYTES
            # ------------------------------------------------

            image_bytes = base64.b64decode(
                image_base64
            )

            # ------------------------------------------------
            # BYTES -> IO
            # ------------------------------------------------

            image_stream = io.BytesIO(
                image_bytes
            )

            # ------------------------------------------------
            # IO -> TK PHOTOIMAGE
            # ------------------------------------------------

            # PhotoImage може читати PNG/GIF
            image = tk.PhotoImage(
                data=base64.b64encode(
                    image_stream.getvalue()
                )
            )

            # ------------------------------------------------
            # ЗМЕНШЕННЯ ВЕЛИКОГО ФОТО
            # ------------------------------------------------

            width = image.width()
            height = image.height()

            max_width = 500
            max_height = 350

            if (
                width > max_width
                or height > max_height
            ):

                factor_x = (
                    width / max_width
                )

                factor_y = (
                    height / max_height
                )

                factor = max(
                    factor_x,
                    factor_y
                )

                subsample = max(
                    1,
                    int(factor)
                )

                image = image.subsample(
                    subsample,
                    subsample
                )

            # ------------------------------------------------
            # ЗБЕРІГАЄМО ПОСИЛАННЯ НА ФОТО
            # ------------------------------------------------

            self.photo_references.append(
                image
            )

            # ------------------------------------------------
            # LABEL З ФОТО
            # ------------------------------------------------

            image_label = ctk.CTkLabel(
                parent,
                text="",
                image=image
            )

            image_label.pack(
                anchor="w",
                pady=(7, 2)
            )

        except Exception as e:

            ctk.CTkLabel(
                parent,
                text="🖼️ Не вдалося відобразити зображення",
                text_color=COLORS["pink"]
            ).pack(
                anchor="w",
                pady=(5, 0)
            )

            print(
                "Помилка відображення фото:",
                e
            )

    # ========================================================
    # СКРОЛ
    # ========================================================

    def scroll_to_bottom(self):

        try:

            self.messages._parent_canvas.yview_moveto(
                1.0
            )

        except:
            pass

    # ========================================================
    # ЛЕВА ПАНЕЛЬ
    # ========================================================

    def create_interface(self):

        self.sidebar = ctk.CTkFrame(
            self,
            width=280,
            corner_radius=0,
            fg_color=COLORS["sidebar"]
        )

        self.sidebar.pack(
            side="left",
            fill="y"
        )

        self.sidebar.pack_propagate(False)

        # ----------------------------------------------------
        # TOP
        # ----------------------------------------------------

        top = ctk.CTkFrame(
            self.sidebar,
            height=80,
            fg_color=COLORS["sidebar"]
        )

        top.pack(fill="x")
        top.pack_propagate(False)

        self.profile_button = ctk.CTkButton(
            top,
            text="👤  " + self.username,
            height=45,
            corner_radius=12,
            fg_color=COLORS["sidebar_light"],
            hover_color=COLORS["border"],
            anchor="w",
            command=self.toggle_profile
        )

        self.profile_button.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(15, 5),
            pady=17
        )

        ctk.CTkButton(
            top,
            text="+",
            width=42,
            height=42,
            corner_radius=12,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont(
                size=22,
                weight="bold"
            ),
            command=self.new_chat
        ).pack(
            side="right",
            padx=(0, 15),
            pady=18
        )

        # ----------------------------------------------------
        # PROFILE
        # ----------------------------------------------------

        self.profile_panel = ctk.CTkFrame(
            self.sidebar,
            fg_color=COLORS["panel"],
            corner_radius=15,
            border_width=1,
            border_color=COLORS["border"]
        )

        # ----------------------------------------------------
        # SEARCH
        # ----------------------------------------------------

        self.search = ctk.CTkEntry(
            self.sidebar,
            height=42,
            corner_radius=12,
            placeholder_text="🔎  Пошук чатів...",
            fg_color=COLORS["input"],
            border_width=0
        )

        self.search.pack(
            fill="x",
            padx=15,
            pady=(5, 15)
        )

        self.search.bind(
            "",
            lambda event:
            self.filter_chats()
        )

        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        ctk.CTkLabel(
            self.sidebar,
            text="ВАШІ ЧАТИ",
            text_color=COLORS["secondary"],
            font=ctk.CTkFont(
                size=11,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 8)
        )

        # ----------------------------------------------------
        # CHAT SCROLL
        # ----------------------------------------------------

        self.chat_scroll = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["accent"]
        )

        self.chat_scroll.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=(0, 10)
        )

        self.chat_buttons = []

        self.build_chat_list()

        # ----------------------------------------------------
        # BOTTOM
        # ----------------------------------------------------

        bottom = ctk.CTkFrame(
            self.sidebar,
            height=65,
            fg_color=COLORS["sidebar_light"],
            corner_radius=0
        )

        bottom.pack(
            fill="x",
            side="bottom"
        )

        self.online_label = ctk.CTkLabel(
            bottom,
            text="○  Підключення...",
            text_color=COLORS["yellow"],
            font=ctk.CTkFont(size=12)
        )

        self.online_label.pack(
            side="left",
            padx=(18, 5)
        )

        ctk.CTkButton(
            bottom,
            text="⚙",
            width=40,
            height=40,
            fg_color="transparent",
            hover_color=COLORS["border"],
            command=self.show_settings
        ).pack(
            side="right",
            padx=10
        )

        # ----------------------------------------------------
        # MAIN
        # ----------------------------------------------------

        self.main = ctk.CTkFrame(
            self,
            fg_color=COLORS["background"],
            corner_radius=0
        )

        self.main.pack(
            side="right",
            fill="both",
            expand=True
        )

        self.show_chat()

    # ========================================================
    # СПИСОК ЧАТІВ
    # ========================================================

    def build_chat_list(
        self,
        filtered=None
    ):

        for widget in self.chat_scroll.winfo_children():
            widget.destroy()

        self.chat_buttons = []

        chats = (
            filtered
            if filtered is not None
            else self.chats
        )

        for icon, name in chats:

            selected = (
                name == self.current_chat
            )

            button = ctk.CTkButton(
                self.chat_scroll,
                text=f"{icon}   {name}",
                height=48,
                corner_radius=12,
                fg_color=(
                    COLORS["accent"]
                    if selected
                    else "transparent"
                ),
                hover_color=COLORS["sidebar_light"],
                anchor="w",
                font=ctk.CTkFont(size=14),
                command=lambda n=name:
                self.open_chat(n)
            )

            button.pack(
                fill="x",
                pady=3
            )

            self.chat_buttons.append(
                button
            )

    # ========================================================
    # ПОШУК
    # ========================================================

    def filter_chats(self):

        query = (
            self.search
            .get()
            .lower()
            .strip()
        )

        if not query:

            self.build_chat_list()

            return

        filtered = [
            chat
            for chat in self.chats
            if query in chat[1].lower()
        ]

        self.build_chat_list(
            filtered
        )

    # ========================================================
    # ПРОФІЛЬ
    # ========================================================

    def toggle_profile(self):

        if self.profile_open:

            self.profile_panel.pack_forget()

            self.profile_open = False

            return

        self.profile_panel.pack(
            fill="x",
            padx=12,
            pady=(0, 10),
            before=self.search
        )

        for widget in self.profile_panel.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.profile_panel,
            text="ПРОФІЛЬ",
            text_color=COLORS["secondary"],
            font=ctk.CTkFont(
                size=10,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=15,
            pady=(15, 5)
        )

        ctk.CTkLabel(
            self.profile_panel,
            text="👤  " + self.username,
            font=ctk.CTkFont(
                size=16,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=15
        )

        ctk.CTkLabel(
            self.profile_panel,
            text="Змінити ім'я:",
            text_color=COLORS["secondary"]
        ).pack(
            anchor="w",
            padx=15,
            pady=(12, 3)
        )

        name_entry = ctk.CTkEntry(
            self.profile_panel,
            height=38,
            corner_radius=10,
            placeholder_text="Нове ім'я"
        )

        name_entry.pack(
            fill="x",
            padx=15
        )

        ctk.CTkButton(
            self.profile_panel,
            text="Зберегти",
            height=38,
            corner_radius=10,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=lambda:
            self.change_name(name_entry)
        ).pack(
            fill="x",
            padx=15,
            pady=12
        )

        self.profile_open = True

    # ========================================================
    # ЗМІНА ІМЕНІ
    # ========================================================

    def change_name(self, entry):

        new_name = entry.get().strip()

        if not new_name:
            return

        new_name = new_name.replace(
            "|",
            ""
        )

        new_name = new_name.replace(
            "\n",
            ""
        )

        self.username = new_name

        self.profile_button.configure(
            text="👤  " + self.username
        )

        self.profile_open = False

        self.profile_panel.pack_forget()

    # ========================================================
    # ВІДКРИТТЯ ЧАТУ
    # ========================================================

    def open_chat(self, name):

        self.current_chat = name

        self.build_chat_list()

        self.show_chat()

    # ========================================================
    # ВІКНО ЧАТУ
    # ========================================================

    def show_chat(self):

        for widget in self.main.winfo_children():
            widget.destroy()

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        header = ctk.CTkFrame(
            self.main,
            height=80,
            fg_color=COLORS["sidebar"],
            corner_radius=0
        )

        header.pack(
            fill="x"
        )

        header.pack_propagate(
            False
        )

        ctk.CTkLabel(
            header,
            text="💬  " + self.current_chat,
            font=ctk.CTkFont(
                size=21,
                weight="bold"
            )
        ).pack(
            side="left",
            padx=25
        )

        self.online_label_chat = ctk.CTkLabel(
            header,
            text="○  Підключення...",
            text_color=COLORS["yellow"],
            font=ctk.CTkFont(size=12)
        )

        self.online_label_chat.pack(
            side="right",
            padx=25
        )

        if self.connected:

            self.online_label_chat.configure(
                text="●  Сервер онлайн",
                text_color=COLORS["green"]
            )

        # ----------------------------------------------------
        # MESSAGE AREA
        # ----------------------------------------------------

        self.messages = ctk.CTkScrollableFrame(
            self.main,
            fg_color="transparent"
        )

        self.messages.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=15
        )

        # ----------------------------------------------------
        # INPUT
        # ----------------------------------------------------

        input_frame = ctk.CTkFrame(
            self.main,
            height=80,
            fg_color=COLORS["sidebar"]
        )

        input_frame.pack(
            fill="x"
        )

        input_frame.pack_propagate(
            False
        )

        # ----------------------------------------------------
        # КНОПКА ФОТО
        # ----------------------------------------------------

        ctk.CTkButton(
            input_frame,
            text="📷",
            width=50,
            height=48,
            corner_radius=15,
            fg_color=COLORS["sidebar_light"],
            hover_color=COLORS["border"],
            font=ctk.CTkFont(size=20),
            command=self.choose_image
        ).pack(
            side="left",
            padx=(20, 5),
            pady=15
        )

        # ----------------------------------------------------
        # INPUT
        # ----------------------------------------------------

        self.message_entry = ctk.CTkEntry(
            input_frame,
            height=48,
            corner_radius=15,
            fg_color=COLORS["input"],
            border_width=0,
            placeholder_text="Напишіть повідомлення..."
        )

        self.message_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=5,
            pady=15
        )

        # ----------------------------------------------------
        # SEND
        # ----------------------------------------------------

        ctk.CTkButton(
            input_frame,
            text="➤",
            width=55,
            height=48,
            corner_radius=15,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont(size=20),
            command=self.send_message
        ).pack(
            side="right",
            padx=(5, 20),
            pady=15
        )

        self.message_entry.bind(
            "",
            lambda event:
            self.send_message()
        )

    # ========================================================
    # НОВИЙ ЧАТ
    # ========================================================

    def new_chat(self):

        new_name = (
            f"Новий чат "
            f"{len(self.chats) + 1}"
        )

        self.chats.append(
            ("💬", new_name)
        )

        self.current_chat = new_name

        self.build_chat_list()

        self.show_chat()

    # ========================================================
    # НАСТРОЙКИ
    # ========================================================

    def show_settings(self):

        for widget in self.main.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.main,
            text="⚙  Налаштування",
            font=ctk.CTkFont(
                size=30,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=40,
            pady=(40, 10)
        )

        ctk.CTkLabel(
            self.main,
            text="Налаштуйте LogiTalk під себе",
            text_color=COLORS["secondary"]
        ).pack(
            anchor="w",
            padx=40
        )

        theme = ctk.CTkFrame(
            self.main,
            height=80,
            corner_radius=15,
            fg_color=COLORS["sidebar"]
        )

        theme.pack(
            fill="x",
            padx=40,
            pady=30
        )

        ctk.CTkLabel(
            theme,
            text="🌙  Темна тема",
            font=ctk.CTkFont(
                size=15,
                weight="bold"
            )
        ).pack(
            side="left",
            padx=20
        )

        switch = ctk.CTkSwitch(
            theme,
            text=""
        )

        switch.select()

        switch.pack(
            side="right",
            padx=20
        )

    # ========================================================
    # ЗАКРИТТЯ
    # ========================================================

    def close_app(self):

        self.running = False
        self.connected = False

        if self.client_socket:

            try:
                self.client_socket.shutdown(
                    socket.SHUT_RDWR
                )
            except:
                pass

            try:
                self.client_socket.close()
            except:
                pass

        self.destroy()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    app = LogiTalk()

    app.mainloop()
