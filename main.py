#!/usr/bin/env python3
"""
Tasnuva TOS - A simulated terminal operating system
Entry point that boots the system and starts the shell
"""

import os
import sys
from core import Core
from vfs import VFS

def show_banner():
    """Display ASCII banner for TASNUVA"""
    banner = """
 ########  #####  ####### ###    ## ##    ## ##    ##  ##### 
    ##    ##   ## ##      ####   ## ##    ## ##    ## ##   ##
    ##    ####### ####### ## ##  ## ##    ## ##    ## #######
    ##    ##   ##      ## ##  ## ## ##    ##  ##  ##  ##   ##
    ##    ##   ## ####### ##   ####  ######    ####   ##   ##

     Tasnuva TOS (Othoy Edition)- Terminal Operating System
     ======================================================
    """
    print(banner)

def boot_system():
    """Boot the Tasnuva TOS system"""
    print("Booting Tasnuva TOS...")
    
    # Initialize Virtual File System
    print("Mounting Virtual File System...")
    vfs = VFS()
    
    # Initialize Core System
    print("Loading Core System...")
    core = Core(vfs)
    
    print("System ready!")
    print("Type 'help' for available commands or 'exit' to quit.\n")
    
    return core

def main():
    """Main entry point"""
    try:
        # Show boot banner
        show_banner()
        
        # Boot system components
        core = boot_system()
        
        # Start shell loop
        core.run_shell()
        
    except KeyboardInterrupt:
        print("\n\nSystem shutdown requested...")
    except Exception as e:
        print(f"System error: {e}")
        sys.exit(1)
    
    print("Tasnuva TOS shutdown complete.")

if __name__ == "__main__":
    main()
