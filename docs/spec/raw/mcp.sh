#!/bin/bash
# usage: mcp.sh method 'params-json'
curl -s -m 60 -X POST https://mcp.sandbox.airwallex.com/docs -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"$1\",\"params\":$2}" | sed -n 's/^data: //p'
