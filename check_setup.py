#!/usr/bin/env python3
"""
Quick validation check - run this to ensure basic setup is correct.
"""
import sys

def check_python_version():
    """Ensure Python 3.9+"""
    if sys.version_info < (3, 9):
        print("❌ Python 3.9 or higher required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✓ Python version: {sys.version.split()[0]}")
    return True

def check_imports():
    """Check if key packages can be imported"""
    packages = {
        'langchain': 'LangChain',
        'langgraph': 'LangGraph',
        'dotenv': 'python-dotenv',
    }
    
    all_ok = True
    for package, name in packages.items():
        try:
            __import__(package)
            print(f"✓ {name} installed")
        except ImportError:
            print(f"❌ {name} not installed")
            all_ok = False
    
    return all_ok

def check_env():
    """Check if .env file exists"""
    import os
    if os.path.exists('.env'):
        print("✓ .env file found")
        return True
    else:
        print("⚠ .env file not found")
        print("  Run: cp env.template .env")
        return False

def main():
    print("Quick Setup Check")
    print("=" * 50)
    
    python_ok = check_python_version()
    print()
    
    if python_ok:
        print("Checking packages...")
        imports_ok = check_imports()
        print()
        
        print("Checking configuration...")
        env_ok = check_env()
        print()
        
        if imports_ok and env_ok:
            print("=" * 50)
            print("✓ Basic setup looks good!")
            print("\nNext: Add your API keys to .env")
            print("Then: python main.py --mock --interactive")
        elif not imports_ok:
            print("=" * 50)
            print("⚠ Please install dependencies:")
            print("  pip install -r requirements.txt")
        else:
            print("=" * 50)
            print("⚠ Please complete setup:")
            print("  cp env.template .env")
            print("  # Then edit .env with your API keys")

if __name__ == "__main__":
    main()

