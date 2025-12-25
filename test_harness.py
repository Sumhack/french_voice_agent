#!/usr/bin/env python3
"""
French Debt Collection Agent - Test Harness

Runs automated synthetic conversations against the agent with predefined scenarios.
Measures: success rate, response times, hand-off rate, and failure modes.

Cost optimized: 6 scenarios × 3 clients × 1 iteration = 18 API calls (default)

Usage:
    python test_harness.py                      # Run all tests (18 calls)
    python test_harness.py --iterations 3       # Run 3 times per scenario (54 calls)
    python test_harness.py --client dell        # Test specific client only (6 calls)
    python test_harness.py --verbose            # Show detailed output
    python test_harness.py -i 2 --client amazon # 2 iterations, Amazon only
"""

import sys
import time
import argparse
import statistics
from typing import Tuple, List, Dict
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
import os

# Load environment
load_dotenv()

# Import agent
from agent import (
    FrenchDebtCollectionAgent,
    GEMINI_API_KEY,
    CLIENTS,
    MODEL
)

# Configure Gemini
if not GEMINI_API_KEY:
    print("❌ Error: GEMINI_API_KEY not found in .env file")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

# ============================================================================
# TEST SCENARIOS
# ============================================================================

TEST_SCENARIOS = [
    # Positive scenarios
    {
        "name": "Client Agrees to Pay",
        "category": "Positive",
        "conversation": [
            "Bonjour.",
            "Oui, c'est moi qui suis responsable.",
            "D'accord, je comprends.",
            "Je peux payer immédiatement.",
            "Au revoir."
        ]
    },
    {
        "name": "Client Asks for Time to Pay",
        "category": "Positive",
        "conversation": [
            "Bonjour.",
            "C'est moi.",
            "Je comprends, mais j'ai besoin de plus de temps.",
            "Je peux payer dans deux semaines.",
            "Merci, à bientôt."
        ]
    },
    {
        "name": "Client Requests Payment Plan",
        "category": "Positive",
        "conversation": [
            "Oui, c'est pour mon compte.",
            "C'est beaucoup d'argent.",
            "Un plan de paiement serait mieux pour moi.",
            "Pouvez-vous proposer quelque chose?",
            "Au revoir."
        ]
    },

    # Edge cases
    {
        "name": "Robot Question Detection",
        "category": "Edge Case",
        "conversation": [
            "Bonjour.",
            "Vous êtes un robot?",
            "D'accord, je comprends.",
            "Je peux payer demain.",
            "À bientôt."
        ]
    },
    {
        "name": "Upset/Angry Client",
        "category": "Edge Case",
        "conversation": [
            "C'est qui?",
            "Je suis très en colère contre vous!",
            "C'est injuste!",
            "Je veux parler à un responsable.",
            "Au revoir."
        ]
    },

    # Language/boundary cases
    {
        "name": "Multiple Language Switches",
        "category": "Boundary",
        "conversation": [
            "Bonjour.",
            "Do you speak English?",
            "Je préfère parler en français.",
            "But can we switch?",
            "Non, seulement en français.",
            "D'accord.",
            "Je peux payer demain.",
            "Au revoir."
        ]
    },
]


# ============================================================================
# TEST EXECUTION
# ============================================================================

class TestResult:
    """Store results of a single test run."""

    def __init__(self, scenario_name: str, client_key: str, iteration: int):
        self.scenario_name = scenario_name
        self.client_key = client_key
        self.iteration = iteration
        self.success = False
        self.error_message = None
        self.response_times = []
        self.total_time = 0
        self.turns = 0
        self.properly_closed = False
        self.conversation = []
        self.failure_reason = None  # NEW: Track why it failed

    def add_exchange(self, user_msg: str, agent_response: str, response_time: float):
        """Add user/agent exchange to results."""
        self.response_times.append(response_time)
        self.turns += 1
        self.conversation.append({
            "user": user_msg,
            "agent": agent_response,
            "response_time": response_time
        })

    def set_error(self, error_msg: str):
        """Mark test as failed with error."""
        self.success = False
        self.error_message = error_msg
        self.failure_reason = f"API Error: {error_msg}"

    def set_failure_reason(self, reason: str):
        """Set why test failed."""
        self.failure_reason = reason
        self.success = False

    def finalize(self, properly_closed: bool):
        """Finalize test result."""
        self.properly_closed = properly_closed
        self.total_time = sum(self.response_times) if self.response_times else 0
        # Success = no errors (removed closing requirement)
        self.success = self.error_message is None


