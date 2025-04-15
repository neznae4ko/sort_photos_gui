import os
import shutil
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from PIL import Image
from PIL.ExifTags import TAGS

class PhotoProcessor:
    def __init__(self, root):
        self.root = root
        self.setup_ui()
        self.setup_tags()
        self.setup_keyboard_shortcuts()

    def setup_ui(self):
        self.root.title("Анализатор и сортировщик фотографий")
        self.root.geometry("1000x800")

        # Конфигурация
        self.config = {
            'default_source': r"D:\from\",
            'default_target': r"D:\to\)",
            'default_camera': "Kodak",
            'font': ('Arial', 10),
            'colors': {
                'normal': 'black',
                'error': 'red',
                'match': '#CC0000',
                'header': '#0066CC',
                'success': '#009933',
                'warning': '#FF8800',
                'model': 'black'  # New tag for camera model
            }
        }

        # Создание элементов интерфейса
        self.create_source_frame()
        self.create_target_frame()
        self.create_camera_input()
        self.create_action_buttons()
        self.create_log_panel()

    def setup_tags(self):
        for tag_name, color in self.config['colors'].items():
            self.log_text.tag_config(tag_name, foreground=color)
            if tag_name in ('match', 'header', 'model'):  # Include 'model' tag
                self.log_text.tag_config(tag_name, font=('Arial', 10, 'bold'))

    def setup_keyboard_shortcuts(self):
        # Обработка Ctrl+C в английской раскладке
        self.root.bind('<Control-c>', self.copy_from_log)
        # Обработка Ctrl+C в русской раскладке (Ctrl+C)
        self.root.bind('<Control-C>', self.copy_from_log)

    def copy_from_log(self, event=None):
        try:
            # Получаем выделенный текст
            selected_text = self.log_text.get("sel.first", "sel.last")
            if selected_text:
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)
        except tk.TclError:
            # Если ничего не выделено, копируем весь текст
            all_text = self.log_text.get("1.0", tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(all_text)
        return "break"  # Предотвращаем стандартное поведение

    def create_source_frame(self):
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(frame, text="Папка источник:").pack(anchor='w')

        self.source_entry = tk.Entry(frame, font=self.config['font'])
        self.source_entry.pack(fill=tk.X, pady=2)
        self.source_entry.insert(0, self.config['default_source'])

        tk.Button(
            frame,
            text="Выбрать...",
            command=lambda: self.browse_folder(self.source_entry)
        ).pack(pady=5)

    def create_target_frame(self):
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(frame, text="Папка назначения:").pack(anchor='w')

        self.target_entry = tk.Entry(frame, font=self.config['font'])
        self.target_entry.pack(fill=tk.X, pady=2)
        self.target_entry.insert(0, self.config['default_target'])

        tk.Button(
            frame,
            text="Выбрать...",
            command=lambda: self.browse_folder(self.target_entry)
        ).pack(pady=5)

    def create_camera_input(self):
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(frame, text="Название камеры для поиска:").pack(anchor='w')

        self.camera_entry = tk.Entry(frame, font=self.config['font'])
        self.camera_entry.pack(fill=tk.X, pady=2)
        self.camera_entry.insert(0, self.config['default_camera'])

        tk.Label(frame, text="(регистр не учитывается)").pack(anchor='w')

    def create_action_buttons(self):
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        self.analyze_btn = tk.Button(
            btn_frame,
            text="АНАЛИЗИРОВАТЬ",
            command=self.process_photos,
            bg="#4CAF50",
            fg="white",
            font=('Arial', 11, 'bold'),
            padx=20,
            pady=8
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=10)

        self.move_btn = tk.Button(
            btn_frame,
            text="ПЕРЕМЕСТИТЬ",
            command=self.move_matching_photos,
            bg="#FF9800",
            fg="white",
            font=('Arial', 11, 'bold'),
            padx=20,
            pady=8
        )
        self.move_btn.pack(side=tk.LEFT, padx=10)

    def create_log_panel(self):
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.log_text = tk.Text(
            frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="white",
            font=self.config['font'],
            padx=5,
            pady=5
        )

        # Добавляем контекстное меню
        self.setup_context_menu()

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)

    def setup_context_menu(self):
        # Создаем контекстное меню
        self.context_menu = tk.Menu(self.log_text, tearoff=0)
        self.context_menu.add_command(label="Копировать", command=self.copy_from_log)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Очистить лог", command=self.clear_log)

        # Привязываем меню к правой кнопке мыши
        self.log_text.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def browse_folder(self, entry_widget):
        folder = filedialog.askdirectory()
        if folder:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, folder)

    def process_photos(self):
        source = self.source_entry.get()
        target = self.target_entry.get()
        camera_name = self.camera_entry.get().strip()

        if not camera_name:
            messagebox.showwarning("Ошибка", "Введите название камеры для поиска")
            return

        if not self.validate_paths(source, target):
            return

        self.clear_log()
        self.log_message(f"=== ПОИСК ФОТОГРАФИЙ КАМЕРЫ: {camera_name.upper()} ===", 'header')

        photo_count = 0
        match_count = 0

        for root, _, files in os.walk(source):
            for file in files:
                if self.is_image_file(file):
                    photo_count += 1
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, source)

                    try:
                        model = self.get_camera_model(file_path)
                        if model:
                            if camera_name.lower() in model.lower():
                                self.log_message(f"{rel_path} - ", 'match', end='')
                                self.log_message(f"{model}", 'model')  # Log model in bold
                                match_count += 1
                            else:
                                self.log_message(f"{rel_path} - ", 'normal', end='')
                                self.log_message(f"{model}", 'model')  # Log model in bold
                        else:
                            self.log_message(f"{rel_path} - Модель не определена", 'normal')
                    except Exception as e:
                        self.log_message(f"ОШИБКА: {rel_path} - {str(e)}", 'error')

        self.log_message("\n=== РЕЗУЛЬТАТЫ ===", 'header')
        self.log_message(f"Всего фотографий: {photo_count}", 'header')
        self.log_message(f"Найдено совпадений: {match_count}", 'match' if match_count > 0 else 'normal')

    def move_matching_photos(self):
        source = self.source_entry.get()
        target = self.target_entry.get()
        camera_name = self.camera_entry.get().strip()

        if not camera_name:
            messagebox.showwarning("Ошибка", "Введите название камеры для перемещения")
            return

        if not self.validate_paths(source, target):
            return

        target = os.path.join(target, camera_name)  # Добавляем папку с названием камеры

        if not messagebox.askyesno(
            "Подтверждение",
            f"Вы уверены, что хотите переместить все фото камеры '{camera_name}' из:\n{source}\nв:\n{target}?"
        ):
            return

        self.clear_log()
        self.log_message(f"=== ПЕРЕМЕЩЕНИЕ ФОТО КАМЕРЫ: {camera_name.upper()} ===", 'header')

        moved_count = 0
        errors_count = 0

        for root, _, files in os.walk(source):
            for file in files:
                if self.is_image_file(file):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, source)

                    try:
                        model = self.get_camera_model(file_path)
                        if model and camera_name.lower() in model.lower():
                            # Сохраняем структуру папок внутри папки камеры
                            target_rel_path = os.path.join(camera_name, rel_path)
                            full_target_path = os.path.join(self.target_entry.get(), target_rel_path)

                            os.makedirs(os.path.dirname(full_target_path), exist_ok=True)

                            shutil.move(file_path, full_target_path)
                            self.log_message(f"Перемещено: {rel_path}", 'success')
                            moved_count += 1
                    except Exception as e:
                        self.log_message(f"ОШИБКА перемещения {rel_path}: {str(e)}", 'error')
                        errors_count += 1

        self.log_message("\n=== ИТОГИ ПЕРЕМЕЩЕНИЯ ===", 'header')
        self.log_message(f"Успешно перемещено: {moved_count}", 'success')
        self.log_message(f"Ошибок: {errors_count}", 'error' if errors_count > 0 else 'normal')

        if moved_count > 0:
            messagebox.showinfo("Готово", f"Перемещено {moved_count} фотографий камеры {camera_name}")

    def validate_paths(self, source, target):
        if not os.path.isdir(source):
            self.log_message(f"ОШИБКА: Папка источника не существует!\n{source}", 'error')
            return False
        if not os.path.isdir(target):
            self.log_message(f"ОШИБКА: Целевая папка не существует!\n{target}", 'error')
            return False
        return True

    def is_image_file(self, filename):
        #return filename.lower().endswith(('.jpg', '.jpeg', '.tiff', '.png', '.nef', '.cr2', '.arw', '.raf', 'raw', ))
        return filename.lower().endswith(('.jpg', '.jpeg' ))


    def get_camera_model(self, file_path):
        try:
            with Image.open(file_path) as img:
                exif = img._getexif()
                if exif:
                    for tag_id, value in exif.items():
                        if TAGS.get(tag_id) == "Model" and value:
                            return str(value).strip()
        except:
            return None
        return None

    def log_message(self, message, tag='normal', end='\n'):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message, tag)
        if end:
            self.log_text.insert(tk.END, end)
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)
        self.root.update()

    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoProcessor(root)
    root.mainloop()
