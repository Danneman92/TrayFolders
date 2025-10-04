import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QFileInfo
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FolderWatcher(FileSystemEventHandler):
    """Watches folder for changes and updates menu"""
    def __init__(self, callback):
        self.callback = callback
        
    def on_any_event(self, event):
        self.callback()

class TrayFolders(QSystemTrayIcon):
    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = Path(folder_path)
        self.setIcon(QIcon.fromTheme("folder"))
        self.setToolTip(f"TrayFolders - {self.folder_path.name}")
        
        # Setup file watcher
        self.observer = Observer()
        self.event_handler = FolderWatcher(self.update_menu)
        self.observer.schedule(self.event_handler, str(self.folder_path), recursive=False)
        self.observer.start()
        
        self.update_menu()
        self.show()
        
    def update_menu(self):
        """Update the context menu with folder contents"""
        menu = QMenu()
        
        if not self.folder_path.exists():
            action = menu.addAction("Folder not found")
            action.setEnabled(False)
        else:
            # Add files and folders
            items = sorted(self.folder_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            
            for item in items:
                if item.name.startswith('.'):
                    continue
                    
                action = QAction(item.name, menu)
                
                # Set icon based on type
                if item.is_dir():
                    action.setIcon(QIcon.fromTheme("folder"))
                else:
                    # Get file icon from system
                    file_info = QFileInfo(str(item))
                    action.setIcon(QIcon.fromTheme("text-x-generic"))
                
                action.triggered.connect(lambda checked=False, p=item: self.open_item(p))
                menu.addAction(action)
            
            if not items:
                action = menu.addAction("Empty folder")
                action.setEnabled(False)
        
        menu.addSeparator()
        
        # Open folder action
        open_action = QAction("Open Folder", menu)
        open_action.triggered.connect(lambda: self.open_item(self.folder_path))
        menu.addAction(open_action)
        
        # Exit action
        exit_action = QAction("Exit", menu)
        exit_action.triggered.connect(QApplication.quit)
        menu.addAction(exit_action)
        
        self.setContextMenu(menu)
    
    def open_item(self, path):
        """Open file or folder with default application"""
        os.startfile(str(path))
    
    def cleanup(self):
        """Cleanup resources"""
        self.observer.stop()
        self.observer.join()

def main():
    # Default to user's Documents folder or specify custom path
    folder = os.path.expanduser("~/Documents")
    
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    
    if not os.path.exists(folder):
        print(f"Error: Folder '{folder}' does not exist")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    tray = TrayFolders(folder)
    
    try:
        sys.exit(app.exec())
    finally:
        tray.cleanup()

if __name__ == "__main__":
    main()
