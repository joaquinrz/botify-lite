import json
import sys
import time
from typing import Optional, Dict, Any, List

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from rich.table import Table

from ..api.client import api_client
from ..core.config import settings
from ..core.history import history_manager


class ChatTerminal:
    """Interactive chat terminal using Rich for UI components."""
    
    def __init__(self):
        """Initialize the chat terminal."""
        self.console = Console()
        self.streaming_buffer = ""
    
    def display_welcome(self) -> None:
        """Display a welcome message when starting the chat application."""
        welcome_message = """
        # Botify CLI
        
        Welcome to the Botify CLI application. Type your messages and get responses from the Botify Assistant.
        
        - Type your message and press Enter to chat with the Assistant
        - Type `/history` to view chat history
        - Type `/clear` to clear chat history
        - Type `/stream on` or `/stream off` to toggle streaming mode
        - Type `/exit` or `/quit` to exit the application
        """
        
        self.console.print(Panel(Markdown(welcome_message.strip()), 
                                 title="Welcome", 
                                 border_style="blue"))
    
    def display_history(self, max_entries: int = 5) -> None:
        """Display recent chat history.
        
        Args:
            max_entries: Maximum number of history entries to display.
        """
        history = history_manager.load_history(max_entries)
        
        if not history:
            self.console.print(Panel("No chat history found.", 
                                    title="Chat History", 
                                    border_style="yellow"))
            return
        
        table = Table(title=f"Recent Chat History (Last {min(max_entries, len(history))} Conversations)")
        table.add_column("Time", style="cyan")
        table.add_column("You", style="green")
        table.add_column("Assistant", style="blue")
        
        for entry in history:
            timestamp = entry.get("timestamp", "Unknown")
            # Format timestamp for display (just the time part)
            try:
                formatted_time = timestamp.split("T")[1][:8]  # Extract HH:MM:SS
            except (IndexError, AttributeError):
                formatted_time = timestamp
                
            user_msg = entry.get("user_message", "")
            # Truncate user message if too long
            user_msg = user_msg[:50] + "..." if len(user_msg) > 50 else user_msg
            
            assistant_response = entry.get("assistant_response", {})
            voice_summary = assistant_response.get("voiceSummary", "")
            # Truncate assistant response if too long
            voice_summary = voice_summary[:50] + "..." if len(voice_summary) > 50 else voice_summary
            
            table.add_row(formatted_time, user_msg, voice_summary)
        
        self.console.print(table)
    
    def handle_command(self, command: str) -> bool:
        """Handle special commands.
        
        Args:
            command: The command to process.
            
        Returns:
            True if the application should continue, False if it should exit.
        """
        cmd_lower = command.lower().strip()
        
        if cmd_lower in ["/exit", "/quit"]:
            self.console.print("[yellow]Exiting chat application. Goodbye![/yellow]")
            return False
        
        elif cmd_lower == "/history":
            self.display_history()
            return True
        
        elif cmd_lower == "/clear":
            result = history_manager.clear_history()
            if result:
                self.console.print("[green]Chat history cleared successfully.[/green]")
            else:
                self.console.print("[red]Failed to clear chat history.[/red]")
            return True
        
        elif cmd_lower == "/stream on":
            # Enable streaming mode
            settings.use_streaming = True
            self.console.print("[green]Streaming mode enabled.[/green]")
            return True
        
        elif cmd_lower == "/stream off":
            # Disable streaming mode
            settings.use_streaming = False
            self.console.print("[green]Streaming mode disabled.[/green]")
            return True
        
        # Not a recognized command
        return None
    
    def format_response(self, response: Dict[str, str]) -> str:
        """Format the assistant's response for display.
        
        Args:
            response: The response from the assistant.
            
        Returns:
            Formatted response string.
        """
        voice_summary = response.get("voiceSummary", "")
        display_response = response.get("displayResponse", "")
        
        if not display_response:
            return voice_summary
        
        return display_response
    
    def chat_non_streaming(self, message: str) -> None:
        """Handle non-streaming chat interaction.
        
        Args:
            message: The user message to send.
        """
        try:
            # Start timing the response
            start_time = time.time()
            
            with self.console.status("[bold blue]Waiting for response...[/bold blue]"):
                response = api_client.chat(message)
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Display the raw response JSON
            self.console.print("[blue]Assistant:[/blue]")
            raw_response = json.dumps(response, indent=2)
            self.console.print(raw_response, highlight=False)
            
            # Display elapsed time
            self.console.print(f"[dim italic]Response time: {elapsed_time:.2f} seconds[/dim italic]")
            
            # Save to history
            history_manager.save_conversation(message, response)
            
        except Exception as e:
            self.console.print(f"[bold red]Error:[/bold red] {str(e)}")
    
    def chat_streaming(self, message: str) -> None:
        """Handle streaming chat interaction by displaying raw tokens directly.
        
        Args:
            message: The user message to send.
        """
        try:
            # Start timing the response
            start_time = time.time()
            
            # Initialize buffer for accumulated response for history
            accumulated_raw_text = ""
            
            # Start response display
            self.console.print("[blue]Assistant (streaming):[/blue]")
            
            # Process the stream and display chunks immediately exactly as received
            try:
                # Print characters directly without any processing
                for chunk in api_client.chat_stream(message):
                    # Print the chunk exactly as it arrives from backend
                    self.console.print(chunk, end="", highlight=False)
                    # Also accumulate for history
                    accumulated_raw_text += chunk
                
                # Print a final newline
                self.console.print()
                
                # Calculate and display elapsed time
                elapsed_time = time.time() - start_time
                self.console.print(f"[dim italic]Response time: {elapsed_time:.2f} seconds[/dim italic]")
                    
            except Exception as e:
                self.console.print(f"\n[bold red]Error during streaming:[/bold red] {str(e)}")
            
            # After streaming completes, save to history - using raw unprocessed text
            try:
                # Just save the raw text without parsing
                history_response = {
                    "voiceSummary": accumulated_raw_text[:100] + ("..." if len(accumulated_raw_text) > 100 else ""),
                    "displayResponse": accumulated_raw_text
                }
                history_manager.save_conversation(message, history_response)
                    
            except Exception as e:
                self.console.print(f"[bold red]Error saving to history:[/bold red] {str(e)}")
                
        except Exception as e:
            self.console.print(f"[bold red]Error:[/bold red] {str(e)}")
    
    def start_chat_loop(self) -> None:
        """Start the main chat interaction loop."""
        self.display_welcome()
        
        while True:
            # Get user input
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            # Check if this is a command
            command_result = self.handle_command(user_input)
            if command_result is not None:  # It was a command
                if not command_result:  # Command says to exit
                    break
                continue  # Skip to next iteration
            
            # Process regular chat message
            if settings.use_streaming:
                self.chat_streaming(user_input)
            else:
                self.chat_non_streaming(user_input)


# Create a single instance of the chat terminal
chat_terminal = ChatTerminal()