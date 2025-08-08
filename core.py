#!/usr/bin/env python3
"""
Core system for Tasnuva TOS
Handles shell loop, command execution, and loading commands from SQLite
"""

import sqlite3
import os
import shlex

class Core:
    def __init__(self, vfs):
        self.vfs = vfs
        self.commands = {}
        self.init_commands_db()
        self.load_commands()
    
    def init_commands_db(self, force_reset=False):
        """Initialize commands database with default commands"""
        conn = sqlite3.connect('commands.db')
        cursor = conn.cursor()

        if force_reset:
            cursor.execute('DROP TABLE IF EXISTS commands')

        # Create commands table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL,
                function_code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Check if commands already exist
        cursor.execute('SELECT COUNT(*) FROM commands')
        if cursor.fetchone()[0] == 0:
            # Insert default commands
            default_commands = [
                ('ls', 'List directory contents', '''
def ls_command(args, vfs, core):
    path = args[0] if args else None
    contents = vfs.list_directory(path)
    if contents is None:
        return "ls: cannot access directory"
    
    if not contents:
        return ""
    
    result = []
    for name, file_type in contents:
        if file_type == 'directory':
            result.append(name + '/')
        else:
            result.append(name)
    
    return '  '.join(result)
'''),
                ('pwd', 'Print working directory', '''
def pwd_command(args, vfs, core):
    return vfs.get_current_directory()
'''),
                ('cd', 'Change directory', '''
def cd_command(args, vfs, core):
    if not args:
        path = '/'
    else:
        path = args[0]
    
    if vfs.change_directory(path):
        return ""
    else:
        return f"cd: {path}: No such directory"
'''),
                ('cat', 'Display file contents', '''
def cat_command(args, vfs, core):
    if not args:
        return "cat: missing file operand"
    
    content = vfs.read_file(args[0])
    if content is None:
        return f"cat: {args[0]}: No such file"
    
    return content.rstrip()
'''),
                ('echo', 'Display text', '''
def echo_command(args, vfs, core):
    if not args:
        return ""
    
    # Handle output redirection
    text = ' '.join(args)
    if '>' in args:
        redirect_idx = args.index('>')
        if redirect_idx == len(args) - 1:
            return "echo: missing filename for redirection"
        
        text = ' '.join(args[:redirect_idx])
        filename = args[redirect_idx + 1]
        
        if vfs.write_file(filename, text + '\\n'):
            return ""
        else:
            return f"echo: cannot write to {filename}"
    elif '>>' in args:
        redirect_idx = args.index('>>')
        if redirect_idx == len(args) - 1:
            return "echo: missing filename for redirection"
        
        text = ' '.join(args[:redirect_idx])
        filename = args[redirect_idx + 1]
        
        if vfs.write_file(filename, text + '\\n', append=True):
            return ""
        else:
            return f"echo: cannot write to {filename}"
    
    return text
'''),
                ('mkdir', 'Create directory', '''
def mkdir_command(args, vfs, core):
    if not args:
        return "mkdir: missing operand"
    
    for dirname in args:
        if not vfs.create_directory(dirname):
            return f"mkdir: cannot create directory '{dirname}'"
    
    return ""
'''),
                ('touch', 'Create empty file', '''
def touch_command(args, vfs, core):
    if not args:
        return "touch: missing file operand"
    
    for filename in args:
        if not vfs.write_file(filename, ""):
            return f"touch: cannot create '{filename}'"
    
    return ""
'''),
                ('rm', 'Remove files and directories', '''
def rm_command(args, vfs, core):
    if not args:
        return "rm: missing operand"
    
    for path in args:
        if not vfs.remove(path):
            if not vfs.exists(path):
                return f"rm: cannot remove '{path}': No such file or directory"
            elif vfs.is_directory(path):
                return f"rm: cannot remove '{path}': Directory not empty"
            else:
                return f"rm: cannot remove '{path}'"
    
    return ""
'''),
                ('help', 'Show available commands', '''
def help_command(args, vfs, core):
    commands_info = []
    conn = sqlite3.connect('commands.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, description FROM commands ORDER BY name')
    
    for name, desc in cursor.fetchall():
        commands_info.append(f"{name:10} - {desc}")
    
    conn.close()
    commands_info.append("exit       - Exit Tasnuva TOS")
    return '\\n'.join(commands_info)
'''),
                ('clear', 'Clear screen', '''
def clear_command(args, vfs, core):
    import os
    os.system('cls' if os.name == 'nt' else 'clear')
    return ""
'''),
                ('reset', 'Reset the system to its default state', '''
def reset_command(args, vfs, core):
    if '--confirm' in args:
        core.reset_core()
        return "System has been reset to default state."
    else:
        return "This is a destructive operation. Please run 'reset --confirm' to proceed."
''')
            ]
            
            for name, desc, code in default_commands:
                cursor.execute('''
                    INSERT INTO commands (name, description, function_code) 
                    VALUES (?, ?, ?)
                ''', (name, desc, code))
        
        conn.commit()
        conn.close()
    
    def load_commands(self):
        """Load commands from database into memory"""
        conn = sqlite3.connect('commands.db')
        cursor = conn.cursor()
        cursor.execute('SELECT name, function_code FROM commands')
        
        for name, code in cursor.fetchall():
            try:
                # Create a safe execution environment
                exec_globals = {
                    'sqlite3': sqlite3,
                    'os': os,
                    '__builtins__': {
                        'len': len,
                        'str': str,
                        'int': int,
                        'float': float,
                        'bool': bool,
                        'list': list,
                        'dict': dict,
                        'tuple': tuple,
                        'set': set,
                        'range': range,
                        'enumerate': enumerate,
                        'zip': zip,
                        'print': print,
                    }
                }
                exec_locals = {}
                
                # Execute the function code
                exec(code, exec_globals, exec_locals)
                
                # Find the function (should be named {name}_command)
                func_name = f"{name}_command"
                if func_name in exec_locals:
                    self.commands[name] = exec_locals[func_name]
                
            except Exception as e:
                print(f"Error loading command '{name}': {e}")
        
        conn.close()
    
    def execute_command(self, command_line):
        """Execute a command line"""
        if not command_line.strip():
            return ""
        
        try:
            # Parse command line
            parts = shlex.split(command_line)
            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            
            # Handle built-in exit command
            if command == 'exit':
                return 'EXIT'
            
            # Execute command if it exists
            if command in self.commands:
                try:
                    result = self.commands[command](args, self.vfs, self)
                    return result if result is not None else ""
                except Exception as e:
                    return f"Error executing {command}: {e}"
            else:
                return f"{command}: command not found"
                
        except Exception as e:
            return f"Error parsing command: {e}"
    
    def reset_core(self):
        """Reset the VFS and commands to their initial state."""
        # Reset the virtual filesystem
        self.vfs.reset_filesystem()
        
        # Force re-initialization of the commands database
        self.init_commands_db(force_reset=True)
        
        # Clear and reload commands into memory
        self.commands.clear()
        self.load_commands()

    def run_shell(self):
        """Main shell loop"""
        while True:
            try:
                # Show prompt
                current_dir = self.vfs.get_current_directory()
                prompt = f"Tasnuva TOS:{current_dir}$ "
                
                # Get user input
                command_line = input(prompt).strip()
                
                if not command_line:
                    continue
                
                # Execute command
                result = self.execute_command(command_line)
                
                # Handle exit
                if result == 'EXIT':
                    break
                
                # Display result
                if result:
                    print(result)
                    
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit Tasnuva TOS")
            except EOFError:
                break
