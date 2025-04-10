import os
import json
import tempfile
import pytest
from unittest.mock import patch

from app.core.history import ChatHistoryManager


@pytest.fixture
def temp_history_file():
    """Create a temporary file for testing history manager."""
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = temp_file.name
    
    # Return the path and clean up after the test
    yield temp_path
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def history_manager(temp_history_file):
    """Create a history manager that uses the temporary file."""
    return ChatHistoryManager(history_file=temp_history_file)


@pytest.fixture
def sample_response():
    """Create a sample assistant response for testing."""
    return {
        "voiceSummary": "This is a test summary",
        "displayResponse": "This is a detailed test response."
    }


def test_save_conversation(history_manager, temp_history_file, sample_response):
    """Test saving a conversation exchange to the history file."""
    # Save a conversation
    history_manager.save_conversation("Hello, assistant", sample_response)
    
    # Check that the file exists
    assert os.path.exists(temp_history_file)
    
    # Read the file and verify its contents
    with open(temp_history_file, "r") as file:
        content = file.read().strip()
        entry = json.loads(content)
        
        # Check that the entry has the expected fields
        assert "timestamp" in entry
        assert entry["user_message"] == "Hello, assistant"
        assert entry["assistant_response"] == sample_response


def test_load_history(history_manager, temp_history_file, sample_response):
    """Test loading conversation history from the file."""
    # Save multiple conversations
    for i in range(3):
        history_manager.save_conversation(f"Message {i}", sample_response)
    
    # Load the history
    history = history_manager.load_history()
    
    # Check that we got the expected number of entries
    assert len(history) == 3
    
    # Check the contents of the entries
    for i, entry in enumerate(history):
        assert entry["user_message"] == f"Message {i}"
        assert entry["assistant_response"] == sample_response


def test_load_history_with_limit(history_manager, temp_history_file, sample_response):
    """Test loading conversation history with a limit on the number of entries."""
    # Save multiple conversations
    for i in range(5):
        history_manager.save_conversation(f"Message {i}", sample_response)
    
    # Load limited history (only 2 most recent)
    history = history_manager.load_history(max_entries=2)
    
    # Check that we got only 2 entries (the most recent)
    assert len(history) == 2
    
    # Check that they are the most recent entries
    assert history[0]["user_message"] == "Message 3"
    assert history[1]["user_message"] == "Message 4"


def test_load_history_empty_file(history_manager, temp_history_file):
    """Test loading history from an empty file."""
    # Ensure the file exists but is empty
    open(temp_history_file, "w").close()
    
    # Load the history
    history = history_manager.load_history()
    
    # Check that we got an empty list
    assert history == []


def test_load_history_nonexistent_file(history_manager):
    """Test loading history when the file doesn't exist."""
    # Set a non-existent file path
    history_manager.history_file = "/path/to/nonexistent/file.json"
    
    # Load the history
    history = history_manager.load_history()
    
    # Check that we got an empty list
    assert history == []


def test_clear_history(history_manager, temp_history_file, sample_response):
    """Test clearing the chat history."""
    # Save a conversation
    history_manager.save_conversation("Hello", sample_response)
    
    # Verify that the file exists
    assert os.path.exists(temp_history_file)
    
    # Clear the history
    result = history_manager.clear_history()
    
    # Check that the operation was successful
    assert result is True
    
    # Verify that the file no longer exists
    assert not os.path.exists(temp_history_file)


def test_clear_history_error(history_manager):
    """Test handling errors when clearing history."""
    # Mock os.remove to raise an exception
    with patch("os.remove", side_effect=Exception("Test error")):
        result = history_manager.clear_history()
        
        # Check that the operation failed
        assert result is False