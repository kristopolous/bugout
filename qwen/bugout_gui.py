#!/usr/bin/env python3
"""
bugout_gui.py - BugOut Graphical User Interface

A wxPython GUI for the BugOut automated bug fix workflow.
"""

import wx
import wx.adv
import threading
import queue
import json
import os
import sys
import io
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

SYMBOLS = {
    "success": "✓",
    "error": "✗",
    "warning": "⚠",
    "info": "ℹ",
    "bug": "🐛",
    "rocket": "🚀",
    "check": "✅",
    "star": "★",
    "sparkle": "✨",
}


class LogPanel(wx.Panel):
    """Panel for displaying log output with syntax highlighting."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.log_text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.log_text.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        
        # Define text attributes for different log levels
        self.attr_normal = wx.TextAttr(wx.BLACK)
        self.attr_success = wx.TextAttr(wx.Colour(0, 128, 0))  # Green
        self.attr_error = wx.TextAttr(wx.Colour(200, 0, 0))    # Red
        self.attr_info = wx.TextAttr(wx.Colour(0, 100, 200))   # Blue
        self.attr_warning = wx.TextAttr(wx.Colour(200, 150, 0))  # Orange
        self.attr_bold = wx.TextAttr(wx.BLACK)
        self.attr_bold.SetFontWeight(wx.FONTWEIGHT_BOLD)
        self.attr_dim = wx.TextAttr(wx.Colour(100, 100, 100))
        self.attr_dim.SetFontStyle(wx.FONTSTYLE_ITALIC)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.log_text, 1, wx.EXPAND)
        self.SetSizer(sizer)
    
    def write_line(self, text, attr=None):
        """Write a line of text to log - MUST be called from main thread."""
        if attr is None:
            attr = self.attr_normal
        self.log_text.SetDefaultStyle(attr)
        self.log_text.AppendText(text + "\n")
    
    def clear(self):
        """Clear the log."""
        self.log_text.Clear()
    
    def log_success(self, text):
        wx.CallAfter(self.write_line, f"  {SYMBOLS['check']} {text}", self.attr_success)
    
    def log_error(self, text):
        wx.CallAfter(self.write_line, f"  {SYMBOLS['error']} {text}", self.attr_error)
    
    def log_info(self, text):
        wx.CallAfter(self.write_line, f"  {SYMBOLS['info']} {text}", self.attr_info)
    
    def log_warning(self, text):
        wx.CallAfter(self.write_line, f"  {SYMBOLS['warning']} {text}", self.attr_warning)
    
    def log_header(self, text):
        wx.CallAfter(self.write_line, f"\n{text}\n", self.attr_bold)
    
    def log_dim(self, text):
        wx.CallAfter(self.write_line, text, self.attr_dim)
    
    def log_raw(self, text):
        """Log raw text with ANSI code parsing."""
        wx.CallAfter(self._parse_and_log, text)
    
    def _parse_and_log(self, text):
        """Parse ANSI codes and log with appropriate style."""
        # Strip ANSI codes
        clean_text = re.sub(r'\033\[[0-9;]*m', '', text)
        
        if not clean_text.strip():
            return
        
        # Determine style based on content
        if '✓' in text or 'complete' in text.lower():
            attr = self.attr_success
        elif '✗' in text or 'error' in text.lower() or 'failed' in text.lower():
            attr = self.attr_error
        elif '⚠' in text or 'warning' in text.lower():
            attr = self.attr_warning
        elif '●' in text or '━' in text:
            attr = self.attr_bold
        elif '→' in text:
            attr = self.attr_dim
        else:
            attr = self.attr_normal
        
        self.write_line(clean_text, attr)


class CapturingWriter:
    """Thread-safe file-like object that captures output and sends to log panel."""
    
    def __init__(self, log_panel, msg_queue):
        self.log_panel = log_panel
        self.msg_queue = msg_queue
        self.buffer = ""
        self._lock = threading.Lock()
    
    def write(self, text):
        """Capture text and queue for main thread."""
        with self._lock:
            self.buffer += text
            # Process complete lines
            while '\n' in self.buffer:
                line, self.buffer = self.buffer.split('\n', 1)
                if line.strip():
                    # Send to queue for main thread processing
                    self.msg_queue.put({"type": "log", "text": line})
    
    def flush(self):
        """Flush buffer."""
        with self._lock:
            if self.buffer:
                self.msg_queue.put({"type": "log", "text": self.buffer})
                self.buffer = ""
    
    def isatty(self):
        return False


class ConfigPanel(wx.Panel):
    """Panel for configuration inputs."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # Repository input
        repo_label = wx.StaticText(self, label="Repository:")
        self.repo_input = wx.TextCtrl(self, value="microsoft/vscode")
        self.repo_input.SetToolTip("GitHub repository in format owner/repo")
        
        # Issue number input
        issue_label = wx.StaticText(self, label="Issue Number:")
        self.issue_input = wx.TextCtrl(self, value="")
        self.issue_input.SetToolTip("GitHub issue number")
        
        # Output directory
        dir_label = wx.StaticText(self, label="Output Directory:")
        self.dir_input = wx.TextCtrl(self, value="./bugout_data")
        self.dir_input.SetToolTip("Directory to store output files")
        dir_browse_btn = wx.Button(self, label="Browse...")
        dir_browse_btn.Bind(wx.EVT_BUTTON, self.on_browse_dir)
        
        # Layout
        grid_sizer = wx.GridBagSizer(vgap=10, hgap=10)
        grid_sizer.Add(repo_label, pos=(0, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        grid_sizer.Add(self.repo_input, pos=(0, 1), span=(1, 2), flag=wx.EXPAND)
        
        grid_sizer.Add(issue_label, pos=(1, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        grid_sizer.Add(self.issue_input, pos=(1, 1), span=(1, 2), flag=wx.EXPAND)
        
        grid_sizer.Add(dir_label, pos=(2, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        grid_sizer.Add(self.dir_input, pos=(2, 1), flag=wx.EXPAND)
        grid_sizer.Add(dir_browse_btn, pos=(2, 2), flag=wx.EXPAND)
        
        grid_sizer.AddGrowableCol(1)
        self.SetSizer(grid_sizer)
    
    def on_browse_dir(self, event):
        """Open directory browser."""
        dlg = wx.DirDialog(self, "Choose output directory", 
                          defaultPath=str(Path(self.dir_input.GetValue()).absolute()),
                          style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON)
        if dlg.ShowModal() == wx.ID_OK:
            self.dir_input.SetValue(dlg.GetPath())
        dlg.Destroy()
    
    def get_config(self):
        """Get configuration values."""
        return {
            "repo": self.repo_input.GetValue().strip(),
            "issue": self.issue_input.GetValue().strip(),
            "output_dir": self.dir_input.GetValue().strip()
        }


class StatusPanel(wx.Panel):
    """Panel for displaying current status."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.status_label = wx.StaticText(self, label="Status: Ready")
        self.progress_bar = wx.Gauge(self, range=100, size=(-1, 20))
        self.step_label = wx.StaticText(self, label="Step: 0/8")
        self.run_id_label = wx.StaticText(self, label="Run ID: -")
        
        # Status colors
        self.status_label.SetFont(wx.Font(11, wx.DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.status_label, 0, wx.EXPAND | wx.BOTTOM, 5)
        sizer.Add(self.progress_bar, 0, wx.EXPAND | wx.BOTTOM, 5)
        sizer.Add(self.step_label, 0, wx.EXPAND | wx.BOTTOM, 5)
        sizer.Add(self.run_id_label, 0, wx.EXPAND)
        
        self.SetSizer(sizer)
    
    def update_status(self, status, step=None, total_steps=8, run_id=None):
        """Update status display."""
        self.status_label.SetLabel(f"Status: {status}")
        if step is not None:
            self.step_label.SetLabel(f"Step: {step}/{total_steps}")
            self.progress_bar.SetValue(int((step / total_steps) * 100))
        if run_id:
            self.run_id_label.SetLabel(f"Run ID: {run_id}")
        
        # Color coding
        if status == "Running":
            self.status_label.SetForegroundColour(wx.Colour(0, 100, 200))
        elif status == "Complete":
            self.status_label.SetForegroundColour(wx.Colour(0, 128, 0))
        elif status == "Failed":
            self.status_label.SetForegroundColour(wx.Colour(200, 0, 0))
        else:
            self.status_label.SetForegroundColour(wx.BLACK)


class BugOutFrame(wx.Frame):
    """Main BugOut application frame."""
    
    def __init__(self):
        super().__init__(None, title="🐛 BugOut - Automated Bug Fix Workflow", size=(1000, 700))
        
        # Set frame icon (if available)
        self.SetBackgroundColour(wx.Colour(245, 245, 245))
        
        # Message queue for thread-safe logging
        self.msg_queue = queue.Queue()
        self.is_running = False
        self.original_stdout = None
        self.original_stderr = None
        self.capturing_writer = None
        
        # Create UI
        self._create_menu()
        self._create_ui()
        
        # Start message processor
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._process_messages, self.timer)
        self.timer.Start(100)  # Check queue every 100ms
        
        # Center on screen
        self.Centre()
    
    def _create_menu(self):
        """Create menu bar."""
        menubar = wx.MenuBar()
        
        # File menu
        file_menu = wx.Menu()
        open_item = file_menu.Append(wx.ID_OPEN, "&Open Run...\tCtrl+O", "Open existing run")
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, "E&xit\tCtrl+Q", "Exit application")
        menubar.Append(file_menu, "&File")
        
        # Help menu
        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, "&About", "About BugOut")
        menubar.Append(help_menu, "&Help")
        
        self.SetMenuBar(menubar)
        
        # Bind events
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)
        self.Bind(wx.EVT_MENU, self.on_open, open_item)
    
    def _create_ui(self):
        """Create user interface."""
        # Main sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Header with logo
        header_panel = self._create_header()
        main_sizer.Add(header_panel, 0, wx.EXPAND | wx.ALL, 10)
        
        # Configuration panel
        config_panel = ConfigPanel(self)
        self.config_panel = config_panel
        main_sizer.Add(config_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        # Status panel
        status_panel = StatusPanel(self)
        self.status_panel = status_panel
        main_sizer.Add(status_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        # Log panel
        log_label = wx.StaticText(self, label="Output Log:")
        log_label.SetFont(wx.Font(11, wx.DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        main_sizer.Add(log_label, 0, wx.LEFT | wx.TOP, 10)
        
        self.log_panel = LogPanel(self)
        main_sizer.Add(self.log_panel, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        # Control buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.run_btn = wx.Button(self, label="🚀 Run BugOut", size=(150, 40))
        self.run_btn.SetFont(wx.Font(12, wx.DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.run_btn.SetBackgroundColour(wx.Colour(0, 120, 215))
        self.run_btn.SetForegroundColour(wx.WHITE)
        self.run_btn.Bind(wx.EVT_BUTTON, self.on_run)
        button_sizer.Add(self.run_btn, 0, wx.RIGHT, 10)
        
        self.stop_btn = wx.Button(self, label="⏹ Stop", size=(100, 40))
        self.stop_btn.Enable(False)
        self.stop_btn.Bind(wx.EVT_BUTTON, self.on_stop)
        button_sizer.Add(self.stop_btn, 0, wx.RIGHT, 10)
        
        self.clear_btn = wx.Button(self, label="🗑 Clear Log", size=(120, 40))
        self.clear_btn.Bind(wx.EVT_BUTTON, lambda e: self.log_panel.clear())
        button_sizer.Add(self.clear_btn)
        
        main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 20)
        
        self.SetSizer(main_sizer)
    
    def _create_header(self):
        """Create header panel with logo."""
        panel = wx.Panel(self)
        panel.SetBackgroundColour(wx.Colour(50, 50, 80))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Try to load logo
        logo_path = Path(__file__).parent.parent / "logo.ansiart"
        logo_text = ""
        if logo_path.exists():
            with open(logo_path, 'r') as f:
                logo_text = f.read().strip()
        
        if logo_text:
            logo_label = wx.StaticText(panel, label=logo_text)
            logo_label.SetForegroundColour(wx.Colour(100, 200, 255))
            logo_label.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            sizer.Add(logo_label, 0, wx.ALIGN_CENTER | wx.TOP, 10)
        
        title_label = wx.StaticText(panel, label="🐛 BugOut - Automated Bug Fix Workflow")
        title_label.SetForegroundColour(wx.WHITE)
        title_label.SetFont(wx.Font(16, wx.DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title_label, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        subtitle_label = wx.StaticText(panel, label="From bug report to production-ready patch")
        subtitle_label.SetForegroundColour(wx.Colour(200, 200, 200))
        sizer.Add(subtitle_label, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        
        panel.SetSizer(sizer)
        return panel
    
    def _process_messages(self, event):
        """Process queued messages from worker thread."""
        while not self.msg_queue.empty():
            try:
                msg = self.msg_queue.get_nowait()
                msg_type = msg.get("type", "normal")
                text = msg.get("text", "")
                
                if msg_type == "log":
                    # Raw log output from capturing writer
                    self.log_panel.log_raw(text)
                elif msg_type == "success":
                    self.log_panel.log_success(text)
                elif msg_type == "error":
                    self.log_panel.log_error(text)
                elif msg_type == "info":
                    self.log_panel.log_info(text)
                elif msg_type == "warning":
                    self.log_panel.log_warning(text)
                elif msg_type == "header":
                    self.log_panel.log_header(text)
                elif msg_type == "status":
                    self.status_panel.update_status(
                        text, 
                        msg.get("step"),
                        msg.get("total_steps", 8),
                        msg.get("run_id")
                    )
                elif msg_type == "complete":
                    self._on_complete(msg.get("success", False), msg.get("patch_folder"))
                else:
                    self.log_panel.write_line(text)
            except queue.Empty:
                break
    
    def on_run(self, event):
        """Start BugOut workflow."""
        config = self.config_panel.get_config()
        
        # Validate inputs
        if not config["repo"]:
            wx.MessageBox("Please enter a repository (format: owner/repo)", "Validation Error", 
                         wx.ICON_ERROR | wx.OK)
            return
        
        if not config["issue"]:
            wx.MessageBox("Please enter an issue number", "Validation Error", 
                         wx.ICON_ERROR | wx.OK)
            return
        
        # Check environment
        if not self._check_environment():
            return
        
        # Update UI state
        self.is_running = True
        self.run_btn.Enable(False)
        self.stop_btn.Enable(True)
        self.config_panel.Enable(False)
        self.log_panel.clear()
        
        # Log header with configuration
        self.log_panel.log_header(f"🐛 BugOut Workflow Started")
        self.log_panel.log_info(f"Repository: {config['repo']}")
        self.log_panel.log_info(f"Issue: #{config['issue']}")
        self.log_panel.log_info(f"Output: {config['output_dir']}")
        self.log_panel.log_dim("─" * 60)
        
        # Create capturing writer for stdout/stderr
        self.capturing_writer = CapturingWriter(self.log_panel, self.msg_queue)
        
        # Start worker thread
        self.status_panel.update_status("Running")
        thread = threading.Thread(target=self._run_bugout, args=(config,))
        thread.daemon = True
        thread.start()
    
    def on_stop(self, event):
        """Stop running workflow."""
        self.is_running = False
        self._reset_ui()
        self.log_panel.log_warning("Process stopped by user")
    
    def on_exit(self, event):
        """Exit application."""
        if self.is_running:
            dlg = wx.MessageDialog(self, "A process is still running. Are you sure you want to exit?",
                                  "Confirm Exit", wx.YES_NO | wx.ICON_WARNING)
            if dlg.ShowModal() != wx.ID_YES:
                return
        self.Close()
    
    def on_about(self, event):
        """Show about dialog."""
        info = wx.adv.AboutDialogInfo()
        info.Name = "BugOut"
        info.Version = "1.0.0"
        info.Description = "Automated Bug Fix Workflow\n\nFrom bug report to production-ready patch in 8 steps."
        info.Developers = ["BugOut Team"]
        info.WebSite = ("https://github.com/bugout", "BugOut GitHub")
        wx.adv.AboutBox(info)
    
    def on_open(self, event):
        """Open existing run directory."""
        dlg = wx.DirDialog(self, "Choose run directory", 
                          defaultPath="./bugout_data",
                          style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            run_dir = Path(dlg.GetPath())
            self._open_run_directory(run_dir)
        dlg.Destroy()
    
    def _open_run_directory(self, run_dir):
        """Open and display an existing run directory."""
        self.log_panel.clear()
        self.log_panel.log_header(f"Opening run: {run_dir}")
        
        # Load metadata
        metadata_file = run_dir / "run_metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            self.log_panel.log_success(f"Run ID: {metadata.get('run_id', 'N/A')}")
            self.log_panel.log_info(f"Repository: {metadata.get('repo', 'N/A')}")
            self.log_panel.log_info(f"Issue: #{metadata.get('issue_number', 'N/A')}")
            self.log_panel.log_info(f"Timestamp: {metadata.get('timestamp', 'N/A')}")
        
        # List artifacts
        self.log_panel.log_header("Artifacts:")
        for f in sorted(run_dir.glob("*")):
            if f.is_file():
                self.log_panel.log_info(f"  📄 {f.name}")
            elif f.is_dir():
                self.log_panel.log_info(f"  📁 {f.name}/")
    
    def _check_environment(self):
        """Check required environment variables."""
        missing = []
        
        if not os.environ.get("FASTINO_KEY"):
            missing.append("FASTINO_KEY")
        if not os.environ.get("YUTORI_KEY"):
            missing.append("YUTORI_KEY")
        if not os.environ.get("OPENAI_HOST"):
            missing.append("OPENAI_HOST")
        if not os.environ.get("OPENAI_MODEL"):
            missing.append("OPENAI_MODEL")
        
        if missing:
            wx.MessageBox(
                f"Missing environment variables:\n\n" + "\n".join(missing) + 
                "\n\nPlease check your .env file.",
                "Configuration Error",
                wx.ICON_ERROR | wx.OK
            )
            return False
        
        # Check gh CLI
        import subprocess
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            wx.MessageBox(
                "GitHub CLI (gh) not found.\n\nPlease install from: https://cli.github.com/",
                "Missing Dependency",
                wx.ICON_ERROR | wx.OK
            )
            return False
        
        return True
    
    def _run_bugout(self, config):
        """Run BugOut workflow in background thread."""
        # Save original stdout/stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        try:
            # Redirect stdout/stderr to our capturing writer
            sys.stdout = self.capturing_writer
            sys.stderr = self.capturing_writer
            
            # Import bugout module
            from bugout import run_bugout

            # Run workflow
            success, patch_folder = run_bugout(
                config["repo"],
                config["issue"],
                Path(config["output_dir"]) if config["output_dir"] else None
            )

            # Queue completion message
            self.msg_queue.put({
                "type": "complete",
                "success": success,
                "patch_folder": str(patch_folder) if patch_folder else None
            })

        except Exception as e:
            self.msg_queue.put({"type": "error", "text": f"Error: {str(e)}"})
            self.msg_queue.put({"type": "complete", "success": False})
        
        finally:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.capturing_writer.flush()
    
    def _on_complete(self, success, patch_folder):
        """Handle workflow completion."""
        self._reset_ui()
        
        if success:
            self.status_panel.update_status("Complete")
            self.log_panel.log_header("🎉 BugOut Complete!")
            self.log_panel.log_success(f"Patch folder: {patch_folder}")
            
            # Offer to open folder
            dlg = wx.MessageDialog(
                self,
                f"BugOut completed successfully!\n\nPatch folder: {patch_folder}\n\nOpen folder?",
                "Success",
                wx.YES_NO | wx.ICON_INFORMATION
            )
            if dlg.ShowModal() == wx.ID_YES:
                import subprocess
                subprocess.run(["xdg-open", patch_folder])
            dlg.Destroy()
        else:
            self.status_panel.update_status("Failed")
            self.log_panel.log_error("BugOut workflow failed")
    
    def _reset_ui(self):
        """Reset UI to initial state."""
        self.is_running = False
        self.run_btn.Enable(True)
        self.stop_btn.Enable(False)
        self.config_panel.Enable(True)


class BugOutApp(wx.App):
    """BugOut application."""
    
    def OnInit(self):
        self.frame = BugOutFrame()
        self.frame.Show(True)
        return True


def main():
    """Main entry point."""
    app = BugOutApp(False)
    app.MainLoop()


if __name__ == "__main__":
    main()