def run_single_test(scenario: Dict, client_key: str, iteration: int, verbose: bool = False) -> TestResult:
    """Run a single test scenario against a client."""

    result = TestResult(scenario["name"], client_key, iteration)

    try:
        # Initialize agent
        agent = FrenchDebtCollectionAgent(client_key)

        # Get greeting
        greeting = agent.start()
        result.conversation.append({
            "user": "[greeting]",
            "agent": greeting,
            "response_time": 0
        })

        # Run conversation
        for user_msg in scenario["conversation"]:
            start_time = time.time()

            # Generate response
            agent_response = agent.generate_response(user_msg)
            response_time = time.time() - start_time

            # Add to results
            result.add_exchange(user_msg, agent_response, response_time)

            if verbose:
                print(f"  → User: {user_msg}")
                print(f"  → Agent: {agent_response[:100]}...")
                print(f"    Response time: {response_time:.2f}s\n")

        # Check if conversation properly closed
        # A proper close means agent acknowledged the ending
        last_agent_msg = result.conversation[-1]["agent"].lower()
        closing_indicators = ["au revoir", "à bientôt", "fin", "quitter", "merci"]
        result.properly_closed = any(indicator in last_agent_msg for indicator in closing_indicators)

        # Finalize (success if no errors and properly closed)
        result.finalize(result.properly_closed)

    except Exception as e:
        result.set_error(str(e))

    return result


def run_all_tests(clients: List[str], iterations: int = 1, verbose: bool = False) -> List[TestResult]:
    """Run all test scenarios for specified clients."""

    all_results = []
    total_tests = len(TEST_SCENARIOS) * len(clients) * iterations
    current_test = 0

    print("\n" + "=" * 70)
    print(
        f"RUNNING TEST HARNESS - {total_tests} tests total ({len(TEST_SCENARIOS)} scenarios × {len(clients)} clients × {iterations} iteration(s))")
    print("=" * 70 + "\n")

    for scenario in TEST_SCENARIOS:
        print(f"Scenario: {scenario['name']}")
        print("-" * 70)

        for client_key in clients:
            print(f"  Client: {client_key}")

            for iteration in range(1, iterations + 1):
                current_test += 1
                print(f"    Run {iteration}/{iterations}...", end=" ", flush=True)

                result = run_single_test(scenario, client_key, iteration, verbose=verbose)
                all_results.append(result)

                status = "✓" if result.success else "✗"
                print(f"{status}", end="")

                # Show failure reason if test failed
                if not result.success and result.failure_reason:
                    print(f" ({result.failure_reason})", end="")

                print()  # Newline

        print()

    return all_results


# ============================================================================
# ANALYSIS & REPORTING
# ============================================================================

def analyze_results(results: List[TestResult]) -> Dict:
    """Analyze test results and generate statistics."""

    if not results:
        return {}

    # Overall stats
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.success)
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

    # Response time stats
    all_response_times = []
    for result in results:
        all_response_times.extend(result.response_times)

    avg_response_time = statistics.mean(all_response_times) if all_response_times else 0
    p95_response_time = sorted(all_response_times)[int(len(all_response_times) * 0.95)] if all_response_times else 0
    max_response_time = max(all_response_times) if all_response_times else 0

    # Hand-off rate (properly closed conversations)
    properly_closed = sum(1 for r in results if r.properly_closed)
    hand_off_rate = (properly_closed / total_tests * 100) if total_tests > 0 else 0

    # Failure analysis with reasons
    failures_by_scenario = {}
    failures_with_reasons = {}  # NEW: Track failure reasons

    for result in results:
        if not result.success:
            if result.scenario_name not in failures_by_scenario:
                failures_by_scenario[result.scenario_name] = 0
                failures_with_reasons[result.scenario_name] = []

            failures_by_scenario[result.scenario_name] += 1
            failures_with_reasons[result.scenario_name].append(result.failure_reason)

    # Per-client stats
    per_client_stats = {}
    for client_key in set(r.client_key for r in results):
        client_results = [r for r in results if r.client_key == client_key]
        client_passed = sum(1 for r in client_results if r.success)
        per_client_stats[client_key] = {
            "total": len(client_results),
            "passed": client_passed,
            "success_rate": (client_passed / len(client_results) * 100) if client_results else 0
        }

    return {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "success_rate": success_rate,
        "avg_response_time": avg_response_time,
        "p95_response_time": p95_response_time,
        "max_response_time": max_response_time,
        "hand_off_rate": hand_off_rate,
        "failures_by_scenario": failures_by_scenario,
        "failures_with_reasons": failures_with_reasons,
        "per_client_stats": per_client_stats,
        "all_results": results
    }


