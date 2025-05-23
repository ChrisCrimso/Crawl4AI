#!/usr/bin/env python3
"""
This script identifies and removes markdown files that have 
'Error generating fit markdown' or similar generation errors.
"""

import os
import re
import glob
import shutil
from tqdm import tqdm
from datetime import datetime

# Directories to search
DIRECTORIES = ["fiu_content", "crawl_errors", "normalized_urls", "fixed_urls"]
BACKUP_DIR = "backup_removed_files"
ERROR_PATTERNS = [
    r"Error generating fit markdown",
    r"Error generating markdown",
    r"Failed to generate markdown",
    r"Could not generate markdown",
    r"Markdown generation error"
]

def file_has_error(file_path):
    """Check if a file contains any of the error patterns."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Check for error patterns
        for pattern in ERROR_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return True
                
        return False
    except Exception as e:
        print(f"Error reading {file_path}: {str(e)}")
        return False

def backup_file(file_path, backup_dir=BACKUP_DIR):
    """Make a backup of the file before removing it."""
    try:
        # Create relative path structure in backup directory
        dir_name = os.path.basename(os.path.dirname(os.path.dirname(file_path)))
        rel_path = os.path.join(dir_name, os.path.relpath(file_path, os.path.dirname(os.path.dirname(file_path))))
        backup_path = os.path.join(backup_dir, rel_path)
        
        # Ensure backup directory exists
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # Copy file to backup
        shutil.copy2(file_path, backup_path)
        
        return backup_path
    except Exception as e:
        print(f"Error backing up {file_path}: {str(e)}")
        return None

def main():
    """Find and remove files with markdown generation errors."""
    # Ensure backup directory exists
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Track removed files
    removed_files = []
    
    # Process each directory
    for directory in DIRECTORIES:
        if not os.path.exists(directory):
            print(f"Directory {directory} does not exist, skipping.")
            continue
            
        print(f"Searching for error files in {directory}...")
        
        # Find all markdown files
        md_files = glob.glob(f"{directory}/**/*.md", recursive=True)
        print(f"Found {len(md_files)} markdown files")
        
        # Check each file
        for file_path in tqdm(md_files):
            if file_has_error(file_path):
                print(f"Found error in {file_path}")
                
                # Backup file before removing
                backup_path = backup_file(file_path)
                
                if backup_path:
                    # Remove the file
                    try:
                        os.remove(file_path)
                        removed_files.append({
                            'file_path': file_path,
                            'backup_path': backup_path,
                            'directory': directory
                        })
                        print(f"Removed {file_path} (backup at {backup_path})")
                    except Exception as e:
                        print(f"Error removing {file_path}: {str(e)}")
    
    # Print summary
    print(f"\nRemoved {len(removed_files)} files with markdown generation errors")
    print(f"Backups saved to {BACKUP_DIR} directory")
    
    # Create removal report
    report_path = os.path.join(BACKUP_DIR, 'removal_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Markdown Error Files Removal Report\n\n")
        f.write(f"**Removal Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Removed {len(removed_files)} files with markdown generation errors.\n\n")
        
        # Group by directory
        by_directory = {}
        for item in removed_files:
            dir_name = item['directory']
            by_directory[dir_name] = by_directory.get(dir_name, 0) + 1
        
        f.write("## Files Removed by Directory\n\n")
        for dir_name, count in by_directory.items():
            f.write(f"- **{dir_name}:** {count} files\n")
        
        f.write("\n## Details of Removed Files\n\n")
        for item in removed_files:
            file_name = os.path.basename(item['file_path'])
            f.write(f"### {file_name}\n")
            f.write(f"- **Original Path:** `{item['file_path']}`\n")
            f.write(f"- **Backup Path:** `{item['backup_path']}`\n")
            f.write(f"- **Directory:** {item['directory']}\n\n")
    
    print(f"Removal report written to {report_path}")
    
    # Create batch file to restore all files if needed
    restore_path = os.path.join(BACKUP_DIR, 'restore_removed_files.bat')
    with open(restore_path, 'w', encoding='utf-8') as f:
        f.write("@echo off\n")
        f.write("echo Restoring removed markdown files...\n\n")
        
        for item in removed_files:
            source = item['backup_path'].replace('/', '\\')
            dest = item['file_path'].replace('/', '\\')
            dest_dir = os.path.dirname(dest)
            
            f.write(f'if not exist "{dest_dir}" mkdir "{dest_dir}"\n')
            f.write(f'copy "{source}" "{dest}"\n')
        
        f.write("\necho Restoration complete.\n")
        f.write("pause\n")
    
    print(f"Restoration batch file created at {restore_path}")

if __name__ == "__main__":
    main() 