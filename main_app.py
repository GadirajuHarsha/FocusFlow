import time
import tkinter as tk
from gaze_client import GazeFlowClient

class FocusFlowApp:
        def __init__(self, root_window):
                # Create the UI window
                self.root_window = root_window
                self.root_window.title("FocusFlow - Attention Tracker")

                self.actual_screen_width = self.root_window.winfo_screenwidth()
                self.actual_screen_height = self.root_window.winfo_screenheight()

                self.canvas_width = 810
                self.canvas_height = 540
                self.root_window.geometry(f"{self.canvas_width}x{self.canvas_height + 110}") 

                # Create the buttons and labels
                self.status_label = tk.Label(root_window, text="Welcome to FocusFlow! Click 'Connect'")
                self.status_label.pack(pady=5)

                self.connect_button = tk.Button(root_window, text="Connect to GazePointer", command=self.toggle_connection)
                self.connect_button.pack(pady=5)

                # Create the frame of AOI controls
                self.aoi_controls_frame = tk.Frame(root_window)
                self.aoi_controls_frame.pack(pady=5)

                self.add_productive_aoi_button = tk.Button(self.aoi_controls_frame, text="Add Productive AOI", command=lambda: self.start_defining_aoi("Productive"))
                self.add_productive_aoi_button.pack(side=tk.LEFT, padx=5)

                self.add_distraction_aoi_button = tk.Button(self.aoi_controls_frame, text="Add Distraction AOI", command=lambda: self.start_defining_aoi("Distraction"))
                self.add_distraction_aoi_button.pack(side=tk.LEFT, padx=5)

                self.clear_aois_button = tk.Button(self.aoi_controls_frame, text="Clear All AOIs", command=self.clear_all_aois)
                self.clear_aois_button.pack(side=tk.LEFT, padx=5)

                # Frame for session controls
                self.session_controls_frame = tk.Frame(root_window)
                self.session_controls_frame.pack(pady=5)

                self.start_session_button = tk.Button(self.session_controls_frame, text="Start Session", command=self.start_tracking_session, state=tk.NORMAL)
                self.start_session_button.pack(side=tk.LEFT, padx=5)

                self.end_session_button = tk.Button(self.session_controls_frame, text="End Session", command=self.end_tracking_session, state=tk.DISABLED)
                self.end_session_button.pack(side=tk.LEFT, padx=5)

                # Create the canvas to show the gaze tracking dot
                self.canvas = tk.Canvas(root_window, width=self.canvas_width, height=self.canvas_height, bg="lightgray")
                self.canvas.pack(pady=10)
                self.gaze_dot = self.canvas.create_oval(0,0,0,0, fill="red", outline="red")

                # Set the starting gaze tracking status
                self.gz_client = GazeFlowClient()
                self.is_tracking = False
                self.after_id = None

                # Clear the AOI list
                self.aoi_list = []
                self.current_aoi_start_coords = None
                self.defining_aoi_type = None

                # Reset AOI preview rectangle
                self.preview_rectangle_id = None
                self.canvas.bind("<ButtonPress-1>", self.on_aoi_drag_start)
                self.canvas.bind("<B1-Motion>", self.on_aoi_drag_motion)
                self.canvas.bind("<ButtonRelease-1>", self.on_aoi_drag_release)

                # Session state variables
                self.session_active = False
                # Store logged gaze data during a session
                self.session_data_log = [] 
                self.session_start_time = None

        def toggle_connection(self):
                if not self.gz_client.is_connected:
                        # Connect
                        if self.gz_client.connect():
                                # Successful connection
                                self.status_label.config(text="Connected! Receiving gaze data...")
                                self.connect_button.config(text="Disconnect")
                                self.is_tracking = True
                                self.update_gaze_dot()
                        else:
                                # Failed connection
                                self.is_tracking = False
                                # Cancel any scheduled updates
                                if self.after_id:
                                        self.root_window.after_cancel(self.after_id)
                                        self.after_id = None
                                self.gz_client.disconnect()
                                self.status_label.config(text="Connection failed. Is GazePointer running?")
                                self.connect_button.config(text="Connect to GazePointer")
                                self.canvas.coords(self.gaze_dot, 0, 0, 0, 0)
                else:
                        # Disconnect
                        self.is_tracking = False
                        # Cancel any scheduled updates
                        if self.after_id:
                                self.root_window.after_cancel(self.after_id)
                                self.after_id = None
                        self.gz_client.disconnect()
                        self.status_label.config(text="Disconnected. Click 'Connect' to start.")
                        self.connect_button.config(text="Connect to GazePointer")
                        self.canvas.coords(self.gaze_dot, 0, 0, 0, 0)

        def update_gaze_dot(self):
                # Update the dot only if the gaze tracker is currently connected and tracking
                if not self.is_tracking or not self.gz_client.is_connected:
                        return

                gaze_data = self.gz_client.receive_gaze_data()
                # Ensure the data is valid
                if gaze_data and 'GazeX' in gaze_data and 'GazeY' in gaze_data:
                        raw_gaze_x = gaze_data['GazeX']
                        raw_gaze_y = gaze_data['GazeY']

                        # Scale the coordinates to fit the box
                        x = 0
                        y = 0
                        if self.actual_screen_width > 0 and self.actual_screen_height > 0:
                                x = (raw_gaze_x / self.actual_screen_width) * self.canvas_width
                                y = (raw_gaze_y / self.actual_screen_height) * self.canvas_height
                        else:
                                x = raw_gaze_x
                                y = raw_gaze_y
                        
                        # Update coordinates of the gaze tracking dot
                        dot_size = 10
                        self.canvas.coords(self.gaze_dot, x - dot_size/2, y - dot_size/2, x + dot_size/2, y + dot_size/2)

                        # Log the gaze data if a session is active
                        if self.session_active:
                                current_timestamp = time.time()
                                aoi_type_hit = "Outside"

                                candidate_hit_aois = []
                                for i, aoi_item in enumerate(self.aoi_list):
                                        r_x1, r_y1, r_x2, r_y2 = aoi_item['rect']
                                        if r_x1 <= x <= r_x2 and r_y1 <= y <= r_y2:
                                                area = (r_x2 - r_x1) * (r_y2 - r_y1)
                                                candidate_hit_aois.append({
                                                        'type': aoi_item['type'],
                                                        'index': i,
                                                        'area': area,
                                                        'rect_coords': aoi_item['rect'],
                                                })

                                if candidate_hit_aois:
                                        # Sort by area and take the largest
                                        candidate_hit_aois.sort(key=lambda item: (item['area'], item['index']))
                                        chosen_aoi = candidate_hit_aois[0]
                                        aoi_type_hit = chosen_aoi['type']
                                
                                log_entry = {
                                        'timestamp': current_timestamp - (self.session_start_time if self.session_start_time else current_timestamp),
                                        'raw_x': raw_gaze_x,
                                        'raw_y': raw_gaze_y,
                                        'canvas_x': x,
                                        'canvas_y': y,
                                        'aoi_status': aoi_type_hit,
                                }

                                self.session_data_log.append(log_entry)
                        
                        elif self.defining_aoi_type is None:
                                # Only update gaze coordinates if not defining AOI AND not in session
                                self.status_label.config(text=f"Gaze: X={x:.0f}, Y={y:.0f}")

                elif not self.gz_client.is_connected:
                        # If the gaze tracker is not connected, toggle the connection status
                        self.toggle_connection()
                        return

                # Schedule the next update, update at roughly 60 FPS (1000ms/15ms)
                self.after_id = self.root_window.after(15, self.update_gaze_dot)

        def on_closing(self):
                if self.session_active:
                        self.end_tracking_session(force_end=True)
                if self.gz_client.is_connected:
                        self.gz_client.disconnect()
                self.root_window.destroy()
        
        def start_defining_aoi(self, aoi_type):
                if self.session_active:
                        self.status_label.config(text="Cannot define AOIs during an active session.")
                        return
                self.status_label.config(text=f"Defining {aoi_type} AOI: Click 1st corner...")
                self.defining_aoi_type = aoi_type

        def on_aoi_drag_start(self, event):
                # Continue only if in AOI definition mode and not in session
                if self.defining_aoi_type is None or self.session_active: 
                        return
                
                # Store the starting point for the drag
                self.current_aoi_start_coords = (event.x, event.y)

                # Delete any in-progress preview rectangles
                if self.preview_rectangle_id:
                        self.canvas.delete(self.preview_rectangle_id)

                # Make the preview rectangle dashed
                color = "green" if self.defining_aoi_type == "Productive" else "orange"
                self.preview_rectangle_id = self.canvas.create_rectangle(
                        event.x, event.y, event.x, event.y, 
                        outline=color, dash=(4, 2)
                )
                self.status_label.config(text=f"Defining {self.defining_aoi_type} AOI: Drag to set size, release to confirm.")

        def on_aoi_drag_motion(self, event):
                # Continue only if in AOI definition mode and drawing has started
                if self.defining_aoi_type is None or self.current_aoi_start_coords is None or self.session_active:
                        return

                # Update the coordinates of the preview rectangle
                x1, y1 = self.current_aoi_start_coords
                x2, y2 = event.x, event.y
                if self.preview_rectangle_id:
                        self.canvas.coords(self.preview_rectangle_id, x1, y1, x2, y2)
        
        def on_aoi_drag_release(self, event):
                # Continue only if in AOI definition mode and drawing has started
                if self.defining_aoi_type is None or self.current_aoi_start_coords is None or self.session_active:
                        return

                # Delete the preview rectangle
                if self.preview_rectangle_id:
                        self.canvas.delete(self.preview_rectangle_id)
                        self.preview_rectangle_id = None

                x1, y1 = self.current_aoi_start_coords
                x2, y2 = event.x, event.y

                final_x1 = min(x1, x2)
                final_y1 = min(y1, y2)
                final_x2 = max(x1, x2)
                final_y2 = max(y1, y2)

                # Avoid creating zero-size AOIs (click without drag)
                if final_x1 == final_x2 or final_y1 == final_y2:
                        self.status_label.config(text=f"AOI definition cancelled (too small). Click and drag to define.")
                        self.current_aoi_start_coords = None
                        self.defining_aoi_type = None
                        return

                aoi_rect = (final_x1, final_y1, final_x2, final_y2)
                self.aoi_list.append({'rect': aoi_rect, 'type': self.defining_aoi_type})

                # Redraw all AOIs
                self.draw_aois()

                # Reset for the next AOI definition
                self.status_label.config(text=f"{self.defining_aoi_type} AOI defined. Add another or start session.")
                self.current_aoi_start_coords = None
                self.defining_aoi_type = None
        
        def draw_aois(self):
                # Delete old AOI drawings by tag
                self.canvas.delete("aoi_rect") 
                self.canvas.delete("aoi_label")

                # Draw all AOIs in the list
                for i, aoi in enumerate(self.aoi_list):
                        x1, y1, x2, y2 = aoi['rect']
                        color = "green" if aoi['type'] == "Productive" else "orange"
                        
                        self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2, tags="aoi_rect")
                        self.canvas.create_text(x1 + 5, y1 + 5, text=f"{aoi['type']} {i+1}", anchor=tk.NW, fill=color, tags="aoi_label")

        def clear_all_aois(self):
                if self.session_active:
                        self.status_label.config(text="Cannot clear AOIs during an active session.")
                        return
                self.aoi_list = []
                # Redraw all AOIs (which is none)
                self.draw_aois() 
                self.status_label.config(text="All AOIs cleared.")
                self.defining_aoi_type = None

        def start_tracking_session(self):
                if not self.gz_client.is_connected:
                        self.status_label.config(text="Not connected to GazePointer. Please connect first.")
                        return
                
                if not self.aoi_list:
                        self.status_label.config(text="No AOIs defined. Please define at least 1 AOI.")
                        return
                
                if self.session_active:
                        self.status_label.config(text="Session already active. End the session first.")
                        return
                
                # Reset session state
                self.session_active = True
                self.session_data_log = []
                self.session_start_time = time.time()

                self.start_session_button.config(state=tk.DISABLED)
                self.end_session_button.config(state=tk.NORMAL)
                self.status_label.config(text="Session started. Tracking gaze data.")
                self.add_productive_aoi_button.config(state=tk.DISABLED)
                self.add_distraction_aoi_button.config(state=tk.DISABLED)
                self.clear_aois_button.config(state=tk.DISABLED)
                self.defining_aoi_type = None

        def end_tracking_session(self, force_end=False):
                if not self.session_active and not force_end:
                        self.status_label.config(text="No active session to end.")
                        return
                
                # End the session
                self.session_active = False
                self.start_session_button.config(state=tk.NORMAL)
                self.end_session_button.config(state=tk.DISABLED)
                self.status_label.config(text="Session ended. Processing data.")
                self.add_productive_aoi_button.config(state=tk.NORMAL)
                self.add_distraction_aoi_button.config(state=tk.NORMAL)
                self.clear_aois_button.config(state=tk.NORMAL)

                if self.session_data_log:
                        # Process the logged data
                        self.status_label.config(text="Session ended. Calculating metrics...")
                        self.calculate_session_metrics()
                else:
                        self.status_label.config(text="Session ended. No data logged.")

        def calculate_session_metrics(self):
                if not self.session_data_log:
                        self.status_label.config(text="Metrics: No data logged.")
                        return

                durations = []
                if len(self.session_data_log) > 1:
                        for i in range(len(self.session_data_log) - 1):
                                durations.append(self.session_data_log[i+1]['timestamp'] - self.session_data_log[i]['timestamp'])
                        if durations:
                                durations.append(durations[-1]) 
                        else: 
                                durations.append(0.015) 
                elif self.session_data_log: 
                        durations.append(0.015)

                time_in_productive = 0
                time_in_distraction = 0
                time_in_outside = 0
                # More accurate total time
                total_logged_time = sum(durations)

                for i, entry in enumerate(self.session_data_log):
                        delta_time = durations[i]
                        if entry['aoi_status'] == "Productive":
                                time_in_productive += delta_time
                        elif entry['aoi_status'] == "Distraction":
                                time_in_distraction += delta_time
                        else:
                                time_in_outside += delta_time
                
                print("\n--- Session Metrics ---")
                metrics_summary = f"Total Session Time: {total_logged_time:.2f} seconds\n"
                if total_logged_time > 0:
                        metrics_summary += f"Time in Productive: {time_in_productive:.2f}s ({(time_in_productive/total_logged_time)*100:.1f}%)\n"
                        metrics_summary += f"Time in Distraction: {time_in_distraction:.2f}s ({(time_in_distraction/total_logged_time)*100:.1f}%)\n"
                        metrics_summary += f"Time Outside AOIs: {time_in_outside:.2f}s ({(time_in_outside/total_logged_time)*100:.1f}%)"
                else:
                        metrics_summary += "Not enough data for dwell time calculation."
                print(metrics_summary)

                productive_to_distraction = 0
                distraction_to_productive = 0
                
                if len(self.session_data_log) > 1:
                        for i in range(1, len(self.session_data_log)):
                                prev_status = self.session_data_log[i-1]['aoi_status']
                                curr_status = self.session_data_log[i]['aoi_status']

                                if prev_status == "Productive" and curr_status == "Distraction":
                                        productive_to_distraction += 1
                                elif prev_status == "Distraction" and curr_status == "Productive":
                                        distraction_to_productive += 1
                
                transitions_summary = f"Transitions P->D: {productive_to_distraction}, D->P: {distraction_to_productive}"
                print(transitions_summary)
                metrics_summary += f"\n{transitions_summary}"

                productive_bouts_durations = []
                current_bout_start_timestamp = None
                
                for i, entry in enumerate(self.session_data_log):
                        entry_is_productive = (entry['aoi_status'] == "Productive")
                        entry_timestamp = entry['timestamp'] 

                        if entry_is_productive and current_bout_start_timestamp is None:
                                current_bout_start_timestamp = entry_timestamp
                        elif not entry_is_productive and current_bout_start_timestamp is not None:
                                bout_duration = entry_timestamp - current_bout_start_timestamp
                                # Ensure bout duration is not negative
                                if bout_duration > 0 : productive_bouts_durations.append(bout_duration)
                                current_bout_start_timestamp = None 
                
                if current_bout_start_timestamp is not None and self.session_data_log:
                        # Ensure last entry's timestamp is used relative to current_bout_start_timestamp
                        last_entry_timestamp = self.session_data_log[-1]['timestamp']
                        bout_duration = last_entry_timestamp - current_bout_start_timestamp
                        if bout_duration > 0 : productive_bouts_durations.append(bout_duration)

                bouts_summary = ""
                if productive_bouts_durations:
                        avg_bout_duration = sum(productive_bouts_durations) / len(productive_bouts_durations)
                        max_bout_duration = max(productive_bouts_durations)
                        bouts_summary = f"Productive Focus Bouts: Count={len(productive_bouts_durations)}, Avg={avg_bout_duration:.2f}s, Max={max_bout_duration:.2f}s"
                else:
                        bouts_summary = "No productive focus bouts recorded."
                print(bouts_summary)
                metrics_summary += f"\n{bouts_summary}"
                
                # Update status label with the final summary
                self.status_label.config(text="Session ended. Metrics calculated (see console).")

if __name__ == "__main__":
        # Runs when main_app.py is executed
        root = tk.Tk()
        app = FocusFlowApp(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()