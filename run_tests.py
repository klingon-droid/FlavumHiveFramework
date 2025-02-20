import unittest
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_report.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_test_suite() -> Dict:
    """Run all tests and return results"""
    # Discover and load all tests
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Prepare result collection
    result = unittest.TestResult()
    start_time = time.time()
    
    # Run tests
    suite.run(result)
    end_time = time.time()
    
    return {
        'total': result.testsRun,
        'failures': len(result.failures),
        'errors': len(result.errors),
        'skipped': len(result.skipped),
        'success': result.wasSuccessful(),
        'run_time': end_time - start_time,
        'failures_detail': result.failures,
        'errors_detail': result.errors
    }

def generate_report(results: Dict) -> str:
    """Generate a detailed test report"""
    report = []
    report.append("=" * 80)
    report.append(f"Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    report.append(f"\nTest Summary:")
    report.append(f"Total Tests: {results['total']}")
    report.append(f"Passed: {results['total'] - results['failures'] - results['errors']}")
    report.append(f"Failed: {results['failures']}")
    report.append(f"Errors: {results['errors']}")
    report.append(f"Skipped: {results['skipped']}")
    report.append(f"Run Time: {results['run_time']:.2f} seconds")
    report.append(f"Overall Status: {'SUCCESS' if results['success'] else 'FAILURE'}")
    
    if results['failures']:
        report.append("\nFailures:")
        for test, trace in results['failures_detail']:
            report.append(f"\n{test}")
            report.append("-" * 40)
            report.append(trace)
    
    if results['errors']:
        report.append("\nErrors:")
        for test, trace in results['errors_detail']:
            report.append(f"\n{test}")
            report.append("-" * 40)
            report.append(trace)
    
    return "\n".join(report)

def main():
    """Run tests and generate report"""
    logger.info("Starting test run")
    
    try:
        # Ensure test directory exists
        if not Path('tests').exists():
            logger.error("Tests directory not found")
            return 1
        
        # Run tests
        results = run_test_suite()
        
        # Generate and save report
        report = generate_report(results)
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Test report generated: {report_file}")
        print("\n" + report)
        
        # Return appropriate exit code
        return 0 if results['success'] else 1
    
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 