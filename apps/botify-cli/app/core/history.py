import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import os

from .config import settings


class ChatHistoryManager:
    """Manager for chat history operations."""
    
    def __init__(self, history_file: Optional[str] = None):
        """Initialize the chat history manager.
        
        Args:
            history_file: Optional override for the history file path.
        """
        self.history_file = history_file or settings.history_file
    
    def save_conversation(self, user_message: str, assistant_response: Dict[str, str]) -> None:
        """Save a conversation exchange to the history file.
        
        Args:
            user_message: The user's message.
            assistant_response: The assistant's response.
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(self.history_file)), exist_ok=True)
        
        # Format the conversation entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "assistant_response": assistant_response
        }
        
        # Append to the history file
        with open(self.history_file, "a", encoding="utf-8") as file:
            file.write(json.dumps(entry) + "\n")
    
    def load_history(self, max_entries: int = 10) -> List[Dict[str, Any]]:
        """Load conversation history from the file.
        
        Args:
            max_entries: Maximum number of history entries to load (most recent).
            
        Returns:
            A list of conversation entries.
        """
        if not os.path.exists(self.history_file):
            return []
        
        # Load entries from the file
        entries = []
        try:
            with open(self.history_file, "r", encoding="utf-8") as file:
                for line in file:
                    try:
                        entry = json.loads(line.strip())
                        entries.append(entry)
                    except json.JSONDecodeError:
                        # Skip invalid JSON lines
                        continue
        except Exception:
            # Return empty list if there's an error reading the file
            return []
        
        # Return the most recent entries (up to max_entries)
        return entries[-max_entries:] if max_entries > 0 else entries
    
    def clear_history(self) -> bool:
        """Clear the chat history file.
        
        Returns:
            True if the history was cleared successfully, False otherwise.
        """
        try:
            if os.path.exists(self.history_file):
                os.remove(self.history_file)
            return True
        except Exception:
            return False


# Create a single instance of the history manager
history_manager = ChatHistoryManager()