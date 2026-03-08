#!/bin/bash
source gbash.sh || exit 1
# Try using corp curl or similar to get the page.
curl -s --negotiate -u : "https://docs.google.com/spreadsheets/d/1GCPSG6TLLlVQeWIFqS9pPpD3XtHhc6EcVJeOKi-7F_U/export?format=csv&gid=0" | head -n 10
