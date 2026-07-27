#!/bin/bash

# LABEELE.AI Backend Diagnostics Script
# Run this from your frontend folder

echo "🔍 LABEELE.AI Backend Diagnostics"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Backend URL
BACKEND_URL="https://labeelea1-labeele-duke-prod.hf.space"

echo -e "${BLUE}Testing Backend: ${BACKEND_URL}${NC}"
echo ""

# Test 1: Backend is reachable
echo "📡 Test 1: Checking if backend is online..."
if curl -s --head --max-time 5 "$BACKEND_URL" | head -n 1 | grep "HTTP" > /dev/null; then
    echo -e "${GREEN}✅ Backend is reachable${NC}"
else
    echo -e "${RED}❌ Backend is not reachable${NC}"
    exit 1
fi
echo ""

# Test 2: Check root endpoint
echo "🏠 Test 2: Testing root endpoint (GET /)..."
RESPONSE=$(curl -s "$BACKEND_URL")
if [[ $RESPONSE == *"Duke"* ]] || [[ $RESPONSE == *"API"* ]] || [[ $RESPONSE == *"docs"* ]]; then
    echo -e "${GREEN}✅ Root endpoint responding${NC}"
    echo "Response preview: ${RESPONSE:0:100}..."
else
    echo -e "${YELLOW}⚠️  Root endpoint responding but unexpected content${NC}"
fi
echo ""

# Test 3: Check /docs endpoint
echo "📚 Test 3: Testing /docs endpoint..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/docs")
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ /docs endpoint exists (FastAPI docs available)${NC}"
    echo "   Visit: $BACKEND_URL/docs"
else
    echo -e "${YELLOW}⚠️  /docs returned $HTTP_CODE${NC}"
fi
echo ""

# Test 4: Check /api/auth/register endpoint
echo "🔐 Test 4: Testing /api/auth/register endpoint..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BACKEND_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test123"}')

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    echo -e "${GREEN}✅ /api/auth/register exists and working${NC}"
elif [ "$HTTP_CODE" = "404" ]; then
    echo -e "${RED}❌ /api/auth/register NOT FOUND (404)${NC}"
    echo -e "${RED}   This is the main issue!${NC}"
elif [ "$HTTP_CODE" = "422" ]; then
    echo -e "${YELLOW}⚠️  /api/auth/register exists but validation error (expected)${NC}"
else
    echo -e "${YELLOW}⚠️  /api/auth/register returned $HTTP_CODE${NC}"
fi
echo ""

# Test 5: Check /api/auth/login endpoint
echo "🔓 Test 5: Testing /api/auth/login endpoint..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BACKEND_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test123"}')

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    echo -e "${GREEN}✅ /api/auth/login exists and working${NC}"
elif [ "$HTTP_CODE" = "404" ]; then
    echo -e "${RED}❌ /api/auth/login NOT FOUND (404)${NC}"
elif [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "422" ]; then
    echo -e "${YELLOW}⚠️  /api/auth/login exists but auth failed (expected)${NC}"
else
    echo -e "${YELLOW}⚠️  /api/auth/login returned $HTTP_CODE${NC}"
fi
echo ""

# Test 6: List all available endpoints
echo "📋 Test 6: Attempting to list available endpoints..."
OPENAPI=$(curl -s "$BACKEND_URL/openapi.json")
if [ ! -z "$OPENAPI" ]; then
    echo -e "${GREEN}✅ OpenAPI schema available${NC}"
    echo ""
    echo "Available endpoints:"
    echo "$OPENAPI" | grep -o '"[^"]*":{"' | sed 's/":{"//g' | sed 's/"//g' | sort | uniq | while read endpoint; do
        echo "  - $endpoint"
    done
else
    echo -e "${YELLOW}⚠️  Could not fetch OpenAPI schema${NC}"
fi
echo ""

# Summary
echo "=================================="
echo -e "${BLUE}📊 DIAGNOSIS SUMMARY${NC}"
echo "=================================="
echo ""

# Check if auth endpoints exist
AUTH_REGISTER_EXISTS=false
AUTH_LOGIN_EXISTS=false

if curl -s -X POST "$BACKEND_URL/api/auth/register" -H "Content-Type: application/json" -d '{}' | grep -v "404" > /dev/null 2>&1; then
    AUTH_REGISTER_EXISTS=true
fi

if curl -s -X POST "$BACKEND_URL/api/auth/login" -H "Content-Type: application/json" -d '{}' | grep -v "404" > /dev/null 2>&1; then
    AUTH_LOGIN_EXISTS=true
fi

echo "Backend Status:"
echo "  URL: $BACKEND_URL"
echo "  Reachable: ✅"
echo ""

echo "Required Endpoints:"
if [ "$AUTH_REGISTER_EXISTS" = true ]; then
    echo -e "  ${GREEN}✅ /api/auth/register${NC}"
else
    echo -e "  ${RED}❌ /api/auth/register (MISSING - THIS IS THE PROBLEM!)${NC}"
fi

if [ "$AUTH_LOGIN_EXISTS" = true ]; then
    echo -e "  ${GREEN}✅ /api/auth/login${NC}"
else
    echo -e "  ${RED}❌ /api/auth/login (MISSING)${NC}"
fi
echo ""

# Recommendations
echo "=================================="
echo -e "${BLUE}💡 RECOMMENDATIONS${NC}"
echo "=================================="
echo ""

if [ "$AUTH_REGISTER_EXISTS" = false ] || [ "$AUTH_LOGIN_EXISTS" = false ]; then
    echo -e "${RED}ISSUE FOUND:${NC} Auth endpoints are missing from your backend!"
    echo ""
    echo "You have 3 options:"
    echo ""
    echo "1. ${GREEN}[BEST]${NC} Add auth endpoints to your Hugging Face backend"
    echo "   See: BACKEND_AUTH_FIX.md"
    echo ""
    echo "2. ${YELLOW}[QUICK]${NC} Use mock authentication in frontend"
    echo "   See: MOCK_AUTH_FIX.md"
    echo ""
    echo "3. ${YELLOW}[TEMPORARY]${NC} Disable registration until backend is ready"
    echo "   Comment out registration in login page"
else
    echo -e "${GREEN}All required endpoints are working!${NC}"
    echo "Your issue might be elsewhere. Check browser console for details."
fi
echo ""

echo "=================================="
echo "For detailed fixes, see:"
echo "  - CONSOLE_ERRORS_FIX.md"
echo "  - IMMEDIATE_FIX.md"
echo "=================================="
