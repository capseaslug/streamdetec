import pcapy
import re
import threading
import tkinter as tk
from tkinter import scrolledtext
import psutil
import netifaces

class PacketAnalyzer:
    def __init__(self, interface, log_text_widget):
        self.interface = interface
        self.cap = pcapy.open_live(interface, 65536, True, 0)
        self.log_text_widget = log_text_widget
    
    def start(self):
        threading.Thread(target=self._packet_sniffer).start()
    
    def _packet_sniffer(self):
        while True:
            header, packet = self.cap.next()
            payload = packet[14:]  # Strip Ethernet header
            if self._is_video_stream(payload):
                result = f"Detected potential video stream on interface {self.interface}\n"
                self.log_text_widget.insert(tk.END, result)

    def _is_video_stream(self, payload):
        video_patterns = [
            rb'\x00\x00\x01\xb0',  # MPEG-2 start code
            rb'\x00\x00\x00\x01\x67',  # H.264 start code
            rb'flv\x01',  # FLV header
        ]
        
        for pattern in video_patterns:
            if re.search(pattern, payload):
                return True
        return False

def start_analyzer(interface, log_text_widget):
    analyzer = PacketAnalyzer(interface, log_text_widget)
    analyzer.start()

def check_monitoring_processes(log_text_widget):
    for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = process.info['cmdline']
            
            if "keylogger" in ' '.join(cmdline).lower() or "monitoring" in ' '.join(cmdline).lower():
                result = f"Potential monitoring process detected: {process.info['name']}\n"
                log_text_widget.insert(tk.END, result)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def start_button_callback(interface_var, log_text_widget):
    interface = interface_var.get()
    start_analyzer(interface, log_text_widget)
    check_monitoring_processes(log_text_widget)

# Create GUI window
root = tk.Tk()
root.title("Network Analyzer")

# Create and place interface selection label and entry
interface_label = tk.Label(root, text="Interface:")
interface_label.pack()

interface_var = tk.StringVar()
interface_entry = tk.Entry(root, textvariable=interface_var)
interface_entry.pack()

# Create and place start button
start_button = tk.Button(root, text="Start Analysis", command=lambda: start_button_callback(interface_var, log_text))
start_button.pack()

# Create and place log text widget
log_text = scrolledtext.ScrolledText(root, wrap=tk.WORD)
log_text.pack()

# Run GUI main loop
root.mainloop()
