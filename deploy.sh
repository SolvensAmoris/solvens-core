#!/bin/bash
# Solvens Core - Deployment Script
# =====================================

set -e

echo "=========================================="
echo "SOLVENS CORE DEPLOYMENT"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# 1. GitHub Pages
deploy_github_pages() {
    echo -e "${BLUE}[1] GitHub Pages${NC}"
    echo "Go to: https://github.com/SolvensAmoris/solvens-core/settings/pages"
    echo "Select: Source → Deploy from a branch → main"
    echo "Then: Select / (root) folder"
    echo ""
}

# 2. Vercel
deploy_vercel() {
    echo -e "${BLUE}[2] Vercel${NC}"
    echo "Run: vercel --prod"
    echo "Or: npx vercel --prod"
    echo ""
}

# 3. Netlify
deploy_netlify() {
    echo -e "${BLUE}[3] Netlify${NC}"
    echo "Run: netlify deploy --prod --dir=."
    echo "Or drag the project folder to netlify.com/drop"
    echo ""
}

# Show options
echo "Choose deployment method:"
echo ""
deploy_github_pages
deploy_vercel
deploy_netlify

# Auto-detect
if command -v vercel &> /dev/null; then
    echo -e "${GREEN}Vercel detected! Deploying...${NC}"
    vercel --prod
elif command -v netlify &> /dev/null; then
    echo -e "${GREEN}Netlify detected! Deploying...${NC}"
    netlify deploy --prod --dir=.
else
    echo -e "${GREEN}No auto-deploy tool found.${NC}"
    echo "Please use one of the methods above."
fi

echo ""
echo "=========================================="
echo "After deploy, update README with live URL!"
echo "=========================================="
