#!/usr/bin/env python3
"""
Comprehensive test runner for the Loan Extraction System.

Runs all unit and integration tests with beautiful console output.
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
    UNDERLINE = '\033[4m'


def print_ascii_art():
    """Display ASCII art banner."""
    art = f"""
{Colors.OKCYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   ██╗      ██████╗  █████╗ ███╗   ██╗    ████████╗███████╗███████╗████████╗███████╗
║   ██║     ██╔═══██╗██╔══██╗████╗  ██║    ╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝██╔════╝
║   ██║     ██║   ██║███████║██╔██╗ ██║       ██║   █████╗  ███████╗   ██║   ███████╗
║   ██║     ██║   ██║██╔══██║██║╚██╗██║       ██║   ██╔══╝  ╚════██║   ██║   ╚════██║
║   ███████╗╚██████╔╝██║  ██║██║ ╚████║       ██║   ███████╗███████║   ██║   ███████║
║   ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝       ╚═╝   ╚══════╝╚══════╝   ╚═╝   ╚══════╝
║                                                                  ║
║              🚀 Loan Document Extraction Test Suite 🚀          ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
{Colors.ENDC}"""
    print(art)


def print_section(title: str, symbol: str = "═"):
    """Print a section header."""
    width = 70
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}{symbol * width}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}{title.center(width)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}{symbol * width}{Colors.ENDC}\n")


def run_command(cmd: list[str], description: str) -> tuple[bool, float]:
    """
    Run a command and return success status and duration.

    Args:
        cmd: Command to run as list of arguments
        description: Human-readable description of the command

    Returns:
        Tuple of (success: bool, duration: float)
    """
    print(f"{Colors.OKCYAN}▶ {description}...{Colors.ENDC}")
    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
            check=False,
        )
        duration = time.time() - start_time

        if result.returncode == 0:
            print(f"{Colors.OKGREEN}✓ {description} completed successfully ({duration:.2f}s){Colors.ENDC}\n")
            return True, duration
        else:
            print(f"{Colors.FAIL}✗ {description} failed with exit code {result.returncode} ({duration:.2f}s){Colors.ENDC}\n")
            return False, duration

    except Exception as e:
        duration = time.time() - start_time
        print(f"{Colors.FAIL}✗ {description} failed with error: {e} ({duration:.2f}s){Colors.ENDC}\n")
        return False, duration


def print_summary(results: dict):
    """Print test summary."""
    print_section("📊 TEST SUMMARY", "═")

    total_duration = sum(r['duration'] for r in results.values())
    passed = sum(1 for r in results.values() if r['success'])
    failed = len(results) - passed

    print(f"{Colors.BOLD}Total Test Suites: {len(results)}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}✓ Passed: {passed}{Colors.ENDC}")
    print(f"{Colors.FAIL}✗ Failed: {failed}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}⏱  Total Duration: {total_duration:.2f}s{Colors.ENDC}\n")

    print(f"{Colors.BOLD}Detailed Results:{Colors.ENDC}")
    for name, result in results.items():
        status = f"{Colors.OKGREEN}✓ PASS{Colors.ENDC}" if result['success'] else f"{Colors.FAIL}✗ FAIL{Colors.ENDC}"
        print(f"  {status} - {name} ({result['duration']:.2f}s)")

    print()

    if failed == 0:
        print(f"{Colors.BOLD}{Colors.OKGREEN}{'🎉 ALL TESTS PASSED! 🎉'.center(70)}{Colors.ENDC}")
    else:
        print(f"{Colors.BOLD}{Colors.FAIL}{'⚠️  SOME TESTS FAILED ⚠️'.center(70)}{Colors.ENDC}")

    print(f"{Colors.BOLD}{Colors.OKBLUE}{'═' * 70}{Colors.ENDC}\n")


def main():
    """Main test runner."""
    print_ascii_art()

    # Change to backend directory
    backend_dir = Path(__file__).parent
    print(f"{Colors.OKCYAN}Working directory: {backend_dir}{Colors.ENDC}\n")

    results = {}

    # Run unit tests
    print_section("🧪 UNIT TESTS", "═")
    success, duration = run_command(
        ["pytest", "tests/unit", "-v", "--cov=src", "--cov-report=term-missing", "-m", "not integration", "--timeout=30"],
        "Running unit tests"
    )
    results["Unit Tests"] = {"success": success, "duration": duration}

    # Run extraction tests
    print_section("🔬 EXTRACTION TESTS", "═")
    success, duration = run_command(
        ["pytest", "tests/extraction", "-v", "--cov=src", "--cov-append", "--cov-report=term-missing", "--timeout=30"],
        "Running extraction tests"
    )
    results["Extraction Tests"] = {"success": success, "duration": duration}

    # Run integration tests
    print_section("🔗 INTEGRATION TESTS", "═")
    success, duration = run_command(
        ["pytest", "tests/integration", "-v", "--cov=src", "--cov-append", "--cov-report=term-missing", "-m", "integration", "--timeout=60"],
        "Running integration tests"
    )
    results["Integration Tests"] = {"success": success, "duration": duration}

    # Generate coverage report
    print_section("📈 COVERAGE REPORT", "═")
    success, duration = run_command(
        ["coverage", "report"],
        "Generating coverage report"
    )
    results["Coverage Report"] = {"success": success, "duration": duration}

    # Generate HTML coverage report
    print(f"{Colors.OKCYAN}▶ Generating HTML coverage report...{Colors.ENDC}")
    success, duration = run_command(
        ["coverage", "html"],
        "Generating HTML coverage report"
    )
    if success:
        html_path = backend_dir / "htmlcov" / "index.html"
        print(f"{Colors.OKGREEN}📊 HTML coverage report: {html_path}{Colors.ENDC}\n")

    # Print summary
    print_summary(results)

    # Exit with appropriate code
    all_passed = all(r['success'] for r in results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
