from tkinter import *
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
from vehicle_detection import VehicleDetector
import threading
import time

class DynamicSignalsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dynamic Signals - Smart Traffic Control")
        self.root.geometry("1200x800")
        
        # Set theme colors
        self.bg_color = "#F0F8FF"  # Light blue background
        self.title_color = "#1E3A8A"  # Dark blue for titles
        self.accent_color = "#4F46E5"  # Indigo for buttons
        self.text_color = "#1F2937"  # Dark gray for text
        
        self.root.configure(bg=self.bg_color)
        
        # Create a title bar
        self.title_frame = Frame(root, bg="#1E3A8A", height=60)    
    
        self.title_frame.pack(fill=X)
        
        self.title_label = Label(self.title_frame, text="Dynamic Signals: AI Traffic Control", 
                               font=('Helvetica', 22, 'bold'), bg="#1E3A8A", fg="white")
        self.title_label.pack(pady=10)
        
        # Main content frame with two columns
        self.content_frame = Frame(root, bg=self.bg_color)
        self.content_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Left frame for traffic signals
        self.signals_frame = Frame(self.content_frame, bg=self.bg_color)
        self.signals_frame.pack(side=LEFT, fill=BOTH, expand=True)
        
        # Right frame for controls and logs
        self.controls_frame = Frame(self.content_frame, bg=self.bg_color)
        self.controls_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=20)
        
        # Create traffic signal image frames
        self.signal_frames = []
        self.signal_images = []
        self.signal_canvases = []
        self.light_positions = [
            {"red": (50, 50, 30), "yellow": (50, 100, 30), "green": (50, 150, 30)},  # Road 1
            {"red": (50, 50, 30), "yellow": (50, 100, 30), "green": (50, 150, 30)},  # Road 2
            {"red": (50, 50, 30), "yellow": (50, 100, 30), "green": (50, 150, 30)},  # Road 3
            {"red": (50, 50, 30), "yellow": (50, 100, 30), "green": (50, 150, 30)},  # Road 4
        ]
        
        # Signal frame titles
        signal_titles = ["North Road", "East Road", "South Road", "West Road"]
        
        # Create 2x2 grid for signals
        for i in range(4):
            row = i // 2
            col = i % 2
            
            # Create a frame with border
            frame = Frame(self.signals_frame, bg="white", bd=2, relief=RIDGE)
            frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            # Title for each signal
            title = Label(frame, text=signal_titles[i], font=('Helvetica', 12, 'bold'), bg="white", fg=self.title_color)
            title.pack(pady=5)
            
            # Canvas for the traffic signal image
            canvas = Canvas(frame, width=200, height=300, bg="white", highlightthickness=0)
            canvas.pack(fill=BOTH, expand=True, padx=10, pady=10)
            
            # Create default traffic signal with all lights off
            self.draw_traffic_signal(canvas, "off", "off", "off")
            
            self.signal_frames.append(frame)
            self.signal_canvases.append(canvas)
        
        # Configure grid weights
        self.signals_frame.grid_rowconfigure(0, weight=1)
        self.signals_frame.grid_rowconfigure(1, weight=1)
        self.signals_frame.grid_columnconfigure(0, weight=1)
        self.signals_frame.grid_columnconfigure(1, weight=1)
        
        # Status section
        self.status_frame = LabelFrame(self.controls_frame, text="Road Status", font=('Helvetica', 12, 'bold'), 
                                      bg="white", fg=self.title_color, bd=2, relief=RIDGE)
        self.status_frame.pack(fill=X, pady=10)
        
        self.status_labels = []
        for i in range(4):
            frame = Frame(self.status_frame, bg="white")
            frame.pack(fill=X, padx=10, pady=5)
            
            road_label = Label(frame, text=f"{signal_titles[i]}:", font=('Helvetica', 11), 
                             bg="white", fg=self.text_color, width=10, anchor='w')
            road_label.pack(side=LEFT)
            
            status_label = Label(frame, text="Not Processed", font=('Helvetica', 11), 
                              bg="white", fg="gray")
            status_label.pack(side=LEFT, fill=X, expand=True)
            
            self.status_labels.append(status_label)
        
        # Control buttons
        self.button_frame = Frame(self.controls_frame, bg=self.bg_color)
        self.button_frame.pack(fill=X, pady=10)
        
        self.start_btn = Button(self.button_frame, text="Start Traffic Control", 
                              command=self.control_junction, font=('Helvetica', 12, 'bold'), 
                              bg=self.accent_color, fg='white', relief=RAISED, bd=1,
                              padx=15, pady=8, cursor="hand2")
        self.start_btn.pack(side=LEFT, padx=5)
        
        self.clear_btn = Button(self.button_frame, text="Reset", 
                              command=self.reset_status, font=('Helvetica', 12, 'bold'), 
                              bg="#DC2626", fg='white', relief=RAISED, bd=1,
                              padx=15, pady=8, cursor="hand2")
        self.clear_btn.pack(side=LEFT, padx=5)
        
        # Logs section
        log_frame = LabelFrame(self.controls_frame, text="System Logs", font=('Helvetica', 12, 'bold'), 
                             bg="white", fg=self.title_color, bd=2, relief=RIDGE)
        log_frame.pack(fill=BOTH, expand=True, pady=10)
        
        self.log_text = Text(log_frame, height=15, width=40, font=('Courier', 10), 
                           bg="#F9FAFB", fg=self.text_color, bd=0)
        self.log_text.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        scroll = Scrollbar(self.log_text)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=RIGHT, fill=Y)
        
        # Initialize detector - PASS THE ROOT WINDOW AS PARAMETER
        self.detector = VehicleDetector(self.root)
        self.current_road = None
        self.emergency_flag = False
        self.running = False
        
        # Add a welcome message
        self.log("Welcome to Dynamic Traffic Signal System")
        self.log("Press 'Start Traffic Control' to begin")

    def draw_traffic_signal(self, canvas, red_state, yellow_state, green_state):
        # Clear the canvas
        canvas.delete("all")
        
        # Draw signal housing
        canvas.create_rectangle(25, 25, 75, 175, fill="#333333", outline="black", width=2)
        
        # Draw lights
        # Red light
        if red_state == "on":
            red_color = "#FF0000"  # Bright red
        else:
            red_color = "#441111"  # Dark red (off)
        canvas.create_oval(35, 35, 65, 65, fill=red_color, outline="black")
        
        # Yellow light
        if yellow_state == "on":
            yellow_color = "#FFFF00"  # Bright yellow
        else:
            yellow_color = "#444411"  # Dark yellow (off)
        canvas.create_oval(35, 85, 65, 115, fill=yellow_color, outline="black")
        
        # Green light
        if green_state == "on":
            green_color = "#00FF00"  # Bright green
        else:
            green_color = "#114411"  # Dark green (off)
        canvas.create_oval(35, 135, 65, 165, fill=green_color, outline="black")
        
        # Draw road indication
        canvas.create_rectangle(25, 185, 75, 220, fill="#bbbbbb", outline="black")
        canvas.create_line(50, 185, 50, 220, fill="white", width=2, dash=(5, 3))

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(END, f"[{timestamp}] {message}\n")
        self.log_text.see(END)

    def activate_green_signal(self, road_index, duration):
        """Show green signal for the specified duration"""
        if not self.running:
            return
            
        road_name = ["North", "East", "South", "West"][road_index]
        
        # Turn on green light
        self.log(f"GREEN signal for {road_name} Road: {duration} seconds")
        self.status_labels[road_index].config(text=f"GREEN for {duration}s", fg="#059669")
        
        canvas = self.signal_canvases[road_index]
        self.draw_traffic_signal(canvas, "off", "off", "on")
        
        # Keep the green light on for the duration
        end_time = time.time() + duration
        while time.time() < end_time and self.running:
            time.sleep(0.5)
            self.root.update()
            
        if not self.running:
            return
        
        # Yellow light transition
        self.activate_yellow_signal(road_index)
        
        if not self.running:
            return
            
        # Red light
        self.activate_red_signal(road_index)

    def activate_yellow_signal(self, road_index):
        """Show yellow signal for 5 seconds"""
        if not self.running:
            return
            
        road_name = ["North", "East", "South", "West"][road_index]
        
        # Turn on yellow light
        self.log(f"YELLOW signal for {road_name} Road: 5 seconds")
        self.status_labels[road_index].config(text="YELLOW for 5s", fg="#D97706")
        
        canvas = self.signal_canvases[road_index]
        self.draw_traffic_signal(canvas, "off", "on", "off")
        
        # Keep the yellow light on for 5 seconds
        start_time = time.time()
        while time.time() < start_time + 5 and self.running:
            time.sleep(0.5)
            self.root.update()

    def activate_red_signal(self, road_index):
        """Show red signal"""
        if not self.running:
            return
            
        road_name = ["North", "East", "South", "West"][road_index]
        
        # Turn on red light
        self.log(f"RED signal for {road_name} Road")
        self.status_labels[road_index].config(text="RED", fg="#DC2626")
        
        canvas = self.signal_canvases[road_index]
        self.draw_traffic_signal(canvas, "on", "off", "off")

    def check_emergency(self):
        return self.emergency_flag

    def control_junction(self):
        self.start_btn.config(state=DISABLED)
        self.running = True
        
        # Reset all signals to red
        for i in range(4):
            self.activate_red_signal(i)
        
        # Start in a separate thread to keep UI responsive
        thread = threading.Thread(target=self._process_junction)
        thread.daemon = True
        thread.start()

    def _process_junction(self):
        road_times = [0] * 4  # Store green times for each road
        road_names = ["North", "East", "South", "West"]
        
        # Process all roads first
        for road in range(4):
            if not self.running:
                break
                
            self.log(f"Please select video for {road_names[road]} Road")
            self.status_labels[road].config(text="Waiting for video...", fg="blue")
            self.root.update()  # Update UI
            
            # Use a modal dialog that blocks until user selects a file
            filename = filedialog.askopenfilename(
                title=f"Select Video for {road_names[road]} Road",
                filetypes=[("Video files", "*.mp4 *.avi")]
            )
            
            if filename and self.running:
                self.log(f"Processing {road_names[road]} Road: {os.path.basename(filename)}")
                self.status_labels[road].config(text="Processing...", fg="orange")
                self.root.update()  # Update UI
                
                # Detect vehicles and calculate green time
                green_time, emergency = self.detector.detect_vehicles(filename)
                road_times[road] = green_time
                
                if emergency:
                    self.log(f"⚠️ Emergency vehicle detected on {road_names[road]} Road")
                
                self.status_labels[road].config(text=f"Processed: {green_time}s", fg="green")
                self.log(f"{road_names[road]} Road Green Time: {green_time} seconds")
            else:
                if self.running:  # Only show warning if still running
                    messagebox.showwarning("No File", f"No video selected for {road_names[road]} Road")
                    self.status_labels[road].config(text="No Video", fg="gray")
                road_times[road] = 10  # Default time if no video
        
        # Execute signal sequence with emergency handling
        if self.running:
            self.log("Starting traffic signal sequence")
            
            for road in range(4):
                if not self.running:
                    break
                    
                if road_times[road] > 0:
                    self.current_road = road
                    
                    # Activate green signal for this road
                    self.activate_green_signal(road, road_times[road])
                    
                    # Small delay between roads
                    if self.running:
                        time.sleep(2)
        
        self.log("Traffic control sequence completed")
        self.running = False
        # Re-enable start button on the main thread
        self.root.after(0, lambda: self.start_btn.config(state=NORMAL))

    def reset_status(self):
        # Stop any running sequence
        self.running = False
        
        # Reset all status labels
        for i, label in enumerate(self.status_labels):
            label.config(text="Not Processed", fg="gray")
        
        # Clear the log
        self.log_text.delete(1.0, END)
        self.log("Status reset")
        
        # Reset all signals to off
        for canvas in self.signal_canvases:
            self.draw_traffic_signal(canvas, "off", "off", "off")
        
        # Reset flags
        self.emergency_flag = False
        self.current_road = None
        
        # Re-enable start button
        self.start_btn.config(state=NORMAL)

if __name__ == "__main__":
    root = Tk()
    app = DynamicSignalsApp(root)
    root.mainloop()