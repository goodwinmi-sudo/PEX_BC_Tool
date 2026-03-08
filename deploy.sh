#!/bin/bash
# deal_reviewer deployment script enforcing the UCE Test Harness

echo "=========================================================="
echo " Starting PEX BC Tool Deployment Check"
echo "=========================================================="

export GOOGLE_API_PREVENT_AGENT_TOKEN_SHARING_FOR_GCP_SERVICES=false
python3 test_harness.py
TEST_RESULT=$?

if [ $TEST_RESULT -ne 0 ]; then
    echo "=========================================================="
    echo " [FAILURE] Deployment BLOCKED."
    echo " You must fix the test harness errors before deploying."
    echo " This enforces our UCE (User Centered Excellence) standard."
    echo "=========================================================="
    exit 1
fi

echo "Checking Git Hygiene..."
if [ -n "$(git status --porcelain)" ]; then
    echo "=========================================================="
    echo " [FAILURE] Deployment BLOCKED."
    echo " Your working directory is not clean. Commit all changes first."
    echo "=========================================================="
    exit 1
fi

if [ -n "$(git log origin/main..HEAD 2>/dev/null)" ]; then
    echo "=========================================================="
    echo " [FAILURE] Deployment BLOCKED."
    echo " You have unpushed commits. Please run 'git push' first."
    echo "=========================================================="
    exit 1
fi

echo "=========================================================="
echo " [SUCCESS] All assertions passed. Proceeding with deployment."
echo "=========================================================="

# The actual deployment commands (corprun build and apply OR gcloud)
if command -v corprun &> /dev/null; then
    echo "Running corprun build..."
    corprun build
    echo "Running corprun apply..."
    corprun apply
elif [ -f "/usr/local/google/home/goodwinmi/google-cloud-sdk/bin/gcloud" ]; then
    echo "corprun not found. Using local gcloud SDK for Cloud Run deployment..."
    /usr/local/google/home/goodwinmi/google-cloud-sdk/bin/gcloud run deploy deal-reviewer \
      --source . \
      --project internal-xr-ai-tools-977945 \
      --region us-central1 \
      --allow-unauthenticated \
      --no-cpu-throttling
else
    echo "Note: 'corprun' or 'gcloud' commands not found in your environment."
    echo "Please run your deployment commands manually now that tests have passed."
fi

echo "Deployment sequence completed."
