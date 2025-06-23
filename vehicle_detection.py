import cv2
import numpy as np
import os
from centroid_tracker import CentroidTracker
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk
import threading
import time

# Import ultralytics
try:
    from ultralytics import YOLO
except ImportError:
    messagebox.showerror("Missing Package", 
                        "The 'ultralytics' package is required but not installed.\n"
                        "Please install it with: pip install ultralytics")
    raise

class DownloadProgressDialog:
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Downloading YOLOv8 Model")
        self.dialog.geometry("400x150")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Dialog content
        tk.Label(self.dialog, text="Downloading YOLOv8 model...", font=("Helvetica", 12)).pack(pady=(20, 10))
        tk.Label(self.dialog, text="This may take a few minutes depending on your internet connection.").pack()
        
        self.progress = ttk.Progressbar(self.dialog, orient="horizontal", length=350, mode="indeterminate")
        self.progress.pack(pady=15, padx=25)
        self.progress.start(10)
        
        self.download_complete = False
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def on_close(self):
        if not self.download_complete:
            if messagebox.askokcancel("Cancel Download", "Are you sure you want to cancel the download?"):
                self.dialog.destroy()
        else:
            self.dialog.destroy()
    
    def complete(self):
        self.download_complete = True
        self.progress.stop()
        self.dialog.destroy()

class VehicleDetector:
    def __init__(self, parent_window=None):
        self.parent_window = parent_window
        model_path = "yolov8n.pt"  # Using YOLOv8 nano model
        
        # Check if model exists
        if not os.path.exists(model_path):
            self.download_model(model_path)
        
        # Load the YOLOv8 model
        self.model = YOLO(model_path)
        
        # Define vehicle and emergency vehicle classes
        # YOLOv8 uses COCO classes by default
        self.vehicle_types = ["car", "bus", "truck", "motorcycle"]  # COCO class names
        self.emergency_types = ["ambulance", "fire engine"]  # Note: might need custom training for these
        
        self.ct = CentroidTracker()
    
    def download_model(self, model_path):
        """Download the YOLOv8 model with progress dialog"""
        if self.parent_window:
            progress_dialog = DownloadProgressDialog(self.parent_window)
            
            # Download in a separate thread
            def download_thread():
                try:
                    # This will download the model to the current directory
                    YOLO(model_path)
                    # Close the dialog when done
                    self.parent_window.after(0, progress_dialog.complete)
                except Exception as e:
                    messagebox.showerror("Download Error", f"Failed to download model: {str(e)}")
                    self.parent_window.after(0, progress_dialog.dialog.destroy)
            
            thread = threading.Thread(target=download_thread)
            thread.daemon = True
            thread.start()
            
            # Wait for the dialog to close
            self.parent_window.wait_window(progress_dialog.dialog)
            
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Could not download YOLOv8 model: {model_path}")
        else:
            # No parent window, download without dialog
            try:
                print("Downloading YOLOv8 model. Please wait...")
                YOLO(model_path)
                print("Download complete!")
            except Exception as e:
                raise FileNotFoundError(f"Could not download YOLOv8 model: {str(e)}")

    def detect_vehicles(self, video_path):
        try:
            window_name = "Traffic Detection"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Could not open video file: {video_path}")
                
            cumulative_count = 0
            emergency_detected = False
            
            # Define target display size
            display_width, display_height = 640, 480
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Check if window is closed
                if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                    break
                
                # Resize frame for processing and display
                frame_resized = cv2.resize(frame, (display_width, display_height))
                
                # Run YOLOv8 inference on the resized frame
                results = self.model(frame_resized)
                
                # Process detections
                rects = []
                
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        # Get box coordinates (already in resized frame coordinates)
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                        
                        # Get confidence
                        conf = float(box.conf[0])
                        
                        # Get class name
                        cls = int(box.cls[0])
                        class_name = self.model.names[cls]
                        
                        # Check if detection is a vehicle and confidence is high enough
                        if conf > 0.5 and (class_name in self.vehicle_types or class_name in self.emergency_types):
                            rects.append([x1, y1, x2, y2])
                            
                            # Check for emergency vehicles
                            if class_name in self.emergency_types:
                                emergency_detected = True
                            
                            # Draw bounding box on the resized frame
                            cv2.rectangle(frame_resized, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            cv2.putText(frame_resized, f"{class_name} {conf:.2f}", 
                                      (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Update centroid tracker with scaled rectangles
                objects = self.ct.update(rects)
                count = len(objects)
                cumulative_count = max(cumulative_count, count)
                
                # Draw centroids on the resized frame
                for (objectID, centroid) in objects.items():
                    cv2.circle(frame_resized, (centroid[0], centroid[1]), 4, (0, 255, 0), -1)
                    cv2.putText(frame_resized, f"ID {objectID}", (centroid[0] - 10, centroid[1] - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Display vehicle count
                cv2.putText(frame_resized, f"Current Vehicles: {count}", (10, 30), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame_resized, f"Max Vehicles: {cumulative_count}", (10, 60), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Display emergency vehicle warning
                if emergency_detected:
                    cv2.putText(frame_resized, "Emergency Vehicle Detected!", (10, 90), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                cv2.imshow(window_name, frame_resized)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
            
            cap.release()
            cv2.destroyAllWindows()
            
            # Calculate green time based on vehicle count
            green_time = min(max(cumulative_count * 2, 10), 60)  # Min 10 sec, max 60 sec
            
            return green_time, emergency_detected
            
        except Exception as e:
            print(f"Detection Error: {e}")
            messagebox.showerror("Detection Error", str(e))
            return 10, False  # Default values in case of error6