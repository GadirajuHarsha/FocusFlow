import time
import tkinter as tk
from tkinter import ttk, simpledialog, filedialog
import json
import os
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from gaze_client import GazeFlowClient
from PIL import Image, ImageTk

class FocusFlowApp:
    def __init__(self, root_window):
        self.root_window = root_window
        self.root_window.title("FocusFlow - Attention Tracker")

        self.actual_screen_width = self.root_window.winfo_screenwidth()
        self.actual_screen_height = self.root_window.winfo_screenheight()
        self.screen_aspect_ratio = self.actual_screen_width / self.actual_screen_height

        self._setup_styles()

        self.landing_frame = ttk.Frame(root_window, style="App.TFrame")
        self.main_app_frame = ttk.Frame(root_window, style="App.TFrame")
        self.session_overlay_window = None
        self.aoi_definition_window = None
        self.report_window_instance = None

        self.logo_photo_image = None
        self._setup_landing_page()
        self._setup_main_app_frame_widgets()

        self.show_landing_page()

        self.gz_client = GazeFlowClient()
        self.is_tracking_connection = False
        self.after_id_gaze_update = None
        self.after_id_session_timer = None

        self.aoi_list = []
        self.temp_aoi_points = []
        self.defining_aoi_type_transparent = None
        self.temp_rect_drawing_id = None

        self.session_active = False
        self.session_data_log = []
        self.session_start_time = None
        self.session_elapsed_time_str = tk.StringVar(value="00:00:00")

        self.current_report_data = None

        self.root_window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root_window.grid_rowconfigure(0, weight=1)
        self.root_window.grid_columnconfigure(0, weight=1)

    def _setup_styles(self):
        self.style = ttk.Style()

        try:
            self.default_font = ("Segoe UI", 10)
            self.header_font = ("Segoe UI", 18, "bold")
            self.status_font = ("Segoe UI", 9)
            self.overlay_font = ("Segoe UI", 10, "bold")
            self.aoi_def_font = ("Segoe UI", 12, "bold")
            self.report_header_font = ("Segoe UI", 14, "bold")
            self.report_font = ("Segoe UI", 10)
            self.report_font_bold = ("Segoe UI", 10, "bold")
            self.report_font_italic = ("Segoe UI", 10, "italic")
            self.chart_font_family = "Segoe UI"
            self.chart_font_size_small = 7
            self.chart_font_size_normal = 8
            self.chart_font_size_title = 10
        except tk.TclError:
            self.default_font = ("Calibri", 10); self.header_font = ("Calibri", 18, "bold")
            self.status_font = ("Calibri", 9); self.overlay_font = ("Calibri", 10, "bold")
            self.aoi_def_font = ("Calibri", 12, "bold"); self.report_header_font = ("Calibri", 14, "bold")
            self.report_font = ("Calibri", 10)
            self.report_font_bold = ("Calibri", 10, "bold")
            self.report_font_italic = ("Calibri", 10, "italic")
            self.chart_font_family = "Calibri"
            self.chart_font_size_small = 7
            self.chart_font_size_normal = 8
            self.chart_font_size_title = 10

        self.style.configure("TButton", font=self.default_font)
        self.style.configure("TLabel", font=self.default_font)
        self.style.configure("Header.TLabel", font=self.header_font)
        self.style.configure("Status.TLabel", font=self.status_font, anchor=tk.W)
        self.style.configure("ReportHeader.TLabel", font=self.report_header_font)
        self.style.configure("SessionOverlay.TFrame", background="#2c3e50")
        self.style.configure("SessionOverlay.TLabel", font=self.overlay_font, foreground="white", background="#2c3e50")

    def _setup_landing_page(self):
        self.landing_frame.grid_columnconfigure(0, weight=1)
        self.landing_frame.grid_rowconfigure(0, weight=1)
        self.landing_frame.grid_rowconfigure(3, weight=1)
        content_frame = ttk.Frame(self.landing_frame)
        content_frame.grid(row=1, column=0, rowspan=2)
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
            img = Image.open(logo_path)
            max_width = 200
            max_height = 100
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            self.logo_photo_image = ImageTk.PhotoImage(img)
            logo_label = ttk.Label(content_frame, image=self.logo_photo_image)
            logo_label.pack(pady=(20,10))
        except FileNotFoundError:
            print("Logo file 'logo.png' not found. Displaying text title instead.")
            ttk.Label(content_frame, text="FocusFlow", style="Header.TLabel").pack(pady=(20,10))
        except Exception as e:
            print(f"Error loading logo: {e}. Displaying text title instead.")
            ttk.Label(content_frame, text="FocusFlow", style="Header.TLabel").pack(pady=(20,10))
        ttk.Label(content_frame, text="Visualize and Understand Your Attentional Patterns", wraplength=400, justify=tk.CENTER).pack(pady=10)
        ttk.Button(content_frame, text="Get Started", command=self.show_main_app_page).pack(pady=20, ipadx=10, ipady=5)

    def _setup_main_app_frame_widgets(self):
        self.main_app_frame.grid_rowconfigure(3, weight=1)
        self.main_app_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ttk.Label(self.main_app_frame, text="Connect to GazePointer and define AOIs.", style="Status.TLabel")
        self.status_label.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,5))

        conn_frame = ttk.Frame(self.main_app_frame, style="Controls.TFrame", padding=10)
        conn_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5); conn_frame.grid_columnconfigure(0, weight=1)
        self.connect_button = ttk.Button(conn_frame, text="Connect to GazePointer", command=self.toggle_connection)
        self.connect_button.grid(row=0, column=0, pady=5)

        aoi_ctrl_frame = ttk.Frame(self.main_app_frame, style="Controls.TFrame", padding=10)
        aoi_ctrl_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        for i in range(3): aoi_ctrl_frame.grid_columnconfigure(i, weight=1)
        self.add_productive_aoi_button = ttk.Button(aoi_ctrl_frame, text="Add Productive AOI", command=lambda: self.initiate_transparent_aoi_definition("Productive"))
        self.add_productive_aoi_button.grid(row=0, column=0, padx=5, sticky="ew")
        self.add_distraction_aoi_button = ttk.Button(aoi_ctrl_frame, text="Add Distraction AOI", command=lambda: self.initiate_transparent_aoi_definition("Distraction"))
        self.add_distraction_aoi_button.grid(row=0, column=1, padx=5, sticky="ew")
        self.clear_aois_button = ttk.Button(aoi_ctrl_frame, text="Clear All AOIs", command=self.clear_all_aois)
        self.clear_aois_button.grid(row=0, column=2, padx=5, sticky="ew")

        self.canvas_aspect_frame = ttk.Frame(self.main_app_frame, style="App.TFrame")
        self.canvas_aspect_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)
        self.canvas_aspect_frame.bind("<Configure>", self.resize_preview_canvas)

        self.canvas_aoi_preview = tk.Canvas(self.canvas_aspect_frame, bg="lightgray", highlightthickness=0)
        self.canvas_aoi_preview.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.gaze_dot_preview = self.canvas_aoi_preview.create_oval(0,0,0,0, fill="#3498db", outline="#2980b9", width=2)

        session_reports_frame = ttk.Frame(self.main_app_frame, style="Controls.TFrame", padding=10)
        session_reports_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=5)
        session_reports_frame.grid_columnconfigure(0, weight=1); session_reports_frame.grid_columnconfigure(1, weight=1)
        self.start_session_button = ttk.Button(session_reports_frame, text="Start Session", command=self.start_tracking_session_ui)
        self.start_session_button.grid(row=0, column=0, pady=5, padx=(0,5), sticky="ew")
        self.view_reports_button = ttk.Button(session_reports_frame, text="View Saved Reports", command=self.load_and_show_report)
        self.view_reports_button.grid(row=0, column=1, pady=5, padx=(5,0), sticky="ew")

        self.back_to_home_button = ttk.Button(self.main_app_frame, text="< Back to Home", command=self.show_landing_page)
        self.back_to_home_button.grid(row=5, column=0, pady=(5,10), padx=10)

    def resize_preview_canvas(self, event):
        frame_width = event.width
        frame_height = event.height

        canvas_w, canvas_h = frame_width, int(frame_width / self.screen_aspect_ratio)
        if canvas_h > frame_height:
            canvas_h = frame_height
            canvas_w = int(frame_height * self.screen_aspect_ratio)
            
        canvas_w = max(20, canvas_w)
        canvas_h = max(20, canvas_h)

        self.canvas_aoi_preview.config(width=canvas_w, height=canvas_h)
        self.draw_aois_on_preview_canvas()


    def show_landing_page(self):
        self.main_app_frame.grid_remove()
        if self.session_overlay_window: self.session_overlay_window.destroy(); self.session_overlay_window = None
        if self.report_window_instance: self.report_window_instance.destroy(); self.report_window_instance = None
        self.landing_frame.grid(row=0, column=0, sticky="nsew")


    def show_main_app_page(self):
        self.landing_frame.grid_remove()
        if self.report_window_instance: self.report_window_instance.destroy(); self.report_window_instance = None
        self.main_app_frame.grid(row=0, column=0, sticky="nsew")

    def _create_session_overlay(self):
        if self.session_overlay_window: self.session_overlay_window.destroy()
        self.session_overlay_window = tk.Toplevel(self.root_window)
        self.session_overlay_window.attributes('-topmost', True)
        self.session_overlay_window.overrideredirect(True)

        overlay_frame = ttk.Frame(self.session_overlay_window, style="SessionOverlay.TFrame", padding=10)
        overlay_frame.pack(expand=True, fill='both')

        ttk.Label(overlay_frame, text="Session Active", style="SessionOverlay.TLabel").pack(pady=(0,5))
        self.overlay_timer_label = ttk.Label(overlay_frame, textvariable=self.session_elapsed_time_str, style="SessionOverlay.TLabel")
        self.overlay_timer_label.pack(pady=5)
        self.overlay_focus_indicator_canvas = tk.Canvas(overlay_frame, width=25, height=25, bg="gray", highlightthickness=0)
        self.overlay_focus_indicator_canvas.pack(pady=(5,10))
        end_button = ttk.Button(overlay_frame, text="End Session", command=self.end_tracking_session_ui)
        end_button.pack(pady=(5,0), fill=tk.X, expand=True)

        overlay_width, overlay_height = 200, 180
        x_pos = self.root_window.winfo_screenwidth() - overlay_width - 20
        y_pos = 20
        self.session_overlay_window.geometry(f"{overlay_width}x{overlay_height}+{x_pos}+{y_pos}")
        self.session_overlay_window.resizable(False, False)


    def _update_session_timer_display(self):
        if self.session_active and self.session_start_time:
            elapsed = time.time() - self.session_start_time
            self.session_elapsed_time_str.set(time.strftime("%H:%M:%S", time.gmtime(elapsed)))
            self.after_id_session_timer = self.root_window.after(1000, self._update_session_timer_display)


    def toggle_connection(self):
        if not self.gz_client.is_connected:
            if self.gz_client.connect():
                self.status_label.config(text="Connected! Receiving gaze data...")
                self.connect_button.config(text="Disconnect from GazePointer")
                self.is_tracking_connection = True
                self.update_gaze_preview_loop()
            else:
                self.status_label.config(text="Connection failed. Is GazePointer running?")
                self.gz_client.disconnect(); self.is_tracking_connection = False
        else:
            self.is_tracking_connection = False
            if self.after_id_gaze_update: self.root_window.after_cancel(self.after_id_gaze_update)
            self.gz_client.disconnect()
            self.status_label.config(text="Disconnected. Connect to start.")
            self.connect_button.config(text="Connect to GazePointer")
            if hasattr(self, 'canvas_aoi_preview'): self.canvas_aoi_preview.coords(self.gaze_dot_preview,0,0,0,0)


    def update_gaze_preview_loop(self):
        if not self.is_tracking_connection or not self.gz_client.is_connected:
            self._update_focus_indicator_colors("gray")
            return

        gaze_data = self.gz_client.receive_gaze_data()
        current_aoi_hit_type_for_session = "Outside"

        if gaze_data and 'GazeX' in gaze_data and 'GazeY' in gaze_data:
            raw_x, raw_y = gaze_data['GazeX'], gaze_data['GazeY']
            
            if hasattr(self, 'canvas_aoi_preview') and self.canvas_aoi_preview.winfo_exists():
                canvas_w, canvas_h = self.canvas_aoi_preview.winfo_width(), self.canvas_aoi_preview.winfo_height()
                if canvas_w > 1 and canvas_h > 1 :
                    preview_x = (raw_x / self.actual_screen_width) * canvas_w
                    preview_y = (raw_y / self.actual_screen_height) * canvas_h
                    dot_size = 10
                    self.canvas_aoi_preview.coords(self.gaze_dot_preview, preview_x - dot_size/2, preview_y - dot_size/2, preview_x + dot_size/2, preview_y + dot_size/2)

                    current_aoi_hit_type_for_preview = "Outside"
                    if self.aoi_list:
                        scaled_hits = []
                        for aoi in self.aoi_list:
                            r_x1_c = (aoi['rect_screen_coords'][0] / self.actual_screen_width) * canvas_w
                            r_y1_c = (aoi['rect_screen_coords'][1] / self.actual_screen_height) * canvas_h
                            r_x2_c = (aoi['rect_screen_coords'][2] / self.actual_screen_width) * canvas_w
                            r_y2_c = (aoi['rect_screen_coords'][3] / self.actual_screen_height) * canvas_h
                            if r_x1_c <= preview_x <= r_x2_c and r_y1_c <= preview_y <= r_y2_c:
                                area = (r_x2_c - r_x1_c) * (r_y2_c - r_y1_c)
                                scaled_hits.append({'type': aoi['type'], 'area': area})
                        if scaled_hits:
                            scaled_hits.sort(key=lambda item: item['area'])
                            current_aoi_hit_type_for_preview = scaled_hits[0]['type']
                    self._update_gaze_dot_preview_color(current_aoi_hit_type_for_preview)
                    if not self.session_active and self.defining_aoi_type_transparent is None:
                         self.status_label.config(text=f"Gaze (Preview): X={preview_x:.0f}, Y={preview_y:.0f} | AOI: {current_aoi_hit_type_for_preview}")


            if self.session_active:
                session_hits = []
                for aoi in self.aoi_list:
                    sx1, sy1, sx2, sy2 = aoi['rect_screen_coords']
                    if sx1 <= raw_x <= sx2 and sy1 <= raw_y <= sy2:
                        area = (sx2-sx1) * (sy2-sy1)
                        session_hits.append({'type': aoi['type'], 'area': area})
                if session_hits:
                    session_hits.sort(key=lambda item: item['area'])
                    current_aoi_hit_type_for_session = session_hits[0]['type']
                self._update_focus_indicator_colors(current_aoi_hit_type_for_session)
                self.session_data_log.append({
                    'timestamp': time.time() - self.session_start_time,
                    'raw_x': raw_x, 'raw_y': raw_y, 'aoi_status': current_aoi_hit_type_for_session
                })

        elif not self.gz_client.is_connected:
            self.status_label.config(text="Connection lost. Please check GazePointer.")
            self.connect_button.config(text="Connect to GazePointer"); self.is_tracking_connection = False
            self._update_focus_indicator_colors("gray"); self.gz_client.disconnect()
            return
        self.after_id_gaze_update = self.root_window.after(30, self.update_gaze_preview_loop)

    def _update_gaze_dot_preview_color(self, aoi_type):
        if not hasattr(self, 'canvas_aoi_preview') or not self.canvas_aoi_preview.winfo_exists(): return
        color_map = {"Productive": "green", "Distraction": "orange", "Outside": "red", "gray":"#7f8c8d"}
        fill_color = color_map.get(aoi_type, "red")
        outline_color = {"green": "#27ae60", "orange": "#f39c12", "red": "#c0392b", "gray":"#7f8c8d"}.get(aoi_type, "#c0392b")
        self.canvas_aoi_preview.itemconfig(self.gaze_dot_preview, fill=fill_color, outline=outline_color)


    def _update_focus_indicator_colors(self, aoi_type_for_session):
        if not self.session_active or not self.session_overlay_window: return
        try:
            color_map = {"Productive": "green", "Distraction": "orange", "Outside": "red", "gray":"gray"}
            indicator_color = color_map.get(aoi_type_for_session, "gray")
            if self.overlay_focus_indicator_canvas and self.overlay_focus_indicator_canvas.winfo_exists():
                 self.overlay_focus_indicator_canvas.config(bg=indicator_color)
        except tk.TclError: pass


    def initiate_transparent_aoi_definition(self, aoi_type):
        if self.session_active:
            self.status_label.config(text="Cannot define AOIs during an active session."); return
        if self.aoi_definition_window: return

        self.defining_aoi_type_transparent = aoi_type
        self.temp_aoi_points = []
        self.root_window.attributes('-alpha', 0.05)

        self.aoi_definition_window = tk.Toplevel(self.root_window)
        self.aoi_definition_window.attributes('-fullscreen', True)
        self.aoi_definition_window.attributes('-alpha', 0.25)
        self.aoi_definition_window.attributes('-topmost', True)
        self.aoi_definition_window.overrideredirect(True)

        aoi_canvas = tk.Canvas(self.aoi_definition_window, bg='gray', highlightthickness=0)
        aoi_canvas.pack(fill=tk.BOTH, expand=True)

        for existing_aoi in self.aoi_list:
            xs1, ys1, xs2, ys2 = existing_aoi['rect_screen_coords']
            color = "green" if existing_aoi['type'] == "Productive" else "orange"
            aoi_canvas.create_rectangle(xs1, ys1, xs2, ys2, outline=color, width=3)

        instruction_text = f"Defining {aoi_type} AOI: Click for TOP-LEFT corner."
        self.aoi_instruction_label = ttk.Label(aoi_canvas, text=instruction_text, font=self.aoi_def_font,
                                              background='white', foreground='black', padding=10, relief="raised")
        aoi_canvas.create_window(self.actual_screen_width / 2, 50, window=self.aoi_instruction_label, anchor=tk.CENTER)

        self.temp_rect_drawing_id = None
        aoi_canvas.bind("<ButtonPress-1>", self.on_transparent_aoi_click)
        aoi_canvas.bind("<Motion>", self.on_transparent_aoi_motion_preview)
        self.aoi_definition_window.focus_force()


    def on_transparent_aoi_motion_preview(self, event):
        if not self.aoi_definition_window or not self.defining_aoi_type_transparent or len(self.temp_aoi_points) != 1:
            return
        
        aoi_canvas = event.widget
        x1_screen, y1_screen = self.temp_aoi_points[0]
        x2_curr_screen, y2_curr_screen = event.x_root, event.y_root

        if self.temp_rect_drawing_id:
            aoi_canvas.coords(self.temp_rect_drawing_id, x1_screen, y1_screen, x2_curr_screen, y2_curr_screen)
        else:
            self.temp_rect_drawing_id = aoi_canvas.create_rectangle(
                x1_screen, y1_screen, x2_curr_screen, y2_curr_screen,
                outline="yellow", width=2, dash=(4, 2)
            )


    def on_transparent_aoi_click(self, event):
        if not self.aoi_definition_window or not self.defining_aoi_type_transparent: return
        self.temp_aoi_points.append((event.x_root, event.y_root))
        aoi_canvas = event.widget

        if len(self.temp_aoi_points) == 1:
            self.aoi_instruction_label.config(text=f"Defining {self.defining_aoi_type_transparent} AOI: Move mouse to set size, then click for BOTTOM-RIGHT corner.")
            if self.temp_rect_drawing_id: aoi_canvas.delete(self.temp_rect_drawing_id)
            x1_screen, y1_screen = self.temp_aoi_points[0]
            self.temp_rect_drawing_id = aoi_canvas.create_rectangle(x1_screen, y1_screen, x1_screen +1, y1_screen+1, outline="yellow", width=2, dash=(4,2))

        elif len(self.temp_aoi_points) == 2:
            if self.temp_rect_drawing_id: aoi_canvas.delete(self.temp_rect_drawing_id); self.temp_rect_drawing_id = None
            x1_s, y1_s = self.temp_aoi_points[0]; x2_s, y2_s = self.temp_aoi_points[1]
            fx1, fy1 = min(x1_s, x2_s), min(y1_s, y2_s)
            fx2, fy2 = max(x1_s, x2_s), max(y1_s, y2_s)

            if fx1==fx2 or fy1==fy2: self.status_label.config(text="AOI def cancelled (too small).")
            else:
                self.aoi_list.append({'rect_screen_coords': (fx1,fy1,fx2,fy2), 'type': self.defining_aoi_type_transparent})
                self.status_label.config(text=f"{self.defining_aoi_type_transparent} AOI defined.")
                self.draw_aois_on_preview_canvas()

            self.aoi_definition_window.destroy(); self.aoi_definition_window = None
            self.defining_aoi_type_transparent = None; self.temp_aoi_points = []
            self.root_window.attributes('-alpha', 1.0); self.root_window.deiconify(); self.root_window.focus_force()

    def draw_aois_on_preview_canvas(self):
        if not hasattr(self, 'canvas_aoi_preview') or not self.canvas_aoi_preview.winfo_exists(): return
        self.canvas_aoi_preview.delete("aoi_preview_rect", "aoi_preview_label")
        canvas_w, canvas_h = self.canvas_aoi_preview.winfo_width(), self.canvas_aoi_preview.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1: return

        for i, aoi in enumerate(self.aoi_list):
            xs1,ys1,xs2,ys2 = aoi['rect_screen_coords']
            xc1 = (xs1/self.actual_screen_width)*canvas_w; yc1 = (ys1/self.actual_screen_height)*canvas_h
            xc2 = (xs2/self.actual_screen_width)*canvas_w; yc2 = (ys2/self.actual_screen_height)*canvas_h
            color = "green" if aoi['type'] == "Productive" else "orange"
            self.canvas_aoi_preview.create_rectangle(xc1,yc1,xc2,yc2,outline=color,width=2,tags="aoi_preview_rect")
            self.canvas_aoi_preview.create_text(xc1+7,yc1+7,text=f"{aoi['type'][0]}{i+1}",anchor=tk.NW,fill=color,font=(self.default_font[0],8,"bold"),tags="aoi_preview_label")

    def clear_all_aois(self):
        if self.session_active: self.status_label.config(text="Cannot clear AOIs during session."); return
        self.aoi_list = []; self.draw_aois_on_preview_canvas()
        self.status_label.config(text="All AOIs cleared.")


    def start_tracking_session_ui(self):
        if not self.gz_client.is_connected: self.status_label.config(text="Not connected."); return
        if not self.aoi_list: self.status_label.config(text="No AOIs defined."); return
        if self.session_active: self.status_label.config(text="Session active."); return

        self.session_active = True; self.session_data_log = []
        self.session_start_time = time.time(); self.session_elapsed_time_str.set("00:00:00")
        self.current_report_data = None

        self.root_window.withdraw(); self._create_session_overlay(); self._update_session_timer_display()
        for btn in [self.start_session_button, self.add_productive_aoi_button, self.add_distraction_aoi_button,
                    self.clear_aois_button, self.connect_button, self.back_to_home_button, self.view_reports_button]:
            btn.config(state=tk.DISABLED)

    def end_tracking_session_ui(self, force_end=False):
        if not self.session_active and not force_end: return
        self.session_active = False
        if self.after_id_session_timer: self.root_window.after_cancel(self.after_id_session_timer)
        if self.session_overlay_window: self.session_overlay_window.destroy(); self.session_overlay_window = None

        self.root_window.deiconify(); self.show_main_app_page()
        for btn in [self.start_session_button, self.add_productive_aoi_button, self.add_distraction_aoi_button,
                    self.clear_aois_button, self.connect_button, self.back_to_home_button, self.view_reports_button]:
            btn.config(state=tk.NORMAL)

        if self.session_data_log:
            self.status_label.config(text="Session ended. Generating report...")
            self.current_report_data = self.generate_session_metrics_data()
            self._show_report_window(self.current_report_data, report_title="Current Session Report")
        else:
            self.status_label.config(text="Session ended. No data logged.")
            self.current_report_data = None

    def generate_session_metrics_data(self):
        if not self.session_data_log: return None
        report_data = {"raw_log": self.session_data_log, "report_generated_timestamp": time.time()}
        durations = []
        if len(self.session_data_log) > 1:
            for i in range(len(self.session_data_log) - 1):
                durations.append(self.session_data_log[i+1]['timestamp'] - self.session_data_log[i]['timestamp'])
            if durations: durations.append(durations[-1])
            else: durations.append(0.03)
        elif self.session_data_log: durations.append(0.03)

        time_prod,time_dist,time_out = 0,0,0
        total_time = sum(durations) if durations else 0
        report_data["session_duration"] = total_time

        for i, entry in enumerate(self.session_data_log):
            dt = durations[i]
            if entry['aoi_status'] == "Productive": time_prod += dt
            elif entry['aoi_status'] == "Distraction": time_dist += dt
            else: time_out += dt
        
        report_data["dwell_times"] = {"Productive": time_prod, "Distraction": time_dist, "Outside": time_out}
        report_data["dwell_percentages"] = {
            "Productive": (time_prod/total_time)*100 if total_time > 0 else 0,
            "Distraction": (time_dist/total_time)*100 if total_time > 0 else 0,
            "Outside": (time_out/total_time)*100 if total_time > 0 else 0
        }
        p_to_d, d_to_p = 0,0
        if len(self.session_data_log) > 1:
            for i in range(1, len(self.session_data_log)):
                prev, curr = self.session_data_log[i-1]['aoi_status'], self.session_data_log[i]['aoi_status']
                if prev=="Productive" and curr=="Distraction": p_to_d+=1
                elif prev=="Distraction" and curr=="Productive": d_to_p+=1
        report_data["transitions"] = {"P_to_D":p_to_d, "D_to_P":d_to_p}

        bout_durs = []
        cb_start = None
        for e in self.session_data_log:
            is_p = e['aoi_status'] == "Productive"; ts = e['timestamp']
            if is_p and cb_start is None: cb_start=ts
            elif not is_p and cb_start is not None:
                dur = ts - cb_start
                if dur > 0: bout_durs.append(dur)
                cb_start = None
        if cb_start is not None and self.session_data_log:
            dur = self.session_data_log[-1]['timestamp']-cb_start
            if dur > 0: bout_durs.append(dur)
        
        report_data["focus_bouts"] = {
            "count": len(bout_durs),
            "avg_duration": sum(bout_durs)/len(bout_durs) if bout_durs else 0,
            "max_duration": max(bout_durs) if bout_durs else 0,
            "durations_list": bout_durs
        }
        return report_data

    def _show_report_window(self, report_data_current, report_data_comparison=None, report_title="Session Report"):
        if self.report_window_instance and self.report_window_instance.winfo_exists():
            self.report_window_instance.destroy()

        self.report_window_instance = tk.Toplevel(self.root_window)
        self.report_window_instance.title(report_title)
        
        try:
            self.report_window_instance.state('zoomed')
        except tk.TclError:
            screen_width = self.report_window_instance.winfo_screenwidth()
            screen_height = self.report_window_instance.winfo_screenheight()
            self.report_window_instance.geometry(f"{screen_width}x{screen_height}+0+0")

        from matplotlib import rcParams
        
        is_dark_theme = False
        try:
            current_theme_mode = self.root_window.tk.call("ttk::style", "theme", "use")
            if "dark" in current_theme_mode.lower():
                is_dark_theme = True
        except tk.TclError:
            try:
                bg_test = self.style.lookup("TFrame", "background")
                if bg_test and isinstance(bg_test, str) and bg_test.startswith("#"):
                    hex_color = bg_test.lstrip('#')
                    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    if sum(rgb) < 300:
                        is_dark_theme = True
            except tk.TclError:
                pass

        default_light_bg = "#f0f0f0"
        default_dark_bg = "#333333" # Example dark background
        default_light_text = "black"
        default_dark_text = "white"

        try:
            chart_bg_color = self.style.lookup("TFrame", "background")
            if not chart_bg_color or not isinstance(chart_bg_color, str) or not chart_bg_color.startswith("#"):
                chart_bg_color = default_dark_bg if is_dark_theme else default_light_bg
        except tk.TclError:
            chart_bg_color = default_dark_bg if is_dark_theme else default_light_bg

        try:
            text_color = self.style.lookup("TLabel", "foreground")
            if not text_color or not isinstance(text_color, str):
                 text_color = default_dark_text if is_dark_theme else default_light_text
        except tk.TclError:
            text_color = default_dark_text if is_dark_theme else default_light_text


        grid_color = '#555555' if is_dark_theme else '#cccccc'
        pie_edge_color = chart_bg_color

        rcParams['font.family'] = self.chart_font_family
        rcParams['font.size'] = self.chart_font_size_normal
        rcParams['axes.titlesize'] = self.chart_font_size_title
        rcParams['axes.titleweight'] = 'bold'
        rcParams['axes.labelsize'] = self.chart_font_size_normal
        rcParams['xtick.labelsize'] = self.chart_font_size_small
        rcParams['ytick.labelsize'] = self.chart_font_size_small
        rcParams['legend.fontsize'] = self.chart_font_size_small
        rcParams['figure.facecolor'] = chart_bg_color
        rcParams['axes.facecolor'] = chart_bg_color
        rcParams['savefig.facecolor'] = chart_bg_color
        rcParams['text.color'] = text_color
        rcParams['axes.labelcolor'] = text_color
        rcParams['xtick.color'] = text_color
        rcParams['ytick.color'] = text_color
        rcParams['axes.edgecolor'] = text_color
        rcParams['grid.color'] = grid_color

        outer_frame = ttk.Frame(self.report_window_instance)
        outer_frame.pack(expand=True, fill='both')

        report_canvas = tk.Canvas(outer_frame, highlightthickness=0, bg=chart_bg_color)
        report_scrollbar_y = ttk.Scrollbar(outer_frame, orient="vertical", command=report_canvas.yview)
        report_scrollbar_x = ttk.Scrollbar(outer_frame, orient="horizontal", command=report_canvas.xview)
        report_canvas.configure(yscrollcommand=report_scrollbar_y.set, xscrollcommand=report_scrollbar_x.set)
        report_scrollbar_y.pack(side=tk.RIGHT, fill="y"); report_scrollbar_x.pack(side=tk.BOTTOM, fill="x")
        report_canvas.pack(side=tk.LEFT, fill="both", expand=True)

        main_report_frame = ttk.Frame(report_canvas, padding=20)
        report_canvas.create_window((0, 0), window=main_report_frame, anchor="nw", tags="main_report_frame")
        main_report_frame.bind("<Configure>", lambda e: report_canvas.configure(scrollregion=report_canvas.bbox("all")))

        main_report_frame.grid_columnconfigure(0, weight=1, minsize=500)
        if report_data_comparison:
             main_report_frame.grid_columnconfigure(1, weight=1, minsize=500)


        def create_report_section(parent_frame, data, title_suffix=""):
            section_style = "Card.TFrame" if "Card.TFrame" in self.style.theme_names() else "TFrame"
            section_frame = ttk.Frame(parent_frame, style=section_style, padding=(15,10), relief="solid", borderwidth=1)

            if report_data_comparison:
                col = 0 if "Current" in title_suffix or "Left" in title_suffix else 1
                section_frame.grid(row=0, column=col, sticky="nsew", padx=10, pady=10)
                parent_frame.grid_rowconfigure(0, weight=1)
            else:
                section_frame.pack(fill='both', expand=True, padx=10, pady=10)

            ttk.Label(section_frame, text=f"Summary Metrics{title_suffix}", style="ReportHeader.TLabel").pack(pady=(0, 10), fill='x', anchor='w')
            
            try:
                text_widget_bg_lookup = self.style.lookup(section_style, 'background')
                if text_widget_bg_lookup and isinstance(text_widget_bg_lookup, str) and text_widget_bg_lookup.startswith("#"):
                    text_bg = text_widget_bg_lookup
                else:
                    text_bg = str(chart_bg_color)
            except tk.TclError:
                text_bg = str(chart_bg_color)
            
            metrics_text_widget = tk.Text(section_frame, wrap=tk.WORD, height=18,
                                          font=self.report_font, relief="flat",
                                          borderwidth=0, highlightthickness=0,
                                          bg=text_bg, fg=str(text_color))
            metrics_text_widget.pack(pady=5, padx=5, fill='x')
            self.format_metrics_for_display(data, metrics_text_widget)
            metrics_text_widget.config(state=tk.DISABLED)

            ttk.Label(section_frame, text=f"Visualizations{title_suffix}", style="ReportHeader.TLabel").pack(pady=(20,10), fill='x', anchor='w')
            viz_container_frame = ttk.Frame(section_frame)
            viz_container_frame.pack(fill='both', expand=True, pady=(0,10))

            pie_frame = ttk.Frame(viz_container_frame)
            pie_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=5, pady=5)
            try:
                fig_pie = Figure(figsize=(4.8, 3.8), dpi=90, facecolor=chart_bg_color)
                ax_pie = fig_pie.add_subplot(111)
                ax_pie.set_facecolor(chart_bg_color)

                labels = ['Productive', 'Distraction', 'Outside AOIs']
                sizes = [data['dwell_times'].get('Productive',0), data['dwell_times'].get('Distraction',0), data['dwell_times'].get('Outside',0)]
                pie_colors = ['#5cb85c', '#f0ad4e', '#d9534f'] if sum(sizes) > 0 else ['#777777']*3
                valid_sizes = any(s > 0 for s in sizes)
                explode = (0.05 if data['dwell_times'].get('Productive',0) > 0 and valid_sizes else 0, 0, 0)

                if valid_sizes:
                    wedges, texts_pie, autotexts = ax_pie.pie(sizes, explode=explode, labels=None, colors=pie_colors,
                                                          autopct=lambda p: '{:.1f}%\n({:.1f}s)'.format(p, p * sum(sizes) / 100.0) if p > 1 else '',
                                                          shadow=False, startangle=120, pctdistance=0.8,
                                                          textprops={'color': "white" if is_dark_theme else "black", 'fontsize':self.chart_font_size_small, 'weight':'bold'},
                                                          wedgeprops={'edgecolor': pie_edge_color, 'linewidth': 0.5})
                    ax_pie.legend(wedges, labels, title="AOI Types", loc="center left",
                                  bbox_to_anchor=(0.98, 0, 0.5, 1), fontsize=self.chart_font_size_small,
                                  labelcolor=text_color, title_fontproperties={'size':self.chart_font_size_small, 'weight':'bold'})
                else:
                    ax_pie.text(0.5, 0.5, "No dwell data", ha='center', va='center', color=text_color)
                ax_pie.set_title('Dwell Time Distribution', color=text_color)
                fig_pie.tight_layout(pad=0.5)
                canvas_pie = FigureCanvasTkAgg(fig_pie, master=pie_frame)
                canvas_pie.draw(); canvas_pie.get_tk_widget().pack(fill='both', expand=True)
            except Exception as e:
                print(f"Error creating pie chart: {e}")
                ttk.Label(pie_frame, text=f"Err: Pie Chart ({e})", wraplength=180).pack()

            timeline_frame = ttk.Frame(viz_container_frame)
            timeline_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=5, pady=5)
            try:
                fig_timeline = Figure(figsize=(5.2, 3.8), dpi=90, facecolor=chart_bg_color)
                ax_timeline = fig_timeline.add_subplot(111)
                ax_timeline.set_facecolor(chart_bg_color)

                log = data.get("raw_log", [])
                if log and len(log) > 1 :
                    times = [entry['timestamp'] for entry in log]
                    statuses_raw = [entry['aoi_status'] for entry in log]
                    status_map = {"Productive": 2, "Distraction": 1, "Outside": 0}
                    status_plot_colors = {"Productive": pie_colors[0], "Distraction": pie_colors[1], "Outside": pie_colors[2]}
                    
                    y_coords = []
                    color_segments = []
                    
                    for i in range(len(times)):
                        y_coords.append(status_map.get(statuses_raw[i],0))
                        if i > 0:
                            color_segments.append(status_plot_colors.get(statuses_raw[i-1], pie_colors[2]))

                    if len(times) > 1:
                        for i in range(len(times) - 1):
                            ax_timeline.plot([times[i], times[i+1]], [y_coords[i], y_coords[i]], color=color_segments[i], linewidth=5)
                            if y_coords[i] != y_coords[i+1]:
                                ax_timeline.plot([times[i+1], times[i+1]], [y_coords[i], y_coords[i+1]], color=color_segments[i], linewidth=5)
                        if len(times) == len(y_coords) and len(times) > 0:
                             ax_timeline.plot([times[-1], times[-1]+0.5], [y_coords[-1], y_coords[-1]], color=status_plot_colors.get(statuses_raw[-1], pie_colors[2]), linewidth=5)


                    ax_timeline.set_yticks([0,1,2]); ax_timeline.set_yticklabels(['Outside', 'Distraction', 'Productive'])
                    ax_timeline.set_xlabel("Time (s)"); ax_timeline.set_ylabel("AOI Status")
                    ax_timeline.grid(True, axis='y', linestyle=':', linewidth=0.5, color=grid_color)
                    ax_timeline.spines['top'].set_visible(False)
                    ax_timeline.spines['right'].set_visible(False)
                    ax_timeline.spines['bottom'].set_color(text_color)
                    ax_timeline.spines['left'].set_color(text_color)
                    ax_timeline.set_ylim(-0.5, 2.5)
                else:
                    ax_timeline.text(0.5, 0.5, "Not enough data for timeline", ha='center', va='center', color=text_color)
                ax_timeline.set_title('Attention Timeline', color=text_color)
                fig_timeline.tight_layout(pad=0.5)
                canvas_timeline = FigureCanvasTkAgg(fig_timeline, master=timeline_frame)
                canvas_timeline.draw(); canvas_timeline.get_tk_widget().pack(fill='both', expand=True)
            except Exception as e:
                print(f"Error creating timeline chart: {e}")
                ttk.Label(timeline_frame, text=f"Err: Timeline ({e})", wraplength=180).pack()

        create_report_section(main_report_frame, report_data_current, " (Current Session)" if report_data_comparison else "")
        if report_data_comparison:
            create_report_section(main_report_frame, report_data_comparison, " (Compared Session)")

        buttons_frame = ttk.Frame(outer_frame)
        buttons_frame.pack(fill='x', side=tk.BOTTOM, pady=10, padx=10)
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)
        buttons_frame.grid_columnconfigure(2, weight=1)

        action_button_style = "Accent.TButton" if "Accent.TButton" in self.style.theme_names() else "TButton"

        if report_data_current == self.current_report_data and self.current_report_data is not None:
            ttk.Button(buttons_frame, text="Save This Report", style=action_button_style,
                       command=lambda d=report_data_current: self.save_report_to_json(d)).grid(row=0, column=0, padx=5, sticky="ew")
        ttk.Button(buttons_frame, text="Open & Compare Report", style=action_button_style if report_data_comparison else "TButton",
                   command=lambda current_data=report_data_current: self.load_and_compare_report(current_data)).grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(buttons_frame, text="Close Report", command=self.report_window_instance.destroy).grid(row=0, column=2, padx=5, sticky="ew")

        self.report_window_instance.update_idletasks()
        report_canvas.config(scrollregion = report_canvas.bbox("all"))

    def format_metrics_for_display(self, data, text_widget):
        if not data:
            text_widget.insert(tk.END, "No data available.")
            return

        text_widget.tag_configure("heading", font=self.report_font_bold, spacing1=5, spacing3=8, underline=True)
        text_widget.tag_configure("metric_name", font=self.report_font_bold)
        text_widget.tag_configure("metric_value", font=self.report_font)
        text_widget.tag_configure("sub_metric", font=self.report_font, lmargin1=20, lmargin2=20)
        text_widget.tag_configure("sub_value", font=self.report_font, lmargin1=20, lmargin2=20)
        text_widget.tag_configure("small_italic", font=(self.report_font[0], self.report_font[1]-1, "italic"), foreground="gray", lmargin1=20, lmargin2=20)

        text_widget.insert(tk.END, "Overall Summary\n", "heading")
        text_widget.insert(tk.END, "Session Duration: ", "metric_name")
        text_widget.insert(tk.END, f"{data.get('session_duration', 0):.2f}s\n\n", "metric_value")

        text_widget.insert(tk.END, "Dwell Time Analysis\n", "heading")
        dwell_times = data.get('dwell_times', {})
        dwell_percentages = data.get('dwell_percentages', {})
        for k_dwell, v_dwell in dwell_times.items():
            text_widget.insert(tk.END, f"{k_dwell}: ", ("sub_metric", "metric_name"))
            text_widget.insert(tk.END, f"{v_dwell:.2f}s ", "sub_value")
            text_widget.insert(tk.END, f"({dwell_percentages.get(k_dwell,0):.1f}%)\n", "small_italic")
        text_widget.insert(tk.END, "\n")

        text_widget.insert(tk.END, "Attention Shifts\n", "heading")
        transitions = data.get('transitions', {})
        for k_trans, v_trans in transitions.items():
            text_widget.insert(tk.END, f"{k_trans.replace('_',' ').title()}: ", ("sub_metric", "metric_name"))
            text_widget.insert(tk.END, f"{v_trans}\n", "sub_value")
        text_widget.insert(tk.END, "\n")

        text_widget.insert(tk.END, "Focus Bouts (Productive)\n", "heading")
        bouts = data.get('focus_bouts', {})
        text_widget.insert(tk.END, "Count: ", ("sub_metric", "metric_name"))
        text_widget.insert(tk.END, f"{bouts.get('count',0)}\n", "sub_value")
        text_widget.insert(tk.END, "Average Duration: ", ("sub_metric", "metric_name"))
        text_widget.insert(tk.END, f"{bouts.get('avg_duration',0):.2f}s\n", "sub_value")
        text_widget.insert(tk.END, "Max Duration: ", ("sub_metric", "metric_name"))
        text_widget.insert(tk.END, f"{bouts.get('max_duration',0):.2f}s\n", "sub_value")

        if "re_engagement_latency" in data:
            latency = data.get('re_engagement_latency', {})
            text_widget.insert(tk.END, "\nRe-engagement Latency\n", "heading")
            text_widget.insert(tk.END, "Average Latency: ", ("sub_metric", "metric_name"))
            text_widget.insert(tk.END, f"{latency.get('avg_latency', 'N/A'):.2f}s\n", "sub_value")
            text_widget.insert(tk.END, "Count: ", ("sub_metric", "metric_name"))
            text_widget.insert(tk.END, f"{latency.get('count', 'N/A')}\n", "sub_value")
        else:
            text_widget.insert(tk.END, "\nRe-engagement Latency: ", "heading")
            text_widget.insert(tk.END, "Not calculated.\n", "small_italic")

    def save_report_to_json(self, report_data_to_save):
        if not report_data_to_save:
            simpledialog.messagebox.showerror("Error", "No report data to save.", parent=self.report_window_instance)
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Report As...",
            initialfile=f"FocusFlow_Report_{time.strftime('%Y%m%d_%H%M%S')}.json",
            parent=self.report_window_instance
        )
        if filepath:
            try:
                with open(filepath, 'w') as f:
                    json.dump(report_data_to_save, f, indent=4)
                simpledialog.messagebox.showinfo("Success", f"Report saved to:\n{filepath}", parent=self.report_window_instance)
            except Exception as e:
                simpledialog.messagebox.showerror("Error Saving File", f"Could not save report: {e}", parent=self.report_window_instance)

    def load_and_show_report(self, report_to_compare_with=None):
        parent_window = self.report_window_instance if self.report_window_instance and self.report_window_instance.winfo_exists() else self.root_window
        filepath = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Open Report File",
            parent=parent_window
        )
        if filepath:
            try:
                with open(filepath, 'r') as f:
                    loaded_data = json.load(f)
                if not all(k in loaded_data for k in ["session_duration", "dwell_times", "raw_log"]):
                    raise ValueError("Report file is missing essential data.")

                report_filename = os.path.basename(filepath)
                if report_to_compare_with:
                    self._show_report_window(report_to_compare_with, loaded_data, report_title=f"Comparison: Current vs. {report_filename}")
                else:
                    self._show_report_window(loaded_data, report_title=f"Report: {report_filename}")

            except Exception as e:
                simpledialog.messagebox.showerror("Error Loading File", f"Could not load report: {e}", parent=parent_window)

    def load_and_compare_report(self, current_report_data_for_comparison):
        self.load_and_show_report(report_to_compare_with=current_report_data_for_comparison)

    def on_closing(self):
        if self.session_active: self.end_tracking_session_ui(force_end=True)
        if self.gz_client.is_connected:
            self.is_tracking_connection = False
            if self.after_id_gaze_update: self.root_window.after_cancel(self.after_id_gaze_update)
            if self.after_id_session_timer: self.root_window.after_cancel(self.after_id_session_timer)
            self.gz_client.disconnect()
        if self.aoi_definition_window: self.aoi_definition_window.destroy()
        if self.report_window_instance: self.report_window_instance.destroy()
        self.root_window.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    azure_tcl_path = os.path.join(os.path.dirname(__file__), "themes", "azure.tcl")
    azure_images_path = os.path.join(os.path.dirname(__file__), "themes", "azure")

    try:
        root.tk.call("lappend", "auto_path", os.path.join(os.path.dirname(__file__), "themes"))
        root.tk.call("source", azure_tcl_path)
        root.tk.call("set_theme", "dark")

    except tk.TclError as e:
        print(f"Error loading Azure theme: {e}")
        print("Ensure 'azure.tcl' and the 'azure' image asset folder are in a 'themes' subdirectory.")

    try:
        root.state('zoomed')
    except tk.TclError:
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.geometry(f"{screen_width}x{screen_height}+0+0")

    app = FocusFlowApp(root)
    root.mainloop()