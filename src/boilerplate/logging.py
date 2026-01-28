import sys
from typing import Any, Callable, Optional
from rich.console import Console
from rich.theme import Theme

# Define professional theme
PIPELINE_THEME = Theme({
    "info": "dim white",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "stage": "bold blue reverse",
    "step": "bold blue",
    "command": "dim white",
    "highlight": "bold magenta",
})

class PipelineLogger:
    """Professional logger for pipeline execution logs using Rich."""
    
    def __init__(self, write_callback: Optional[Callable[[str], None]] = None):
        self.callback = write_callback
        # Initialize rich console with the theme and forcing ANSI for widget compatibility
        self.console = Console(
            theme=PIPELINE_THEME,
            force_terminal=True,
            force_interactive=False,
            color_system="standard", # Standard 8-color for best compatibility
            width=100,
            file=self # We act as the file to capture output
        )
        
    def write(self, text: str):
        """Standard write method so Rich can use this class as a file."""
        if self.callback:
            self.callback(text)
        else:
            sys.stdout.write(text)
            
    def flush(self):
        """Flush method for file-like interface."""
        pass

    def stage(self, name: str):
        """Major pipeline stage header."""
        self.console.print()
        self.console.print(f" {name.upper()} ", style="stage")
        self.console.print()

    def step(self, text: str):
        """Step within a stage."""
        self.console.print(f"❯ [step]{text}[/step]")

    def info(self, text: str):
        """Informational message."""
        self.console.print(f"ℹ [info]{text}[/info]")

    def success(self, text: str):
        """Success message."""
        self.console.print(f"✓ [success]{text}[/success]")

    def warning(self, text: str):
        """Warning message."""
        self.console.print(f"⚠ [warning]{text}[/warning]")

    def error(self, text: str):
        """Error message."""
        self.console.print(f"✘ [error]{text}[/error]")

    def command(self, cmd: str):
        """Log a command being executed."""
        self.console.print(f"  [command]$ {cmd}[/command]")

    def plain(self, text: str):
        """Plain text without symbols."""
        self.console.print(text)

    def indent(self, text: str, level: int = 1):
        """Indented text."""
        prefix = "  " * level
        self.console.print(f"{prefix}{text}")
