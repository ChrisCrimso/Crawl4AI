# FIU Recrawling Tool

This tool recrawls all problematic files from FIU websites using the Playwright-based crawler, compares the results with the original files, and migrates successfully recrawled content back to the FIU_content directory.

## Prerequisites

1. Install the required dependencies:
   ```
   pip install -r requirements_crawler.txt
   playwright install
   ```

2. Ensure the following directories exist:
   - `404_issues` - Contains the problematic files from the original crawler
   - `FIU_content` - The main content directory where fixed files will be migrated

## Quick Start

The easiest way to run the entire process is to use the batch file:

```
recrawl_and_migrate.bat
```

This will:
1. Run the Playwright crawler on all problematic files
2. Generate comparison reports
3. Migrate successfully recrawled files to FIU_content

## Manual Usage

If you prefer more control over the process, you can run each step manually:

### Step 1: Recrawl problematic files

```
python recrawl_all_issues.py [options]
```

Options:
- `--directory NAME` - Process only a specific directory (e.g., Athletics, MainSite)
- `--sample N` - Process only N random files from each directory
- `--wait SECONDS` - Wait time after page load (default: 8 seconds)
- `--timeout MS` - Timeout for navigation in milliseconds (default: 60000)
- `--remove-failed` - Remove files that failed to crawl
- `--no-confirm` - Do not ask for confirmation when removing files

### Step 2: Migrate successfully recrawled files

```
python migrate_successful_crawls.py [options]
```

Options:
- `--report PATH` - Path to a specific comparison report (default: use the latest)

## Understanding the Results

After running the tools, check the following:

1. `comparison_results/comparison_report_*.html` - Visual HTML report showing successful and failed crawls
2. `comparison_results/comparison_report_*.json` - Detailed JSON data about all crawls
3. `comparison_results/migration_log.json` - Information about files migrated to FIU_content
4. `logs/*.log` - Detailed logs from each step of the process

## Troubleshooting

If you encounter issues:

1. Check the log files in the `logs` directory
2. Try increasing the timeout (`--timeout`) for slower websites
3. Try increasing the wait time (`--wait`) for JavaScript-heavy pages
4. Run the process on a specific directory to isolate issues

## Removing Failed Files

If you want to remove files that still can't be crawled:

```
python recrawl_all_issues.py --remove-failed
```

This will:
1. Back up the files to `backup_removed_files` directory
2. Remove the original files from `404_issues` 