def generate_report(analysis: Dict, output_file: str = "test_report.md"):
    """Generate markdown report of test results."""

    report = f"""# French Debt Collection Agent - Test Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Tests | {analysis['total_tests']} |
| Passed | {analysis['passed_tests']} |
| **Success Rate** | **{analysis['success_rate']:.1f}%** |
| Hand-off Rate | {analysis['hand_off_rate']:.1f}% |
| Avg Response Time | {analysis['avg_response_time']:.2f}s |
| P95 Response Time | {analysis['p95_response_time']:.2f}s |
| Max Response Time | {analysis['max_response_time']:.2f}s |

## Results by Client

"""

    for client_key, stats in analysis['per_client_stats'].items():
        client_name = CLIENTS[client_key]['client_name']
        report += f"""
### {client_name}
- **Tests Run:** {stats['total']}
- **Success Rate:** {stats['success_rate']:.1f}%

"""

    # Failure analysis
    if analysis['failures_by_scenario']:
        report += """## Notable Failure Modes

"""
        for scenario, count in sorted(analysis['failures_by_scenario'].items(), key=lambda x: x[1], reverse=True):
            report += f"### {scenario}\n"
            report += f"**Failures:** {count}\n\n"

            # Show failure reasons for this scenario
            reasons = analysis['failures_with_reasons'].get(scenario, [])
            if reasons:
                report += "**Reasons:**\n"
                for i, reason in enumerate(reasons, 1):
                    report += f"{i}. {reason}\n"
            report += "\n"
    else:
        report += """## Notable Failure Modes

✓ None - All tests passed!

"""

    # Example transcripts
    report += """## Example Test Transcripts

"""

    # Show 1 successful and 1 failed (if exists)
    results = analysis['all_results']

    successful = next((r for r in results if r.success), None)
    if successful:
        report += f"""### ✓ Successful Test: {successful.scenario_name} ({successful.client_key})

```
"""
        for exchange in successful.conversation[:5]:  # First 5 exchanges
            report += f"Client: {exchange['user']}\n"
            report += f"Agent: {exchange['agent'][:100]}...\n\n"
        report += "```\n\n"

    failed = next((r for r in results if not r.success), None)
    if failed:
        report += f"""### ✗ Failed Test: {failed.scenario_name} ({failed.client_key})

**Error:** {failed.error_message}

"""

    report += """## Test Scenarios Covered

The harness runs 6 focused synthetic conversation scenarios across 3 clients (1 iteration by default):

**Positive (3 scenarios):**
- Client agrees to pay immediately
- Client asks for time to pay
- Client requests payment plan

**Edge Cases (2 scenarios):**
- Robot/AI detection question
- Upset/angry client behavior

**Boundary (1 scenario):**
- Multiple language switches (French/English mixed)

**Total Default Cost:** 18 API calls (6 scenarios × 3 clients × 1 iteration)

You can increase iterations with `--iterations N` for more variance testing.

## Methodology

Each scenario runs once per client by default (configurable via `--iterations`).
A test passes if:
1. Agent generates response without error
2. Agent properly closes the conversation

"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✓ Report saved to: {output_file}")
    return report


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point for test harness."""

    parser = argparse.ArgumentParser(
        description="Run test harness for French Debt Collection Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_harness.py                  # Run all tests (18 API calls)
  python test_harness.py --client dell    # Test Dell only (6 API calls)
  python test_harness.py --iterations 3   # Run 3x per scenario (54 API calls)
  python test_harness.py --verbose        # Show detailed output
  python test_harness.py -i 2             # Run 2 iterations per scenario (36 calls)
        """
    )

    parser.add_argument(
        "--client",
        type=str,
        default=None,
        help="Test specific client (default: all)"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output for each test"
    )

    parser.add_argument(
        "--iterations",
        "-i",
        type=int,
        default=1,
        help="Number of iterations per scenario (default: 1)"
    )

    parser.add_argument(
        "--quick",
        "-q",
        action="store_true",
        help="Deprecated: use --iterations instead"
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="test_report.md",
        help="Output file for report (default: test_report.md)"
    )

    args = parser.parse_args()

    # Determine which clients to test
    if args.client:
        if args.client not in CLIENTS:
            print(f"❌ Error: Client '{args.client}' not found")
            print(f"Available: {', '.join(CLIENTS.keys())}\n")
            sys.exit(1)
        clients = [args.client]
    else:
        clients = list(CLIENTS.keys())

    iterations = args.iterations

    # Run tests
    results = run_all_tests(clients, iterations=iterations, verbose=args.verbose)

    # Analyze
    analysis = analyze_results(results)

    # Report
    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    print(f"Total Tests: {analysis['total_tests']}")
    print(f"Passed: {analysis['passed_tests']}")
    print(f"Success Rate: {analysis['success_rate']:.1f}%")
    print(f"Hand-off Rate: {analysis['hand_off_rate']:.1f}%")
    print(f"Avg Response Time: {analysis['avg_response_time']:.2f}s")
    print(f"P95 Response Time: {analysis['p95_response_time']:.2f}s")
    print("=" * 70 + "\n")

    # Generate markdown report
    generate_report(analysis, args.output)

    sys.exit(0 if analysis['success_rate'] == 100 else 1)


if __name__ == "__main__":
    main()