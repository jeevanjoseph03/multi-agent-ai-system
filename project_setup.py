# First, let's create our project structure
import os

def create_project_structure():
    directories = [
        "multi_agent_system",
        "multi_agent_system/agents",
        "multi_agent_system/memory",
        "multi_agent_system/routers", 
        "multi_agent_system/utils",
        "multi_agent_system/apis",
        "samples",
        "samples/emails",
        "samples/pdfs", 
        "samples/jsons",
        "tests",
        "docs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")

# Run this to create your project structure
if __name__ == "__main__":
    create_project_structure()