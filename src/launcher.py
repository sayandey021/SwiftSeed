"""
SwiftSeed Launcher
This launcher sets the Windows App User Model ID before starting the main application.
This ensures proper taskbar branding and single instance behavior.
"""
import ctypes
import sys
import os
import subprocess

def main():
    # Set Windows App User Model ID FIRST
    if sys.platform == 'win32':
        try:
            app_id = 'SayanDey.SwiftSeed.TorrentClient.v5'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            print(f"[Pre-Init] Windows App User Model ID set to: {app_id}")
        except Exception as e:
            print(f"Failed to set App User Model ID: {e}")
    
    # Get the directory where this script is located
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        app_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Import and run the main app
    sys.path.insert(0, app_dir)
    
    # Check for single instance
    from managers.single_instance_manager import SingleInstanceManager
    
    instance_manager = SingleInstanceManager("SwiftSeed", 48213)
    
    # Check if we're the primary instance
    is_primary = instance_manager.check_and_acquire()
    
    if not is_primary:
        # Another instance is running - send the torrent file to it
        print("Another instance is already running. Sending file to existing instance...")
        
        # Get torrent file from command line if any
        torrent_file = None
        if len(sys.argv) > 1:
            torrent_file = sys.argv[1]
            if os.path.exists(torrent_file):
                print(f"Sending torrent file to existing instance: {torrent_file}")
                message = {
                    'action': 'open_torrent',
                    'file_path': os.path.abspath(torrent_file)
                }
                instance_manager.send_to_primary(message)
            else:
                print(f"File not found: {torrent_file}")
        else:
            # Just bring the existing window to front
            message = {'action': 'show_window'}
            instance_manager.send_to_primary(message)
        
        print("Message sent to existing instance. Exiting.")
        sys.exit(0)
    
    print("This is the primary instance. Starting application...")
    
    # Now import and run the actual main module
    import main as app_main
    import flet as ft
    
    # Set up message handler for the instance manager
    def handle_instance_message(message):
        """Handle messages from other instances"""
        print(f"Received message from another instance: {message}")
        # The actual handling will be done in main.py
        if hasattr(app_main, 'instance_message_handler'):
            app_main.instance_message_handler(message)
    
    # Update the callback
    instance_manager.check_and_acquire(on_message_callback=handle_instance_message)
    
    # Run the app
    try:
        ft.app(
            target=app_main.main, 
            assets_dir="assets",
            name="SwiftSeed",
            view=ft.AppView.FLET_APP
        )
    finally:
        instance_manager.release()

if __name__ == "__main__":
    main()
