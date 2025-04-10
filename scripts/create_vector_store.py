#!/usr/bin/env python
"""
Vector Store Creation Script for Botify Lite

This script creates an Azure OpenAI vector store and loads all JSON files
from the data directory into the store. It outputs the vector store ID
which should be added to your credentials.env file.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# Add the project root to Python path so we can import from the apps directory
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from openai import AzureOpenAI
except ImportError:
    print("OpenAI package not found. Please run 'poetry install' first.")
    sys.exit(1)

# Load environment variables
def load_env_variables() -> Dict[str, str]:
    """Load environment variables from credentials.env file"""
    env_vars = {}
    env_file = project_root / "apps" / "credentials.env"
    
    if not env_file.exists():
        print(f"Error: {env_file} not found. Please create it from credentials.env.template")
        sys.exit(1)
    
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip().strip("\"'")
    
    return env_vars

# Validate required environment variables
def validate_env_vars(env_vars: Dict[str, str]) -> None:
    """Validate that required environment variables are present"""
    required_vars = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_API_VERSION"]
    missing_vars = [var for var in required_vars if var not in env_vars or not env_vars[var]]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please update your credentials.env file.")
        sys.exit(1)

# Get all JSON files from the data directory
def get_json_files(data_dir: Path) -> List[Path]:
    """Get all JSON files from the data directory"""
    json_files = list(data_dir.glob("*.json"))
    
    if not json_files:
        print(f"Error: No JSON files found in {data_dir}")
        sys.exit(1)
    
    print(f"Found {len(json_files)} JSON files in the data directory")
    return json_files

def main() -> None:
    """Main function to create vector store and load data"""
    # Load and validate environment variables
    env_vars = load_env_variables()
    validate_env_vars(env_vars)
    
    # Initialize Azure OpenAI client
    client = AzureOpenAI(
        api_key=env_vars["AZURE_OPENAI_API_KEY"],
        api_version=env_vars["AZURE_OPENAI_API_VERSION"],
        azure_endpoint=env_vars["AZURE_OPENAI_ENDPOINT"]
    )
    
    # Set up paths
    data_dir = project_root / "data"
    
    # Get JSON files
    print("Finding JSON files in data directory...")
    json_files = get_json_files(data_dir)
    
    # Create vector store name with timestamp for uniqueness
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    vector_store_name = f"Botify_Knowledge_Base_{timestamp}"
    
    try:
        # Create vector store
        print(f"Creating vector store '{vector_store_name}'...")
        vector_store = client.vector_stores.create(name=vector_store_name)
        vector_store_id = vector_store.id
        print(f"Vector store created successfully with ID: {vector_store_id}")
        
        # Open file streams for upload
        print(f"Preparing {len(json_files)} files for upload...")
        file_paths = [str(file_path) for file_path in json_files]
        file_streams = [open(path, "rb") for path in file_paths]
        
        # Upload files to vector store and poll for completion
        print(f"Uploading files to vector store...")
        file_batch = client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store_id,
            files=file_streams
        )
        
        # Close all file streams
        for file_stream in file_streams:
            file_stream.close()
        
        # Print results
        print(f"Vector store load status: {file_batch.file_counts.completed}")
        print(f"Files processed: {file_batch.file_counts.completed} succeeded, "
              f"{file_batch.file_counts.failed} failed")
        
        # Print instructions for using the vector store
        print("\n" + "="*80)
        print("NEXT STEPS:")
        print(f"1. Add the following line to your credentials.env file:")
        print(f"AZURE_OPENAI_VECTOR_STORE_ID={vector_store_id}")
        print("2. Restart your application to use the new vector store")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"Error: Failed to create or load vector store: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
