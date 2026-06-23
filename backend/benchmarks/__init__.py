"""Benchmark and replay suite for Panacea autonomous workflows.

Usage (offline, no API keys required):
    pytest backend/tests/test_benchmarks.py -v

Usage (against real models, e.g. in staging):
    python -m benchmarks.runner --workflow coding --model claude-sonnet-4-6

Compare two runs:
    python -m benchmarks.compare baseline.json candidate.json
"""
