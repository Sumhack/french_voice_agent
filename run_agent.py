#!/usr/bin/env python3
"""
French Debt Collection Agent - Entry Point

This script starts an interactive conversation with the debt collection agent.
You can specify which client to use via command-line arguments.

Usage:
    python run_agent.py                    # Use default client
    python run_agent.py --client dell      # Use specific client
    python run_agent.py --client microsoft # Use another client
"""

import sys
import argparse
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Import agent components
from agent import (
    FrenchDebtCollectionAgent,
    GEMINI_API_KEY,
    CLIENTS,
    run_preflight_test,
    DEBUG
)


def main():
    """Main entry point for the agent."""

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Run French Debt Collection Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_agent.py                    # Run with default client
  python run_agent.py --client dell      # Run with Dell client
  python run_agent.py --client microsoft # Run with Microsoft client
  python run_agent.py --list             # List available clients
  python run_agent.py --test             # Run pre-flight test only
        """
    )

    parser.add_argument(
        "--client",
        type=str,
        default=None,
        help="Client to use (see --list for available clients)"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List available clients from config"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run pre-flight test only (don't start agent)"
    )

    parser.add_argument(
        "--skip-test",
        action="store_true",
        help="Skip pre-flight test and start agent directly"
    )

    args = parser.parse_args()

    # List available clients
    if args.list:
        print("\n" + "=" * 70)
        print("AVAILABLE CLIENTS")
        print("=" * 70 + "\n")
        for i, (key, config) in enumerate(CLIENTS.items(), 1):
            print(f"{i}. {key:20} - {config['client_name']}")
            print(f"   Tone: {config.get('tone', 'N/A'):15} | Formality: {config.get('formality_level', 'N/A')}")
        print("\n" + "=" * 70 + "\n")
        return

    # Initialize Gemini API
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY not found in .env file")
        print("Please create .env file from .env.example and add your API key")
        sys.exit(1)

    genai.configure(api_key=GEMINI_API_KEY)

    if DEBUG:
        print("[DEBUG] Gemini API initialized")

    # Run pre-flight test (unless skipped)
    if not args.skip_test:
        print("\nRunning pre-flight test...\n")
        if not run_preflight_test():
            print("❌ Pre-flight test failed. Please fix issues before continuing.")
            print("You can skip this with --skip-test, but it's not recommended.\n")
            sys.exit(1)

    # Run test only mode
    if args.test:
        print("✓ Pre-flight test completed successfully!\n")
        return

    # Validate client selection
    client_key = args.client
    if client_key and client_key not in CLIENTS:
        print(f"❌ Error: Client '{client_key}' not found")
        print(f"\nAvailable clients: {', '.join(CLIENTS.keys())}")
        print("Use --list to see all options\n")
        sys.exit(1)

    # Start the agent
    try:
        print("\n")
        from agent import run_agent
        run_agent(client_key=client_key)
    except KeyboardInterrupt:
        print("\n\n[Session terminée par l'utilisateur]\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")
        if DEBUG:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()