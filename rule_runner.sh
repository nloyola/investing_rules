#!/bin/bash
cd /opt/nelson/src/investing/investing_rules
uv run rules.py rule-runner --json output.json > /dev/null 2>&1
