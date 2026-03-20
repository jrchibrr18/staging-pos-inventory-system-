"""
Set your POS/Store name before building or deploying.
Run this script to customize the name shown in the app, receipts, and login page.
Default: POS System
"""
import json
import os

# Use project root (same folder as this script)
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pos_config.json')


def set_pos_name(name=None):
    """
    Set the POS/store name. Saves to pos_config.json.
    
    Args:
        name: Your POS/store name. If None, prompts for input.
    
    Returns:
        str: The name that was set.
    """
    if name is None:
        current = _load_current_name()
        prompt = f"Enter your POS/Store name [{current}]: "
        name = input(prompt).strip() or current
    
    if not name:
        name = "POS System"
    
    config = {"POS_NAME": name}
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    return name


def _load_current_name():
    """Load current name from config file if it exists."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('POS_NAME', data.get('pos_name', 'POS System'))
        except (json.JSONDecodeError, OSError):
            pass
    return "POS System"


def get_pos_name():
    """Get the current POS name from config."""
    return _load_current_name()


if __name__ == '__main__':
    print("=== POS System - Set Store Name ===\n")
    saved = set_pos_name()
    print(f"\nSaved! Your POS name is set to: {saved}")
    print(f"Config file: {CONFIG_FILE}")
    print("\nRun build.bat (or build.sh) to build with this name.")
