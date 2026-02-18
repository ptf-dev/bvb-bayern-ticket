#!/bin/bash
# VPS setup for BVB ticket tracker
set -e

echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y xvfb google-chrome-stable python3-pip

echo "Installing Python packages..."
pip3 install requests websocket-client resend

echo "Setup complete!"
echo ""
echo "Usage:"
echo "  export BVB_EMAIL='your-email@example.com'"
echo "  export BVB_RESEND_KEY='re_xxx'"
echo "  export BVB_ACCOUNT_EMAIL='your-bvb-email'"
echo "  export BVB_ACCOUNT_PW='your-bvb-password'"
echo "  xvfb-run python3 check_headless.py"
echo ""
echo "To run in background:"
echo "  nohup xvfb-run python3 check_headless.py > tracker.log 2>&1 &"
