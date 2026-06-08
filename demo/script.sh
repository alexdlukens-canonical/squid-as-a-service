#!/usr/bin/env bash
set -euo pipefail

# --- Defaults (override via env vars) ---
TERRASQUID_ENDPOINT="${TERRASQUID_ENDPOINT:?}"
TERRASQUID_API_KEY="${TERRASQUID_API_KEY:?}"
SQUID_PROXY="${SQUID_PROXY:?}"
TARGET_SITE="${TARGET_SITE:-http://google.com}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

banner() { echo -e "\n${YELLOW}=== $1 ===${NC}"; }

# --- Step 0: verify tools ---
banner "Checking prerequisites"
for cmd in curl terraform; do
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "${RED}ERROR: $cmd is not installed${NC}"
        exit 1
    fi
done
echo "OK: curl, terraform are available"

# --- Step 1: Write terraform.tfvars ---
banner "Writing terraform.tfvars"
cat > "$(dirname "$0")/terraform.tfvars" <<EOF
terrasquid_endpoint = "${TERRASQUID_ENDPOINT}"
terrasquid_api_key  = "${TERRASQUID_API_KEY}"
EOF
echo "Wrote terraform.tfvars"

# --- Step 2: Show the site is NOT accessible ---
banner "BEFORE Terraform: Testing proxy access to ${TARGET_SITE}"
echo "Attempting to reach ${TARGET_SITE} via Squid proxy at ${SQUID_PROXY}..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    --proxy "${SQUID_PROXY}" \
    --max-time 5 \
    "${TARGET_SITE}" 2>&1 || echo "FAILED")
echo "HTTP ${HTTP_CODE}"

if [[ "$HTTP_CODE" =~ ^(200|301|302)$ ]]; then
    echo -e "\n${RED}WARNING: Site is already accessible — nothing to demo.${NC}"
else
    echo -e "\n${GREEN}Site is NOT accessible (as expected before Terraform rules are applied).${NC}"
fi

# --- Step 3: Apply Terraform ---
banner "Applying Terraform"
TF_DIR="$(dirname "$0")"
(
    cd "$TF_DIR"
    terraform init -input=false
    terraform apply -auto-approve -input=false
)
echo -e "${GREEN}Terraform apply completed.${NC}"

# --- Step 4: Show the site IS now accessible ---
banner "AFTER Terraform: Testing proxy access to ${TARGET_SITE}"
echo "Attempting to reach ${TARGET_SITE} via Squid proxy at ${SQUID_PROXY}..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    --proxy "${SQUID_PROXY}" \
    --max-time 10 \
    "${TARGET_SITE}" 2>&1 || echo "FAILED")

if [[ "$HTTP_CODE" =~ ^(200|301|302)$ ]]; then
    echo -e "${GREEN}HTTP ${HTTP_CODE} — Site IS now accessible!${NC}"
else
    echo -e "${RED}HTTP ${HTTP_CODE} — Site is still not accessible.${NC}"
    exit 1
fi

echo -e "\n${GREEN}Demo completed successfully.${NC}"
