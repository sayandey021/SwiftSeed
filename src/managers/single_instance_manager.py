"""
Single Instance Manager for SwiftSeed
Ensures only one instance of the application runs at a time
"""
import os
import sys
import socket
import json
import threading


class SingleInstanceManager:
    """Manages single instance of the application"""
    
    def __init__(self, app_name="SwiftSeed", port=48213):
        self.app_name = app_name
        self.port = port
        self.socket = None
        self.is_primary = False
        
    def check_and_acquire(self, on_message_callback=None):
        """
        Check if this is the primary instance and acquire the lock.
        Returns True if this is the primary instance, False otherwise.
        
        Args:
            on_message_callback: Function to call when receiving messages from other instances
        """
        try:
            # Try to bind to the port
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Do NOT use SO_REUSEADDR on Windows as it allows multiple binds
            if sys.platform != 'win32':
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            self.socket.bind(('127.0.0.1', self.port))
            self.socket.listen(5)
            self.is_primary = True
            
            # Start listening for messages from other instances
            if on_message_callback:
                def listen_thread():
                    while True:
                        try:
                            client, _ = self.socket.accept()
                            data = client.recv(4096).decode('utf-8')
                            if data:
                                message = json.loads(data)
                                on_message_callback(message)
                            client.close()
                        except OSError as e:
                            # Socket was closed (expected during shutdown)
                            if e.winerror == 10038 or 'not a socket' in str(e).lower():
                                break  # Exit gracefully
                            print(f"Error in listen thread: {e}")
                            break
                        except Exception as e:
                            print(f"Error in listen thread: {e}")
                            break
                
                threading.Thread(target=listen_thread, daemon=True).start()
            
            return True
            
        except OSError:
            # Port is already in use - another instance is running
            self.is_primary = False
            return False
    
    def send_to_primary(self, message):
        """
        Send a message to the primary instance.
        
        Args:
            message: Dictionary to send to primary instance
        
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(2)
            client.connect(('127.0.0.1', self.port))
            
            data = json.dumps(message).encode('utf-8')
            client.send(data)
            client.close()
            
            return True
        except Exception as e:
            print(f"Failed to send message to primary instance: {e}")
            return False
    
    def release(self):
        """Release the single instance lock"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
