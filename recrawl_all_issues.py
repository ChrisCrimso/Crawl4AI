#!/usr/bin/env python3
"""
Script to recrawl all problematic files across all FIU websites using the improved
Playwright crawler. After crawling, it will identify which files were successfully
crawled and which ones still have issues.
"""

import os
import glob
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime
import subprocess
from tqdm import tqdm

# Constants
ISSUES_DIR = "404_issues"
RECRAWLED_DIR = "recrawled_content"
COMPARISON_DIR = "comparison_results"
LOG_DIR = "logs"

def ensure_dir(directory):
    """Ensure a directory exists."""
    Path(directory).mkdir(parents=True, exist_ok=True)

def get_issue_directories():
    """Get all directories in the issues folder."""
    if not os.path.exists(ISSUES_DIR):
        print(f"Error: {ISSUES_DIR} directory not found!")
        return []
        
    dirs = [d for d in os.listdir(ISSUES_DIR) 
            if os.path.isdir(os.path.join(ISSUES_DIR, d))]
    
    return dirs

def count_files_in_directory(directory):
    """Count the number of markdown files in a directory."""
    return len(glob.glob(os.path.join(directory, "**", "*.md"), recursive=True))

def run_crawler_on_directory(directory, sample_size=None, wait_time=8, timeout=60000):
    """Run the Playwright crawler on a specific directory."""
    cmd = ["python", "playwright_crawler.py", 
           "--directory", directory,
           "--wait", str(wait_time),
           "--timeout", str(timeout)]
    
    if sample_size:
        cmd.extend(["--sample", str(sample_size)])
    
    print(f"\nRunning crawler on {directory}...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        log_file = os.path.join(LOG_DIR, f"crawler_{directory}_{datetime.now().strftime('%Y%m%d%H%M%S')}.log")
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n\nERRORS:\n")
                f.write(result.stderr)
        
        print(f"Log saved to {log_file}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error running crawler on {directory}: {str(e)}")
        return False

def run_comparison():
    """Run the comparison tool."""
    print("\nRunning comparison tool...")
    try:
        result = subprocess.run(["python", "compare_crawls.py"], 
                               capture_output=True, text=True)
        
        log_file = os.path.join(LOG_DIR, f"comparison_{datetime.now().strftime('%Y%m%d%H%M%S')}.log")
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n\nERRORS:\n")
                f.write(result.stderr)
        
        print(f"Comparison log saved to {log_file}")
        
        # Find the most recent comparison report
        json_reports = glob.glob(os.path.join(COMPARISON_DIR, "*.json"))
        if json_reports:
            latest_report = max(json_reports, key=os.path.getctime)
            return latest_report
        
        return None
    except Exception as e:
        print(f"Error running comparison: {str(e)}")
        return None

def analyze_results(report_file):
    """Analyze the comparison report to identify successful and failed crawls."""
    if not report_file or not os.path.exists(report_file):
        print("No comparison report found.")
        return None, None
        
    with open(report_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    successful = [item for item in data["comparisons"] if item["crawl_success"]]
    failed = [item for item in data["comparisons"] if not item["crawl_success"]]
    
    print("\nResults Summary:")
    print(f"Total files processed: {len(data['comparisons'])}")
    print(f"Successfully crawled: {len(successful)} ({len(successful)/len(data['comparisons'])*100:.2f}%)")
    print(f"Failed to crawl: {len(failed)} ({len(failed)/len(data['comparisons'])*100:.2f}%)")
    
    if data["summary"]["avg_improvement"] > 0:
        print(f"Average content improvement: {data['summary']['avg_improvement']:.2f}%")
    
    return successful, failed

def remove_failed_files(failed_files, confirm=True):
    """Remove files that failed to be crawled."""
    if not failed_files:
        print("No failed files to remove.")
        return
        
    print(f"\nPreparing to remove {len(failed_files)} files that couldn't be crawled.")
    
    if confirm:
        response = input("Do you want to continue? (y/n): ")
        if response.lower() != 'y':
            print("Aborted file removal.")
            return
    
    removed = 0
    for item in tqdm(failed_files, desc="Removing files"):
        original_file = item["original_file"]
        if os.path.exists(original_file):
            try:
                # Create a backup directory
                backup_dir = os.path.join("backup_removed_files", 
                                         os.path.dirname(original_file).replace(ISSUES_DIR, "").strip(os.sep))
                ensure_dir(backup_dir)
                
                # Copy to backup before removing
                backup_file = os.path.join(backup_dir, os.path.basename(original_file))
                shutil.copy2(original_file, backup_file)
                
                # Remove the file
                os.remove(original_file)
                removed += 1
            except Exception as e:
                print(f"Error removing {original_file}: {str(e)}")
    
    print(f"Removed {removed} files. Backups saved in 'backup_removed_files' directory.")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Recrawl all problematic files across FIU websites.'
    )
    parser.add_argument('--sample', type=int, default=None,
                        help='If provided, only process this many files per directory')
    parser.add_argument('--wait', type=float, default=8,
                        help='Wait time after page load (seconds)')
    parser.add_argument('--timeout', type=int, default=60000,
                        help='Timeout for navigation in milliseconds')
    parser.add_argument('--remove-failed', action='store_true',
                        help='Remove files that failed to crawl')
    parser.add_argument('--no-confirm', action='store_true',
                        help='Do not ask for confirmation when removing files')
    parser.add_argument('--directory', type=str, default=None,
                        help='Process only this specific directory')
    args = parser.parse_args()
    
    # Ensure directories exist
    ensure_dir(RECRAWLED_DIR)
    ensure_dir(COMPARISON_DIR)
    ensure_dir(LOG_DIR)
    ensure_dir("backup_removed_files")
    
    # Get issue directories
    if args.directory:
        directories = [args.directory]
    else:
        directories = get_issue_directories()
    
    if not directories:
        print("No issue directories found.")
        return
        
    print(f"Found {len(directories)} issue directories:")
    for d in directories:
        file_count = count_files_in_directory(os.path.join(ISSUES_DIR, d))
        print(f"  - {d}: {file_count} files")
    
    # Process each directory
    for directory in directories:
        run_crawler_on_directory(
            directory, 
            sample_size=args.sample,
            wait_time=args.wait,
            timeout=args.timeout
        )
    
    # Run comparison
    report_file = run_comparison()
    
    # Analyze results
    successful, failed = analyze_results(report_file)
    
    # Remove failed files if requested
    if args.remove_failed and failed:
        remove_failed_files(failed, confirm=not args.no_confirm)
    
    print("\nProcessing complete!")
    
if __name__ == "__main__":
    main() 