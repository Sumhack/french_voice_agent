# French Debt Collection Agent - Test Report

**Generated:** 2025-12-25 12:29:55

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Tests | 6 |
| Passed | 6 |
| **Success Rate** | **100.0%** |
| Hand-off Rate | 0.0% |
| Avg Response Time | 4.57s |
| P95 Response Time | 9.19s |
| Max Response Time | 17.49s |

## Results by Client


### Dell
- **Tests Run:** 6
- **Success Rate:** 100.0%

## Notable Failure Modes

✓ None - All tests passed!

## Example Test Transcripts

### ✓ Successful Test: Client Agrees to Pay (dell)

```
Client: [greeting]
Agent: Bonjour, c'est Dell. Comment puis-je vous aider?...

Client: Bonjour.
Agent: Bonjour. Je suis là pour vous aider. Pourriez-vous me faire part de la raison de votre appel aujourd...

Client: Oui, c'est moi qui suis responsable.
Agent: Merci. Pourriez-vous m'expliquer la raison de votre appel ou la situation que vous souhaitez aborder...

Client: D'accord, je comprends.
Agent: Merci. Je vous invite à me faire part de la situation ou de la question qui vous amène à nous contac...

Client: Je peux payer immédiatement.
Agent: C'est une excellente nouvelle. Nous apprécions votre attention à cette affaire....

```

## Test Scenarios Covered

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

