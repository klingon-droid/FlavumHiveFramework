#!/bin/bash

# Remove temporary and test files
rm -f twitter_test.db
rm -f twitter_comprehensive_test.db
rm -f twitter_post_error.png
rm -f twitter_login_error.png
rm -f twitter_dry_run_test.log
rm -f twitter_comprehensive_test.log
rm -f test_report_*.txt
rm -f test_report.log
rm -f integration_test.log
rm -f bot.log

# Remove redundant test files
rm -f test_twitter_dry_run.py
rm -f test_twitter_basic.py
rm -f test_twitter_comprehensive.py
rm -f run_twitter_test.sh

# Remove old/unused files
rm -f requirements-eliza.txt
rm -f app.py
rm -f bot.db

# Clean up debug files
rm -rf debug_twitter/*

# Clean up cache directories
rm -rf __pycache__/
rm -rf .pytest_cache/
find . -type d -name "__pycache__" -exec rm -r {} +

echo "Cleanup complete!" 