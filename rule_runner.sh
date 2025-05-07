#!/bin/bash
cd /opt/nelson/src/investing/ticker_screener
uv run rules.py rule-runner --json output.json > /dev/null 2>&1
