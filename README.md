# TrayFolders

A Windows system tray application that provides quick access to folder contents through an expandable menu with file icons.

## Description

TrayFolders is a lightweight system tray utility built with PySide6 that monitors a specified folder and displays its contents in a convenient right-click menu. It features:

- **System Tray Integration**: Runs quietly in the Windows system tray
- **Dynamic Menu**: Automatically updates when files are added, removed, or modified
- **File Icons**: Displays appropriate icons for folders and files
- **Quick Access**: Open files and folders with a single click
- **Folder Monitoring**: Uses watchdog to detect changes in real-time

## Features

- Monitor any folder on your system
- Expandable context menu with file/folder listings
- Alphabetical sorting (folders first, then files)
- Hides hidden files (files starting with '.')
- Clean, native Windows interface
- Minimal resource usage

## Requirements

- Python 3.7 or higher
- Windows OS
- PySide6
- watchdog

## Installation

1. Clone this repository:
```bash
git clone https://github.com/Danneman92/TrayFolders.git
cd TrayFolders
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run with default folder (Documents):
```bash
python main.py
```

### Specify Custom Folder

Monitor a specific folder:
```bash
python main.py "C:\Path\To\Your\Folder"
```

### Examples

```bash
# Monitor Downloads folder
python main.py "C:\Users\YourName\Downloads"

# Monitor a project folder
python main.py "C:\Projects\MyProject"
```

## How It Works

1. The application creates a system tray icon
2. Right-click the icon to see the folder contents
3. Click any file or folder to open it with the default application
4. The menu automatically updates when files change
5. Use "Open Folder" to open the monitored folder
6. Select "Exit" to close the application

## Building an Executable (Optional)

To create a standalone executable:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=icon.ico main.py
```

The executable will be created in the `dist` folder.

## License

MIT License - Feel free to use and modify as needed.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
