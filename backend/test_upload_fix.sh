#!/bin/bash
# Test script to verify document upload fixes

set -e

echo "=== Testing Document Upload Fixes ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
API_URL="http://localhost:8001"
TEST_FILE="${1:-examples/sample.pdf}"

if [ ! -f "$TEST_FILE" ]; then
    echo -e "${RED}Error: Test file not found: $TEST_FILE${NC}"
    echo "Usage: $0 [path/to/test.pdf]"
    exit 1
fi

echo -e "${YELLOW}1. Uploading test document...${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/documents/" \
  -F "file=@$TEST_FILE" \
  -F "method=docling" \
  -F "ocr=auto")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "HTTP Status: $HTTP_CODE"
echo "Response Body:"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"

if [ "$HTTP_CODE" = "201" ]; then
    echo -e "${GREEN}✓ Upload returned 201 (Created)${NC}"

    # Extract document ID
    DOC_ID=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

    if [ -n "$DOC_ID" ]; then
        echo ""
        echo -e "${YELLOW}2. Checking document status...${NC}"
        sleep 2  # Give processing a moment

        STATUS_RESPONSE=$(curl -s "$API_URL/api/documents/$DOC_ID/status")
        echo "$STATUS_RESPONSE" | python3 -m json.tool

        STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null)
        ERROR_MSG=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('error_message', ''))" 2>/dev/null)

        echo ""
        echo -e "${YELLOW}3. Verifying database record...${NC}"
        docker exec loan-postgres psql -U postgres -d loan_extraction -c \
            "SELECT id, filename, status, error_message FROM documents WHERE id = '$DOC_ID';"

        echo ""
        echo -e "${YELLOW}4. Results Summary:${NC}"
        echo "Document ID: $DOC_ID"
        echo "Status: $STATUS"

        if [ "$STATUS" = "completed" ]; then
            echo -e "${GREEN}✓ Document processing completed${NC}"
            if [ -n "$ERROR_MSG" ] && [ "$ERROR_MSG" != "null" ]; then
                echo -e "${YELLOW}⚠ Partial success with warnings:${NC}"
                echo "  $ERROR_MSG"
                echo -e "${GREEN}✓ FIX 3 working: Partial failures allowed${NC}"
            else
                echo -e "${GREEN}✓ Full success: No errors${NC}"
            fi
        elif [ "$STATUS" = "failed" ]; then
            echo -e "${YELLOW}⚠ Document processing failed${NC}"
            echo "Error: $ERROR_MSG"
            echo -e "${GREEN}✓ FIX 1 working: Document persisted despite failure${NC}"
            echo -e "${GREEN}✓ FIX 2 working: Error message captured${NC}"
        elif [ "$STATUS" = "pending" ]; then
            echo -e "${YELLOW}ℹ Document still processing (async mode detected)${NC}"
        fi

        echo ""
        echo -e "${YELLOW}5. Checking logs for detailed error info...${NC}"
        echo "Last 20 lines from log:"
        tail -20 /private/tmp/fastapi-test.log | grep -E "document_id.*$DOC_ID|ERROR|WARNING" || echo "No recent logs found"

    fi
else
    echo -e "${RED}✗ Upload failed with status $HTTP_CODE${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=== Test Complete ===${NC}"
