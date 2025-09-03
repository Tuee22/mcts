#!/bin/bash
echo "MINIMAL HOOK EXECUTED" >> /tmp/claude-hook-test.log
echo "$(date): Hook ran successfully" >> /tmp/claude-hook-test.log
exit 0