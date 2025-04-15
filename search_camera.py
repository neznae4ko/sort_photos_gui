import os
import shutil
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from PIL import Image, ImageDraw, ImageTk
from PIL.ExifTags import TAGS
import threading
import time

class PhotoProcessor:
    def __init__(self, main_window):
        self.main_window = main_window
        self.initialize_user_interface()
        self.configure_text_tags()
        self.setup_keyboard_shortcuts()
        self.processing_paused = False
        self.processing_stopped = False
        self.analysis_thread = None
        self.unique_camera_models = set()

    def initialize_user_interface(self):
        self.main_window.title("Анализатор и сортировщик фотографий")
        self.main_window.geometry("1600x800")

        self.application_settings = {
            'default_source_directory': r"D:\source_directory",
            'default_target_directory': r"D:\target_directory",
            'default_camera_name': "Sony",
            'font_style': ('Arial', 10),
            'color_scheme': {
                'normal_text': 'black',
                'error_text': 'red',
                'match_text': '#33cc33',
                'header_text': '#0066CC',
                'success_text': '#009933',
                'warning_text': '#FF8800',
                'camera_model_text': 'black'
            }
        }

        self.create_source_target_directory_controls()
        self.create_camera_processing_controls()
        self.create_log_display_panel()

    def configure_text_tags(self):
        for tag_name, color in self.application_settings['color_scheme'].items():
            self.log_display_text.tag_config(tag_name, foreground=color)
            if tag_name in ('match_text', 'header_text', 'camera_model_text'):
                self.log_display_text.tag_config(tag_name, font=('Arial', 10, 'bold'))

    def setup_keyboard_shortcuts(self):
        self.main_window.bind('<Control-c>', self.copy_selected_text)
        self.main_window.bind('<Control-a>', self.select_all_text)
        self.main_window.bind('<Control-v>', self.paste_from_clipboard)
        self.main_window.bind('<Control-C>', self.copy_selected_text)
        self.main_window.bind('<Control-A>', self.select_all_text)
        self.main_window.bind('<Control-V>', self.paste_from_clipboard)

    def copy_selected_text(self, event=None):
        try:
            focused_widget = self.main_window.focus_get()
            if isinstance(focused_widget, tk.Entry):
                focused_widget.event_generate("<<Copy>>")
            elif isinstance(focused_widget, tk.Text):
                if focused_widget.tag_ranges("sel"):
                    focused_widget.event_generate("<<Copy>>")
        except tk.TclError:
            pass

    def select_all_text(self, event=None):
        try:
            focused_widget = self.main_window.focus_get()
            if isinstance(focused_widget, tk.Entry):
                focused_widget.selection_range(0, tk.END)
            elif isinstance(focused_widget, tk.Text):
                focused_widget.tag_add("sel", "1.0", tk.END)
        except tk.TclError:
            pass

    def paste_from_clipboard(self, event=None):
        try:
            focused_widget = self.main_window.focus_get()
            if isinstance(focused_widget, tk.Entry):
                focused_widget.event_generate("<<Paste>>")
            elif isinstance(focused_widget, tk.Text):
                focused_widget.event_generate("<<Paste>>")
        except tk.TclError:
            pass

    def create_source_target_directory_controls(self):
        control_frame = tk.Frame(self.main_window)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(control_frame, text="Исходная папка с фотографиями:").grid(row=0, column=0, padx=5, sticky='e')

        self.source_directory_entry = tk.Entry(control_frame, font=self.application_settings['font_style'])
        self.source_directory_entry.grid(row=0, column=1, padx=5, sticky='ew')
        self.source_directory_entry.insert(0, self.application_settings['default_source_directory'])

        tk.Button(
            control_frame,
            text="Выбрать...",
            command=lambda: self.select_directory(self.source_directory_entry)
        ).grid(row=0, column=2, padx=5)

        tk.Label(control_frame, text="→").grid(row=0, column=3, padx=5)

        tk.Label(control_frame, text="Целевая папка для перемещения:").grid(row=0, column=4, padx=5, sticky='e')

        self.target_directory_entry = tk.Entry(control_frame, font=self.application_settings['font_style'])
        self.target_directory_entry.grid(row=0, column=5, padx=5, sticky='ew')
        self.target_directory_entry.insert(0, self.application_settings['default_target_directory'])

        tk.Button(
            control_frame,
            text="Выбрать...",
            command=lambda: self.select_directory(self.target_directory_entry)
        ).grid(row=0, column=6, padx=5)

        control_frame.grid_columnconfigure(1, weight=1)
        control_frame.grid_columnconfigure(5, weight=1)

    def create_camera_processing_controls(self):
        control_frame = tk.Frame(self.main_window)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # Обновленная цветовая палитра
        self.color_palette = {
            'analyze': {'bg': '#6B8E23', 'fg': '#FFFFFF', 'active_bg': '#556B2F'},  # Оливковый
            'move': {'bg': '#4682B4', 'fg': '#FFFFFF', 'active_bg': '#3A6B8F'},      # Стальной синий
            'pause': {'bg': '#DAA520', 'fg': '#FFFFFF', 'active_bg': '#B8860B'},    # Золотистый
            'stop': {'bg': '#CD5C5C', 'fg': '#FFFFFF', 'active_bg': '#A52A2A'},     # Индийский красный
            'default': {'bg': '#E0E0E0', 'fg': '#333333', 'active_bg': '#CCCCCC'}
        }

        tk.Label(control_frame, text="Название камеры для поиска:").grid(row=0, column=0, padx=5, sticky='e')

        self.camera_name_entry = tk.Entry(control_frame, font=self.application_settings['font_style'])
        self.camera_name_entry.grid(row=0, column=1, padx=5, sticky='ew')
        self.camera_name_entry.insert(0, self.application_settings['default_camera_name'])

        # Кнопка анализа с иконкой "play"
        self.analyze_icon = self.create_control_icon("play")
        self.analyze_button = tk.Button(
            control_frame,
            image=self.analyze_icon,
            command=self.start_photo_analysis,
            bg=self.color_palette['analyze']['bg'],
            fg=self.color_palette['analyze']['fg'],
            activebackground=self.color_palette['analyze']['active_bg'],
            font=('Arial', 11, 'bold'),
            padx=12,
            pady=6,
            text=" Анализировать",
            compound=tk.LEFT,
            relief=tk.GROOVE,
            borderwidth=2
        )
        self.analyze_button.grid(row=0, column=2, padx=5)

        # Остальные кнопки остаются без изменений
        self.move_icon = self.create_control_icon("move")
        self.move_button = tk.Button(
            control_frame,
            image=self.move_icon,
            command=self.move_matching_photos,
            bg=self.color_palette['move']['bg'],
            fg=self.color_palette['move']['fg'],
            activebackground=self.color_palette['move']['active_bg'],
            font=('Arial', 11, 'bold'),
            padx=12,
            pady=6,
            text=" Переместить",
            compound=tk.LEFT,
            relief=tk.GROOVE,
            borderwidth=2
        )
        self.move_button.grid(row=0, column=3, padx=5)

        self.pause_icon = self.create_control_icon("pause")
        self.pause_button = tk.Button(
            control_frame,
            image=self.pause_icon,
            command=self.toggle_processing_pause,
            bg=self.color_palette['pause']['bg'],
            fg=self.color_palette['pause']['fg'],
            activebackground=self.color_palette['pause']['active_bg'],
            font=('Arial', 11, 'bold'),
            padx=12,
            pady=6,
            text=" Пауза",
            compound=tk.LEFT,
            relief=tk.GROOVE,
            borderwidth=2
        )
        self.pause_button.grid(row=0, column=4, padx=5)

        self.stop_icon = self.create_control_icon("stop")
        self.stop_button = tk.Button(
            control_frame,
            image=self.stop_icon,
            command=self.stop_photo_processing,
            bg=self.color_palette['stop']['bg'],
            fg=self.color_palette['stop']['fg'],
            activebackground=self.color_palette['stop']['active_bg'],
            font=('Arial', 11, 'bold'),
            padx=12,
            pady=6,
            text=" Стоп",
            compound=tk.LEFT,
            relief=tk.GROOVE,
            borderwidth=2
        )
        self.stop_button.grid(row=0, column=5, padx=5)

        control_frame.grid_columnconfigure(1, weight=1)





    
    
    def create_control_icon(self, icon_type):
        icon_size = 30
        background_color = "#f0f0f0"
        icon_image = Image.new("RGB", (icon_size, icon_size), background_color)
        icon_draw = ImageDraw.Draw(icon_image)
        
        if icon_type == "search":
            icon_color = "#FFFFFF"
            circle_radius = icon_size//3
            center_x, center_y = icon_size//2, icon_size//2
            icon_draw.ellipse(
                (center_x-circle_radius, center_y-circle_radius,
                 center_x+circle_radius, center_y+circle_radius),
                outline=icon_color, width=3
            )
            handle_length = icon_size//3
            icon_draw.line(
                (center_x, center_y,
                 center_x+handle_length, center_y+handle_length),
                fill=icon_color, width=3
            )
        
        elif icon_type == "move":
            icon_color = "#FFFFFF"
            arrow_size = icon_size//3
            margin = icon_size//4
            icon_draw.polygon(
                [(margin, margin),
                 (icon_size-margin, icon_size//2),
                 (margin, icon_size-margin)],
                fill=icon_color
            )
        
        elif icon_type == "pause":
            icon_color = "#FFFFFF"
            bar_width = icon_size//8
            gap = icon_size//10
            icon_draw.rectangle(
                [(icon_size//2 - gap - bar_width, icon_size//4),
                 (icon_size//2 - gap, 3*icon_size//4)],
                fill=icon_color
            )
            icon_draw.rectangle(
                [(icon_size//2 + gap, icon_size//4),
                 (icon_size//2 + gap + bar_width, 3*icon_size//4)],
                fill=icon_color
            )
        
        elif icon_type == "stop":
            icon_color = "#FFFFFF"
            margin = icon_size//4
            icon_draw.rectangle(
                [(margin, margin),
                 (icon_size-margin, icon_size-margin)],
                fill=icon_color
            )

        return ImageTk.PhotoImage(icon_image)







    def create_log_display_panel(self):
        main_panel = tk.Frame(self.main_window)
        main_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        tk.Label(main_panel, text="Журнал обработки:").grid(row=0, column=0, sticky='w')
        tk.Label(main_panel, text="Обнаруженные модели камер:").grid(row=0, column=2, sticky='w')

        log_frame = tk.Frame(main_panel)
        log_frame.grid(row=1, column=0, sticky='nsew', padx=(0, 5))

        self.log_display_text = tk.Text(
            log_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="white",
            font=self.application_settings['font_style'],
            padx=5,
            pady=5
        )
        self.log_display_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        log_scrollbar = tk.Scrollbar(log_frame, command=self.log_display_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_display_text['yscrollcommand'] = log_scrollbar.set

        camera_list_frame = tk.Frame(main_panel)
        camera_list_frame.grid(row=1, column=2, sticky='nsew', padx=(5, 0))

        self.camera_models_display = tk.Text(
            camera_list_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="white",
            font=self.application_settings['font_style'],
            padx=5,
            pady=5,
            width=30
        )
        self.camera_models_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        camera_scrollbar = tk.Scrollbar(camera_list_frame, command=self.camera_models_display.yview)
        camera_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.camera_models_display['yscrollcommand'] = camera_scrollbar.set

        self.camera_models_display.bind("<Button-1>", self.select_camera_model_from_list)

        main_panel.grid_rowconfigure(1, weight=1)
        main_panel.grid_columnconfigure(0, weight=1)
        main_panel.grid_columnconfigure(2, weight=0)

    def select_directory(self, entry_widget):
        selected_directory = filedialog.askdirectory()
        if selected_directory:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, selected_directory)

    def start_photo_analysis(self):
        if self.analysis_thread and self.analysis_thread.is_alive():
            messagebox.showwarning("Внимание", "Анализ уже выполняется.")
            return
        self.processing_paused = False
        self.processing_stopped = False
        self.analysis_thread = threading.Thread(target=self.process_photo_collection)
        self.analysis_thread.start()

    def toggle_processing_pause(self):
        self.processing_paused = not self.processing_paused
        if self.processing_paused:
            self.pause_button.config(text=" Продолжить")
        else:
            self.pause_button.config(text=" Пауза")

    def stop_photo_processing(self):
        self.processing_stopped = True
        self.processing_paused = False
        self.pause_button.config(text=" Пауза")

    def process_photo_collection(self):
        source_directory = self.source_directory_entry.get()
        target_directory = self.target_directory_entry.get()
        camera_name_to_find = self.camera_name_entry.get().strip()

        if not camera_name_to_find:
            messagebox.showwarning("Ошибка", "Пожалуйста, введите название камеры для поиска")
            return

        if not self.validate_directory_paths(source_directory, target_directory):
            return

        self.clear_log_messages()
        self.add_log_message(f"=== ПОИСК ФОТОГРАФИЙ КАМЕРЫ: {camera_name_to_find.upper()} ===", 'header_text')

        total_photos_processed = 0
        matching_photos_found = 0

        for root_directory, _, files in os.walk(source_directory):
            while self.processing_paused:
                time.sleep(0.1)
            if self.processing_stopped:
                self.add_log_message("\n=== АНАЛИЗ ПРЕРВАН ===", 'error_text')
                return
            for filename in files:
                if self.is_valid_image_file(filename):
                    total_photos_processed += 1
                    full_file_path = os.path.join(root_directory, filename)
                    relative_file_path = os.path.relpath(full_file_path, source_directory)

                    try:
                        camera_model = self.extract_camera_model(full_file_path)
                        if camera_model:
                            if camera_model not in self.unique_camera_models:
                                self.unique_camera_models.add(camera_model)
                                self.add_camera_model_to_list(camera_model)
                            if camera_name_to_find.lower() in camera_model.lower():
                                self.add_log_message(f"{relative_file_path} - ", 'match_text', end='')
                                self.add_log_message(f"{camera_model}", 'camera_model_text')
                                matching_photos_found += 1
                            else:
                                self.add_log_message(f"{relative_file_path} - ", 'normal_text', end='')
                                self.add_log_message(f"{camera_model}", 'camera_model_text')
                        else:
                            self.add_log_message(f"{relative_file_path} - Модель камеры не определена", 'normal_text')
                    except Exception as error:
                        self.add_log_message(f"ОШИБКА: {relative_file_path} - {str(error)}", 'error_text')

        self.add_log_message("\n=== РЕЗУЛЬТАТЫ АНАЛИЗА ===", 'header_text')
        self.add_log_message(f"Всего обработано фотографий: {total_photos_processed}", 'header_text')
        status_tag = 'match_text' if matching_photos_found > 0 else 'normal_text'
        self.add_log_message(f"Найдено соответствующих фотографий: {matching_photos_found}", status_tag)
    
    def move_matching_photos(self):
        source_directory = self.source_directory_entry.get()
        base_target_directory = self.target_directory_entry.get()
        camera_name_to_move = self.camera_name_entry.get().strip()

        if not camera_name_to_move:
            messagebox.showwarning("Ошибка", "Пожалуйста, введите название камеры для перемещения")
            return

        if not self.validate_directory_paths(source_directory, base_target_directory):
            return

        # Проверяем существование папки и добавляем "!" при необходимости
        target_directory = os.path.join(base_target_directory, camera_name_to_move)
        counter = 1
        while os.path.exists(target_directory):
            target_directory = os.path.join(base_target_directory, f"{camera_name_to_move}_{counter}")
            counter += 1

        confirmation_message = (
            f"Вы уверены, что хотите переместить все фотографии камеры '{camera_name_to_move}'?\n"
            f"Из: {source_directory}\n"
            f"В: {target_directory}"
        )
        if not messagebox.askyesno("Подтверждение", confirmation_message):
            return

        self.clear_log_messages()
        self.add_log_message(f"=== ПЕРЕМЕЩЕНИЕ ФОТОГРАФИЙ КАМЕРЫ: {camera_name_to_move.upper()} ===", 'header_text')
        self.add_log_message(f"Фотографии будут перемещены в: {target_directory}", 'header_text')

        successfully_moved_count = 0
        error_count = 0

        for root_directory, _, files in os.walk(source_directory):
            for filename in files:
                if self.is_valid_image_file(filename):
                    full_file_path = os.path.join(root_directory, filename)
                    relative_file_path = os.path.relpath(full_file_path, source_directory)

                    try:
                        camera_model = self.extract_camera_model(full_file_path)
                        if camera_model and camera_name_to_move.lower() in camera_model.lower():
                            # Сохраняем структуру подпапок внутри целевой папки
                            target_relative_path = os.path.join(os.path.basename(target_directory), relative_file_path)
                            full_target_path = os.path.join(base_target_directory, target_relative_path)

                            os.makedirs(os.path.dirname(full_target_path), exist_ok=True)

                            shutil.move(full_file_path, full_target_path)
                            self.add_log_message(f"Успешно перемещено: {relative_file_path}", 'success_text')
                            successfully_moved_count += 1
                    except Exception as error:
                        self.add_log_message(f"ОШИБКА ПЕРЕМЕЩЕНИЯ {relative_file_path}: {str(error)}", 'error_text')
                        error_count += 1

        self.add_log_message("\n=== ИТОГИ ПЕРЕМЕЩЕНИЯ ===", 'header_text')
        self.add_log_message(f"Успешно перемещено фотографий: {successfully_moved_count}", 'success_text')
        status_tag = 'error_text' if error_count > 0 else 'normal_text'
        self.add_log_message(f"Ошибок при перемещении: {error_count}", status_tag)

        if successfully_moved_count > 0:
            messagebox.showinfo(
                "Завершено", 
                f"Успешно перемещено {successfully_moved_count} фотографий камеры {camera_name_to_move}\n"
                f"в папку: {target_directory}"
            )
 
    def validate_directory_paths(self, source_path, target_path):
        if not os.path.isdir(source_path):
            self.add_log_message(f"ОШИБКА: Исходная папка не существует!\n{source_path}", 'error_text')
            return False
        if not os.path.isdir(target_path):
            self.add_log_message(f"ОШИБКА: Целевая папка не существует!\n{target_path}", 'error_text')
            return False
        return True

    def is_valid_image_file(self, filename):
        valid_extensions = ('.jpg', '.jpeg', '.tiff', '.png', '.nef', '.cr2', '.arw', '.raf', '.raw')
        return filename.lower().endswith(valid_extensions)

    def extract_camera_model(self, image_path):
        try:
            with Image.open(image_path) as image:
                exif_data = image._getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        if TAGS.get(tag_id) == "Model" and value:
                            return str(value).strip()
        except Exception:
            return None
        return None

    def add_log_message(self, message, tag='normal_text', end='\n'):
        self.log_display_text.config(state=tk.NORMAL)
        self.log_display_text.insert(tk.END, message, tag)
        if end:
            self.log_display_text.insert(tk.END, end)
        self.log_display_text.config(state=tk.DISABLED)
        self.log_display_text.see(tk.END)
        self.main_window.update()

    def clear_log_messages(self):
        self.log_display_text.config(state=tk.NORMAL)
        self.log_display_text.delete(1.0, tk.END)
        self.log_display_text.config(state=tk.DISABLED)

    def add_camera_model_to_list(self, model_name):
        self.camera_models_display.config(state=tk.NORMAL)
        self.camera_models_display.insert(tk.END, model_name + '\n')
        self.camera_models_display.config(state=tk.DISABLED)

    def select_camera_model_from_list(self, event):
        try:
            click_position = f"@0,{event.y}"
            line_start = self.camera_models_display.index(click_position + " linestart")
            line_end = self.camera_models_display.index(click_position + " lineend")
            selected_model = self.camera_models_display.get(line_start, line_end)
            self.camera_name_entry.delete(0, tk.END)
            self.camera_name_entry.insert(0, selected_model.strip())
        except tk.TclError:
            pass

if __name__ == "__main__":
    application_window = tk.Tk()
    application = PhotoProcessor(application_window)
    application_window.mainloop()
