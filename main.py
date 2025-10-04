import os
import sys
import subprocess

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QFileIconProvider
from PySide6.QtGui import QIcon, QAction, QCursor
from PySide6.QtCore import QObject, Signal, QTimer, QFileInfo

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAVE_WATCHDOG = True
except ImportError:
    HAVE_WATCHDOG = False

try:
    import win32com.client
except ImportError:
    win32com = None

APP_NAME = "TrayFolders"
ICON_PATH = None

def get_app_dir():
    # Supports PyInstaller temporary _MEIPASS for onefile EXE
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        return os.path.dirname(os.path.abspath(__file__))

# Set working directory for reliable DLL loading
os.chdir(get_app_dir())

CFG_PATH = os.path.join(get_app_dir(), "folders.cfg")
MAX_DEPTH = 4
SHOW_FILES = True
SORT_FOLDERS_FIRST = True

icon_provider = QFileIconProvider()

def load_roots(cfg_path=CFG_PATH):
    roots = []
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    roots.append(line)
    return roots

def safe_listdir(path):
    try:
        return os.listdir(path)
    except Exception:
        return []

def get_file_icon(path):
    try:
        qfi = QFileInfo(path)
        return icon_provider.icon(qfi)
    except Exception:
        return QIcon()

def launch_shortcut(lnk_path):
    # Launch .lnk shortcut using target and working directory
    if win32com:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(lnk_path)
        target = shortcut.Targetpath
        working_dir = shortcut.WorkingDirectory or os.path.dirname(target)
        orig_path = os.environ.get('PATH', '')
        os.environ['PATH'] = working_dir + ';' + orig_path
        try:
            if target.lower().endswith('.exe'):
                subprocess.Popen([target], cwd=working_dir)
            else:
                subprocess.Popen(['cmd', '/c', 'start', '', target], cwd=working_dir)
        finally:
            os.environ['PATH'] = orig_path
    else:
        subprocess.Popen(['explorer', os.path.dirname(lnk_path)])

def launch_file(path):
    ext = os.path.splitext(path)[1].lower()
    target_dir = os.path.dirname(path)
    orig_path = os.environ.get('PATH', '')
    os.environ['PATH'] = target_dir + ';' + orig_path
    try:
        if ext == '.lnk':
            launch_shortcut(path)
        elif os.path.isfile(path):
            if path.lower().endswith('.exe'):
                subprocess.Popen([path], cwd=target_dir)
            else:
                subprocess.Popen(['cmd', '/c', 'start', '', path], cwd=target_dir)
        elif os.path.isdir(path):
            subprocess.Popen(['explorer', path], cwd=path)
    finally:
        os.environ['PATH'] = orig_path

def build_folder_menu(menu: QMenu, folder_path: str, depth=0, max_depth=3, show_files=True):
    if depth > max_depth:
        return
    try:
        entries = safe_listdir(folder_path)
        entries_full = [os.path.join(folder_path, e) for e in entries]
    except Exception:
        return

    dirs = [p for p in entries_full if os.path.isdir(p)]
    files = [p for p in entries_full if os.path.isfile(p)]
    dirs.sort(key=lambda p: os.path.basename(p).lower())
    files.sort(key=lambda p: os.path.basename(p).lower())

    if SORT_FOLDERS_FIRST:
        ordered = dirs + (files if show_files else [])
    else:
        mixed = entries_full
        mixed.sort(key=lambda p: os.path.basename(p).lower())
        ordered = [p for p in mixed if os.path.isdir(p)] + ([p for p in mixed if os.path.isfile(p)] if show_files else [])

    for path in ordered:
        name = os.path.basename(path) or path
        icon = get_file_icon(path)
        if os.path.isdir(path):
            sub = QMenu(name, menu)
            sub.setIcon(icon)
            open_here = QAction(icon, "Open in Explorer", sub)
            open_here.triggered.connect(lambda checked=False, p=path: launch_file(p))
            sub.addAction(open_here)
            sub.addSeparator()
            build_folder_menu(sub, path, depth + 1, max_depth, show_files)
            menu.addMenu(sub)
        else:
            act = QAction(icon, name, menu)
            act.triggered.connect(lambda checked=False, p=path: launch_file(p))
            menu.addAction(act)

class TrayApp(QObject):

    rebuild_requested = Signal()

    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.tray = QSystemTrayIcon()
        if ICON_PATH and os.path.exists(ICON_PATH):
            self.tray.setIcon(QIcon(ICON_PATH))
        else:
            icon = QIcon.fromTheme("folder")
            if icon.isNull():
                icon = QIcon()
            self.tray.setIcon(icon)
        self.folder_menu = QMenu()
        self.context_menu = QMenu()
        self._populate_menus()
        self.tray.setContextMenu(self.context_menu)
        self.tray.setToolTip(APP_NAME)
        self.tray.setVisible(True)
        self.tray.activated.connect(self.on_tray_activated)
        self.rebuild_requested.connect(self._rebuild_menus)
        self._pending_rebuild = False
        self._debounce_timer = QTimer()
        self._debounce_timer.setInterval(400)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._commit_rebuild)
        self.observer = None
        if HAVE_WATCHDOG:
            self._setup_watchdog()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.folder_menu.exec(QCursor.pos())
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            pass

    def _populate_menus(self):
        self.folder_menu.clear()
        roots = load_roots()
        valid_roots = [p for p in roots if os.path.isdir(p)]
        for root in valid_roots:
            title = os.path.basename(root) or root
            root_icon = get_file_icon(root)
            root_menu = QMenu(title, self.folder_menu)
            root_menu.setIcon(root_icon)
            open_root = QAction(root_icon, "Open in Explorer", root_menu)
            open_root.triggered.connect(lambda checked=False, p=root: launch_file(p))
            root_menu.addAction(open_root)
            root_menu.addSeparator()
            build_folder_menu(root_menu, root, depth=0, max_depth=MAX_DEPTH, show_files=True)
            self.folder_menu.addMenu(root_menu)
        self.context_menu.clear()
        edit_action = QAction("Edit Folders...", self.context_menu)
        edit_action.triggered.connect(lambda: launch_file(CFG_PATH))
        self.context_menu.addAction(edit_action)
        refresh = QAction("Refresh", self.context_menu)
        refresh.triggered.connect(self._request_rebuild)
        self.context_menu.addAction(refresh)
        quit_action = QAction("Quit", self.context_menu)
        quit_action.triggered.connect(self._quit)
        self.context_menu.addAction(quit_action)

    def _request_rebuild(self):
        self._pending_rebuild = True
        self._debounce_timer.start()

    def _commit_rebuild(self):
        if self._pending_rebuild:
            self._pending_rebuild = False
            self.rebuild_requested.emit()

    def _rebuild_menus(self):
        self._populate_menus()

    def _setup_watchdog(self):
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class Handler(FileSystemEventHandler):
            def __init__(self, notify):
                super().__init__()
                self.notify = notify
            def on_any_event(self, event):
                self.notify()

        self.observer = Observer()
        handler = Handler(self._request_rebuild)
        roots = load_roots()
        for r in roots:
            if os.path.isdir(r):
                self.observer.schedule(handler, r, recursive=True)
        self.observer.start()

    def _quit(self):
        try:
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=2.0)
        except Exception:
            pass
        self.tray.setVisible(False)
        QApplication.quit()

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    if not os.path.exists(CFG_PATH):
        user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        default_folders = [
            os.path.join(user_profile, "Documents"),
            os.path.join(user_profile, "Downloads"),
            os.path.join(user_profile, "Desktop"),
        ]
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            for folder in default_folders:
                f.write(folder + "\n")
    TrayApp().run()
