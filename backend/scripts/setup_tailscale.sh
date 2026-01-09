#!/bin/bash
#
# Tailscale setup script for Paraclete VMs
#
# This script is executed when a new VM is provisioned to:
# - Install Tailscale
# - Configure authentication
# - Set up secure networking
#

set -e

echo "=== Paraclete VM Tailscale Setup ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root"
  exit 1
fi

# Check for required environment variables
if [ -z "$TAILSCALE_AUTHKEY" ]; then
  echo "Error: TAILSCALE_AUTHKEY environment variable not set"
  exit 1
fi

if [ -z "$USER_ID" ]; then
  echo "Warning: USER_ID not set, using default"
  USER_ID="unknown"
fi

echo "Installing Tailscale..."

# Install Tailscale (Ubuntu/Debian)
curl -fsSL https://tailscale.com/install.sh | sh

echo "Configuring Tailscale..."

# Start Tailscale with auth key
tailscale up \
  --authkey="$TAILSCALE_AUTHKEY" \
  --hostname="paraclete-${USER_ID:0:8}" \
  --accept-routes \
  --ssh

echo "Tailscale setup complete!"
echo "Tailscale IP: $(tailscale ip -4)"
echo "SSH enabled via Tailscale"

# Store Tailscale IP for later retrieval
TAILSCALE_IP=$(tailscale ip -4)
echo "$TAILSCALE_IP" > /var/lib/paraclete/tailscale_ip.txt

exit 0
