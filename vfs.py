#!/usr/bin/env python3
"""
Virtual File System (VFS) for Tasnuva TOS
Manages virtual filesystem stored in SQLite database
"""

import sqlite3
import os
from pathlib import Path

class VFS:
    def __init__(self, db_path="vfs.db"):
        self.db_path = db_path
        self.current_path = "/"
        self.init_database()
    
    def init_database(self):
        """Initialize VFS database with default structure"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create filesystem table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS filesystem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('file', 'directory')),
                content TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create root directory if it doesn't exist
        cursor.execute('SELECT COUNT(*) FROM filesystem WHERE path = ?', ('/',))
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO filesystem (path, name, type) 
                VALUES ('/', 'root', 'directory')
            ''')
            
            # Create some default directories
            default_dirs = ['/home', '/tmp', '/usr', '/var']
            for dir_path in default_dirs:
                cursor.execute('''
                    INSERT INTO filesystem (path, name, type) 
                    VALUES (?, ?, 'directory')
                ''', (dir_path, os.path.basename(dir_path)))
            
            # Create a welcome file
            cursor.execute('''
                INSERT INTO filesystem (path, name, type, content) 
                VALUES ('/welcome.txt', 'welcome.txt', 'file', ?)
            ''', ('Welcome to Tasnuva TOS!\nThis is a virtual filesystem.\nTry commands like ls, cd, mkdir, touch, cat, echo, rm.\n',))
        
        conn.commit()
        conn.close()
    
    def normalize_path(self, path):
        """Normalize path to absolute path"""
        if not path.startswith('/'):
            # Relative path
            if self.current_path == '/':
                path = '/' + path
            else:
                path = self.current_path + '/' + path
        
        # Resolve . and .. components
        parts = []
        for part in path.split('/'):
            if part == '' or part == '.':
                continue
            elif part == '..':
                if parts:
                    parts.pop()
            else:
                parts.append(part)
        
        return '/' + '/'.join(parts) if parts else '/'
    
    def exists(self, path):
        """Check if path exists"""
        path = self.normalize_path(path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM filesystem WHERE path = ?', (path,))
        exists = cursor.fetchone()[0] > 0
        conn.close()
        return exists
    
    def is_directory(self, path):
        """Check if path is a directory"""
        path = self.normalize_path(path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT type FROM filesystem WHERE path = ?', (path,))
        result = cursor.fetchone()
        conn.close()
        return result and result[0] == 'directory'
    
    def is_file(self, path):
        """Check if path is a file"""
        path = self.normalize_path(path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT type FROM filesystem WHERE path = ?', (path,))
        result = cursor.fetchone()
        conn.close()
        return result and result[0] == 'file'
    
    def list_directory(self, path=None):
        """List contents of directory"""
        if path is None:
            path = self.current_path
        path = self.normalize_path(path)
        
        if not self.exists(path) or not self.is_directory(path):
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get direct children
        if path == '/':
            pattern = '/[^/]*'
        else:
            pattern = path + '/[^/]*'
        
        cursor.execute('''
            SELECT name, type FROM filesystem 
            WHERE path GLOB ? AND path != ?
            ORDER BY type DESC, name
        ''', (pattern, path))
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def read_file(self, path):
        """Read file content"""
        path = self.normalize_path(path)
        
        if not self.exists(path) or not self.is_file(path):
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT content FROM filesystem WHERE path = ?', (path,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def write_file(self, path, content, append=False):
        """Write content to file"""
        path = self.normalize_path(path)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if self.exists(path):
            if not self.is_file(path):
                conn.close()
                return False  # Cannot write to directory
            
            if append:
                cursor.execute('SELECT content FROM filesystem WHERE path = ?', (path,))
                existing = cursor.fetchone()[0] or ''
                content = existing + content
            
            cursor.execute('''
                UPDATE filesystem 
                SET content = ?, modified_at = CURRENT_TIMESTAMP 
                WHERE path = ?
            ''', (content, path))
        else:
            # Create new file
            name = os.path.basename(path)
            cursor.execute('''
                INSERT INTO filesystem (path, name, type, content) 
                VALUES (?, ?, 'file', ?)
            ''', (path, name, content))
        
        conn.commit()
        conn.close()
        return True
    
    def create_directory(self, path):
        """Create directory"""
        path = self.normalize_path(path)
        
        if self.exists(path):
            return False  # Already exists
        
        # Check parent directory exists
        parent = os.path.dirname(path)
        if parent != path and not self.exists(parent):
            return False  # Parent doesn't exist
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        name = os.path.basename(path)
        cursor.execute('''
            INSERT INTO filesystem (path, name, type) 
            VALUES (?, ?, 'directory')
        ''', (path, name))
        conn.commit()
        conn.close()
        return True
    
    def remove(self, path):
        """Remove file or directory"""
        path = self.normalize_path(path)
        
        if not self.exists(path):
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if self.is_directory(path):
            # Check if directory is empty
            if path == '/':
                pattern = '/[^/]*'
            else:
                pattern = path + '/[^/]*'
            
            cursor.execute('SELECT COUNT(*) FROM filesystem WHERE path GLOB ?', (pattern,))
            if cursor.fetchone()[0] > 0:
                conn.close()
                return False  # Directory not empty
        
        cursor.execute('DELETE FROM filesystem WHERE path = ?', (path,))
        conn.commit()
        conn.close()
        return True
    
    def change_directory(self, path):
        """Change current directory"""
        path = self.normalize_path(path)
        
        if not self.exists(path) or not self.is_directory(path):
            return False
        
        self.current_path = path
        return True
    
    def get_current_directory(self):
        """Get current directory path"""
        return self.current_path
    
    def reset_filesystem(self):
        """Reset filesystem to default state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Drop and recreate the filesystem table
        cursor.execute('DROP TABLE IF EXISTS filesystem')
        
        # Recreate table structure
        cursor.execute('''
            CREATE TABLE filesystem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('file', 'directory')),
                content TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Reset current path
        self.current_path = "/"
        
        # Recreate default structure
        cursor.execute('''
            INSERT INTO filesystem (path, name, type) 
            VALUES ('/', 'root', 'directory')
        ''')
        
        # Create default directories
        default_dirs = ['/home', '/tmp', '/usr', '/var']
        for dir_path in default_dirs:
            cursor.execute('''
                INSERT INTO filesystem (path, name, type) 
                VALUES (?, ?, 'directory')
            ''', (dir_path, os.path.basename(dir_path)))
        
        # Create welcome file
        cursor.execute('''
            INSERT INTO filesystem (path, name, type, content) 
            VALUES ('/welcome.txt', 'welcome.txt', 'file', ?)
        ''', ('Welcome to Tasnuva TOS!\nThis is a virtual filesystem.\nTry commands like ls, cd, mkdir, touch, cat, echo, rm.\n',))
        
        conn.commit()
        conn.close()
        return True
