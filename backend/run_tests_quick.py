#!/usr/bin/env python3
"""
Quick test runner for the Loan Extraction System.

Runs all tests in a single pass for faster execution.
"""
import subprocess
import sys
import time
from pathlib import Path

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_ascii_art():
    """Display ASCII art banner."""
    art = f"""
{Colors.OKCYAN}{Colors.BOLD}
╔═════════════════════════════════════════════════════════════╗
║                                                             ║
║   ⚡ QUICK TEST RUNNER ⚡                                   ║
║   Loan Document Extraction System                          ║
║                                                             ║
╚═════════════════════════════════════════════════════════════╝
{Colors.ENDC}"""
    print(art)


def main():
    """Main test runner."""
    print_ascii_art()

    # Change to backend directory
    backend_dir = Path(__file__).parent
    print(f"{Colors.OKCYAN}Working directory: {backend_dir}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}Running all tests in single pass...{Colors.ENDC}\n")

    start_time = time.time()

    # Run all tests with coverage
    result = subprocess.run(
        [
            "pytest",
            "tests/",
            "-v",
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--timeout=30",
        ],
        check=False,
    )

    duration = time.time() - start_time

    print(f"\n{Colors.BOLD}{Colors.OKBLUE}{'═' * 70}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}⏱  Total Duration: {duration:.2f}s{Colors.ENDC}")

    if result.returncode == 0:
        print(f"{Colors.BOLD}{Colors.OKGREEN}🎉 ALL TESTS PASSED! 🎉{Colors.ENDC}")
    else:
        print(f"{Colors.BOLD}{Colors.FAIL}⚠️  SOME TESTS FAILED ⚠️{Colors.ENDC}")

    print(f"{Colors.BOLD}{Colors.OKBLUE}{'═' * 70}{Colors.ENDC}\n")

    # Show HTML report location
    html_path = backend_dir / "htmlcov" / "index.html"
    print(f"{Colors.OKGREEN}📊 HTML coverage report: {html_path}{Colors.ENDC}\n")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
