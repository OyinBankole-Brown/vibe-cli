#!/usr/bin/env python3
import sys
import subprocess
import argparse
import time
import os
import glob
import shutil
import tempfile
import signal
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
import yt_dlp

# --- Configuration ---
VIBES = {
    "lofi": "https://www.youtube.com/watch?v=jfKfPfyJRdk",  # Lofi Girl
    "synthwave": "https://www.youtube.com/watch?v=4xDzrJKXOOY", # Synthwave Radio
    "rain": "https://www.youtube.com/watch?v=mPZkdNFkNps", # Rainy Mood (or similar)
    "jazz": "https://www.youtube.com/watch?v=M5QY2_8704o", # Jazz
    "nature": "https://www.youtube.com/watch?v=eKFTSSKCzWA", # Nature sounds
}

PID_FILE = os.path.join(tempfile.gettempdir(), "vibe_ffplay.pid")
console = Console()

def find_ffplay():
    """
    Locates the ffplay executable.
    """
    # Check PATH first
    path = shutil.which("ffplay")
    if path:
        return path
    
    # Check Winget location (heuristic)
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        # Pattern: %LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\ffmpeg-*-full_build\bin\ffplay.exe
        pattern = os.path.join(local_appdata, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg_*", "ffmpeg-*-full_build", "bin", "ffplay.exe")
        matches = glob.glob(pattern)
        if matches:
            return matches[0] # Return first match
            
    return None

def get_stream_url(youtube_url):
    """
    Uses yt-dlp to extract the best audio stream URL.
    """
    ydl_options = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    
    with console.status("[bold green]Tuning in...[/bold green]", spinner="dots"):
        try:
            with yt_dlp.YoutubeDL(ydl_options) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                return info['url'], info.get('title', 'Unknown Title')
        except Exception as e:
            console.print(f"[bold red]Error extracting stream:[/bold red] {e}")
            return None, None

def save_pid(pid):
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(pid))
    except Exception as e:
        console.print(f"[bold red]Warning:[/bold red] Could not save PID file: {e}")

def get_pid():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                return int(f.read().strip())
    except:
        pass
    return None

def stop_vibes():
    """
    Stops any running ffplay instances using PID file and fallback.
    """
    # 1. Try PID file
    pid = get_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM) # Try nice kill
            # On Windows signal.SIGTERM is essentially TerminateProcess
            pass 
        except Exception as e:
            pass
        
        # Clean up file
        try:
            os.remove(PID_FILE)
        except:
            pass

    # 2. Nuclear option (Always run this to be safe, as per user feedback "music isn't stopping")
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/d", "/im", "ffplay.exe", "/f"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(["pkill", "ffplay"])
    except Exception:
        pass

def play_stream(stream_url):
    """
    Starts ffplay in a subprocess.
    """
    # Stop previous first!
    stop_vibes()
    
    ffplay_exe = find_ffplay()
    
    if not ffplay_exe:
         console.print("[bold red]Error:[/bold red] 'ffplay' is not found in PATH or standard locations. Please ensure FFmpeg is installed.")
         return None

    cmd = [
        ffplay_exe,
        "-nodisp",
        "-autoexit",
        "-loglevel", "quiet",
        stream_url
    ]
    
    try:
        if sys.platform == "win32":
            # DETACHED_PROCESS (0x00000008)
            creationflags = 0x00000008 
            process = subprocess.Popen(cmd, creationflags=creationflags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            
        if process:
            save_pid(process.pid)
            
        return process
    except Exception as e:
        console.print(f"[bold red]Error starting player:[/bold red] {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Vibe CLI - Background Audio Player")
    parser.add_argument("vibe", nargs="?", default="lofi", choices=VIBES.keys(), help="The vibe you want (default: lofi)")
    parser.add_argument("--stop", action="store_true", help="Stop any running instances")
    
    args = parser.parse_args()

    # CLI Mode
    if args.stop:
        stop_vibes()
        console.print("[bold yellow]Vibes stopped.[/bold yellow]")
        return
    
    vibe_url = VIBES[args.vibe]
    
    stream_url, title = get_stream_url(vibe_url)
    
    if stream_url:
        process = play_stream(stream_url)
        if process:
             # Rich UI
            panel = Panel(
                Text.assemble(
                    ("Focus Mode Active\n", "bold cyan"),
                    (f"Playing: {args.vibe} - {title}\n", "italic white"),
                    ("Running in background.", "dim")
                ),
                title="[bold magenta]VIBE CLI[/bold magenta]",
                border_style="magenta"
            )
            console.print(panel)
        else:
            console.print("[bold red]Failed to start player.[/bold red]")

if __name__ == "__main__":
    main()
