#!/usr/bin/env python3
import os
import typer
from typing import Optional
from rich.console import Console

from .core.config import settings
from .ui.terminal import chat_terminal
from .api.client import api_client

# Create Typer app
app = typer.Typer(help="Botify CLI - Interactive Assistant Client")
console = Console()


def main(
    server: Optional[str] = typer.Option(
        None, "--server", "-s", help="Backend server URL"
    ),
    streaming: Optional[bool] = typer.Option(
        None, "--stream/--no-stream", help="Enable or disable streaming mode"
    ),
    history_file: Optional[str] = typer.Option(
        None, "--history", "-h", help="Custom chat history file location"
    )
):
    """Start the interactive chat session with the Botify Assistant."""
    try:
        # Override settings if command-line options are provided
        if server:
            api_client.base_url = server
        
        if streaming is not None:
            settings.use_streaming = streaming
            
        # Start the chat loop
        chat_terminal.start_chat_loop()
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    typer.run(main)