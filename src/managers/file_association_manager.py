"""
File Association Manager for SwiftSeed
Handles registration of .torrent and magnet: protocol handlers on Windows
"""
import os
import sys
import winreg
import subprocess
from pathlib import Path


class FileAssociationManager:
    """Manages file and protocol associations for SwiftSeed"""
    
    def __init__(self, app_name="SwiftSeed", app_description="SwiftSeed Torrent Client"):
        self.app_name = app_name
        self.app_description = app_description
        self.exe_path = self._get_exe_path()
        
    def _get_exe_path(self):
        """Get the path to the SwiftSeed executable"""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            return sys.executable
        else:
            # Running from Python - return None as we can't register
            return None
    
    def is_running_as_executable(self):
        """Check if running as a compiled executable"""
        return self.exe_path is not None
    
    def is_torrent_handler(self):
        """Check if SwiftSeed is registered as .torrent handler"""
        if not self.is_running_as_executable():
            return False
            
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.torrent", 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, "")
            winreg.CloseKey(key)
            
            # Check if it points to our app
            if value == "SwiftSeed.TorrentFile":
                return True
                
            # Also check the default program
            try:
                key2 = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                     r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.torrent\UserChoice", 
                                     0, winreg.KEY_READ)
                prog_id, _ = winreg.QueryValueEx(key2, "ProgId")
                winreg.CloseKey(key2)
                return prog_id == "SwiftSeed.TorrentFile"
            except:
                pass
                
            return False
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"Error checking .torrent handler: {e}")
            return False
    
    def is_magnet_handler(self):
        """Check if SwiftSeed is registered as magnet: protocol handler"""
        if not self.is_running_as_executable():
            return False
            
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\magnet\shell\open\command", 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, "")
            winreg.CloseKey(key)
            
            # Check if it points to our executable
            return self.exe_path in value
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"Error checking magnet handler: {e}")
            return False
    
    def register_torrent_handler(self):
        """Register SwiftSeed as .torrent file handler"""
        if not self.is_running_as_executable():
            return False, "Can only register when running as executable"
            
        try:
            # Create ProgID for .torrent files
            prog_id_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\SwiftSeed.TorrentFile")
            winreg.SetValue(prog_id_key, "", winreg.REG_SZ, "Torrent File")
            winreg.SetValueEx(prog_id_key, "FriendlyTypeName", 0, winreg.REG_SZ, "Torrent File")
            winreg.CloseKey(prog_id_key)
            
            # Set default icon
            # Try to find file.ico in assets folder
            icon_path = f'"{self.exe_path}",0'
            try:
                app_dir = os.path.dirname(self.exe_path)
                file_icon = os.path.join(app_dir, "assets", "file.ico")
                if os.path.exists(file_icon):
                    icon_path = f'"{file_icon}"'
            except:
                pass
                
            icon_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\SwiftSeed.TorrentFile\DefaultIcon")
            winreg.SetValue(icon_key, "", winreg.REG_SZ, icon_path)
            winreg.CloseKey(icon_key)
            
            # Set command to open
            command_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\SwiftSeed.TorrentFile\shell\open\command")
            winreg.SetValue(command_key, "", winreg.REG_SZ, f'"{self.exe_path}" "%1"')
            winreg.CloseKey(command_key)
            
            # Associate .torrent extension
            ext_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.torrent")
            winreg.SetValue(ext_key, "", winreg.REG_SZ, "SwiftSeed.TorrentFile")
            winreg.CloseKey(ext_key)
            
            print("[OK] Registered .torrent file handler")
            return True, "Successfully registered .torrent handler"
        except Exception as e:
            error_msg = f"Failed to register .torrent handler: {e}"
            print(f"[FAIL] {error_msg}")
            return False, error_msg
    
    def register_magnet_handler(self):
        """Register SwiftSeed as magnet: protocol handler"""
        if not self.is_running_as_executable():
            return False, "Can only register when running as executable"
            
        try:
            # Create magnet protocol handler
            magnet_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\magnet")
            winreg.SetValue(magnet_key, "", winreg.REG_SZ, "URL:Magnet Protocol")
            winreg.SetValueEx(magnet_key, "URL Protocol", 0, winreg.REG_SZ, "")
            winreg.CloseKey(magnet_key)
            
            # Set default icon
            icon_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\magnet\DefaultIcon")
            winreg.SetValue(icon_key, "", winreg.REG_SZ, f'"{self.exe_path}",0')
            winreg.CloseKey(icon_key)
            
            # Set command to open magnet links
            command_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\magnet\shell\open\command")
            winreg.SetValue(command_key, "", winreg.REG_SZ, f'"{self.exe_path}" "%1"')
            winreg.CloseKey(command_key)
            
            print("[OK] Registered magnet: protocol handler")
            return True, "Successfully registered magnet: handler"
        except Exception as e:
            error_msg = f"Failed to register magnet: handler: {e}"
            print(f"[FAIL] {error_msg}")
            return False, error_msg
    
    def register_all(self):
        """Register both .torrent and magnet: handlers"""
        torrent_success, torrent_msg = self.register_torrent_handler()
        magnet_success, magnet_msg = self.register_magnet_handler()
        
        if torrent_success and magnet_success:
            return True, "Successfully registered all handlers"
        elif torrent_success or magnet_success:
            return True, f"Partial success: {torrent_msg}; {magnet_msg}"
        else:
            return False, f"Failed: {torrent_msg}; {magnet_msg}"
    
    def unregister_torrent_handler(self):
        """Unregister .torrent file handler"""
        try:
            # Remove .torrent association
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.torrent")
            except FileNotFoundError:
                pass
            
            # Remove ProgID
            try:
                self._delete_key_recursive(winreg.HKEY_CURRENT_USER, r"Software\Classes\SwiftSeed.TorrentFile")
            except FileNotFoundError:
                pass
                
            print("[OK] Unregistered .torrent file handler")
            return True, "Successfully unregistered .torrent handler"
        except Exception as e:
            error_msg = f"Failed to unregister .torrent handler: {e}"
            print(f"[FAIL] {error_msg}")
            return False, error_msg
    
    def unregister_magnet_handler(self):
        """Unregister magnet: protocol handler"""
        try:
            # Remove magnet protocol
            try:
                self._delete_key_recursive(winreg.HKEY_CURRENT_USER, r"Software\Classes\magnet")
            except FileNotFoundError:
                pass
                
            print("[OK] Unregistered magnet: protocol handler")
            return True, "Successfully unregistered magnet: handler"
        except Exception as e:
            error_msg = f"Failed to unregister magnet: handler: {e}"
            print(f"[FAIL] {error_msg}")
            return False, error_msg
    
    def _delete_key_recursive(self, root, key_path):
        """Recursively delete a registry key and all its subkeys"""
        try:
            # Open the key
            key = winreg.OpenKey(root, key_path, 0, winreg.KEY_ALL_ACCESS)
            
            # Get all subkeys
            subkeys = []
            i = 0
            while True:
                try:
                    subkeys.append(winreg.EnumKey(key, i))
                    i += 1
                except OSError:
                    break
            
            # Recursively delete all subkeys
            for subkey in subkeys:
                self._delete_key_recursive(root, f"{key_path}\\{subkey}")
            
            winreg.CloseKey(key)
            
            # Delete the key itself
            winreg.DeleteKey(root, key_path)
        except FileNotFoundError:
            pass
    
    def open_windows_default_apps(self):
        """Open Windows Settings to Default Apps page"""
        try:
            # Windows 10/11 Settings URI
            subprocess.run(['start', 'ms-settings:defaultapps'], shell=True)
            return True, "Opened Windows Settings"
        except Exception as e:
            return False, f"Failed to open settings: {e}"
    
    def get_status_summary(self):
        """Get a summary of current registration status"""
        if not self.is_running_as_executable():
            return "Not running as executable - cannot check associations"
        
        torrent = "[OK] Registered" if self.is_torrent_handler() else "[X] Not registered"
        magnet = "[OK] Registered" if self.is_magnet_handler() else "[X] Not registered"
        
        return f".torrent files: {torrent}\nmagnet: links: {magnet}"
