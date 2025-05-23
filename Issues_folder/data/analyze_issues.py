#!/usr/bin/env python3
"""
Analyze the issues log file and provide statistics on the types of issues
and their distribution across different directories.
"""

import os
import re
from collections import Counter

# Log file path
LOG_FILE = os.path.join("404_issues", "issues_log.txt")

def analyze_issues():
    """
    Analyze the issues log and return statistics.
    """
    if not os.path.exists(LOG_FILE):
        print(f"Error: Log file not found at {LOG_FILE}")
        return
        
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        log_content = f.read()
    
    # Extract basic stats from the header
    total_files_match = re.search(r"Total files checked: (\d+)", log_content)
    total_files = int(total_files_match.group(1)) if total_files_match else 0
    
    issue_files_match = re.search(r"Files with potential issues: (\d+)", log_content)
    issue_files = int(issue_files_match.group(1)) if issue_files_match else 0
    
    # Extract all file paths and reasons
    file_reason_pattern = re.compile(r"([\w\\]+\.md)\nReason: (.+?)\n\n", re.DOTALL)
    file_reason_matches = file_reason_pattern.findall(log_content)
    
    # Count issues by directory
    directory_counts = Counter()
    for file_path, _ in file_reason_matches:
        directory = file_path.split('\\')[0] if '\\' in file_path else "Unknown"
        directory_counts[directory] += 1
    
    # Count issues by reason
    reason_counts = Counter()
    for _, reason in file_reason_matches:
        reason_counts[reason] += 1
    
    return {
        "total_files": total_files,
        "issue_files": issue_files,
        "issue_percentage": (issue_files / total_files * 100) if total_files else 0,
        "directory_counts": directory_counts,
        "reason_counts": reason_counts
    }

def print_stats(stats):
    """
    Print the statistics in a readable format.
    """
    print("=" * 80)
    print(f"ISSUE ANALYSIS SUMMARY")
    print("=" * 80)
    
    print(f"\nTotal files checked: {stats['total_files']}")
    print(f"Files with potential issues: {stats['issue_files']} ({stats['issue_percentage']:.2f}%)")
    
    print("\n" + "-" * 40)
    print("Issues by directory:")
    print("-" * 40)
    
    for directory, count in sorted(stats["directory_counts"].items(), key=lambda x: x[1], reverse=True):
        percentage = count / stats["issue_files"] * 100
        print(f"{directory:<20} {count:>8} ({percentage:>6.2f}%)")
    
    print("\n" + "-" * 40)
    print("Issues by reason:")
    print("-" * 40)
    
    for reason, count in sorted(stats["reason_counts"].items(), key=lambda x: x[1], reverse=True):
        percentage = count / stats["issue_files"] * 100
        print(f"{reason:<40} {count:>8} ({percentage:>6.2f}%)")
    
    print("\n" + "=" * 80)

def main():
    """Main function."""
    stats = analyze_issues()
    if stats:
        print_stats(stats)
        
        # Write stats to file
        stats_file = os.path.join("404_issues", "issues_stats.txt")
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"ISSUE ANALYSIS SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Total files checked: {stats['total_files']}\n")
            f.write(f"Files with potential issues: {stats['issue_files']} ({stats['issue_percentage']:.2f}%)\n\n")
            
            f.write("-" * 40 + "\n")
            f.write("Issues by directory:\n")
            f.write("-" * 40 + "\n")
            
            for directory, count in sorted(stats["directory_counts"].items(), key=lambda x: x[1], reverse=True):
                percentage = count / stats["issue_files"] * 100
                f.write(f"{directory:<20} {count:>8} ({percentage:>6.2f}%)\n")
            
            f.write("\n" + "-" * 40 + "\n")
            f.write("Issues by reason:\n")
            f.write("-" * 40 + "\n")
            
            for reason, count in sorted(stats["reason_counts"].items(), key=lambda x: x[1], reverse=True):
                percentage = count / stats["issue_files"] * 100
                f.write(f"{reason:<40} {count:>8} ({percentage:>6.2f}%)\n")
            
            f.write("\n" + "=" * 80 + "\n")
        
        print(f"\nStatistics written to {stats_file}")

if __name__ == "__main__":
    main() 