#!/bin/bash
#
# Vision-based batch OCR script for ROI strip images
# Transcribes Japanese text from strip images using Claude's vision API
#
# Usage: ./ocr_vision_batch.sh /path/to/roi_strips [start_strip] [end_strip]
# Example: ./ocr_vision_batch.sh ./roi_strips 10 23
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="${1:-.}"
START_STRIP="${2:-1}"
END_STRIP="${3:-23}"
DRY_RUN="${DRY_RUN:-false}"

# API Configuration
API_KEY="${ANTHROPIC_API_KEY}"
API_ENDPOINT="https://api.anthropic.com/v1/messages"
MODEL="claude-3-5-sonnet-20241022"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
check_prerequisites() {
    if [ -z "$API_KEY" ]; then
        echo -e "${RED}Error: ANTHROPIC_API_KEY environment variable not set${NC}"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}Error: curl is not installed${NC}"
        exit 1
    fi
    
    if ! command -v base64 &> /dev/null; then
        echo -e "${RED}Error: base64 is not installed${NC}"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        echo -e "${YELLOW}Warning: jq not found (optional, for better output parsing)${NC}"
    fi
    
    if [ ! -d "$SOURCE_DIR" ]; then
        echo -e "${RED}Error: Directory not found: $SOURCE_DIR${NC}"
        exit 1
    fi
}

# Encode image to base64
encode_image() {
    local image_file="$1"
    base64 < "$image_file"
}

# Call Vision API
transcribe_image() {
    local image_path="$1"
    local base64_image=$(encode_image "$image_path")
    
    local payload=$(cat <<EOF
{
    "model": "$MODEL",
    "max_tokens": 1024,
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": "$base64_image"
                    }
                },
                {
                    "type": "text",
                    "text": "このページの日本語テキストをすべて転記してください。改行や段落構造を保持してください。余分なコメントや説明は不要です。テキストのみを出力してください。"
                }
            ]
        }
    ]
}
EOF
)
    
    local response=$(curl -s -X POST "$API_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        -H "anthropic-version: 2023-06-01" \
        -d "$payload")
    
    # Extract text from response
    if command -v jq &> /dev/null; then
        echo "$response" | jq -r '.content[0].text'
    else
        # Fallback: basic grep parsing
        echo "$response" | grep -o '"text":"[^"]*' | head -1 | cut -d'"' -f4
    fi
}

# Main processing loop
process_roi_strips() {
    local processed=0
    local skipped=0
    local errors=0
    
    echo "OCR Vision Batch Processing"
    echo "============================"
    echo "Source: $SOURCE_DIR"
    echo "Range: strip_$(printf "%04d" $START_STRIP) to strip_$(printf "%04d" $END_STRIP)"
    echo ""
    
    for ((strip_num=$START_STRIP; strip_num<=$END_STRIP; strip_num++)); do
        local strip_name=$(printf "strip_%04d" $strip_num)
        local jpg_file="$SOURCE_DIR/${strip_name}.jpg"
        local txt_file="$SOURCE_DIR/${strip_name}.txt"
        
        if [ ! -f "$jpg_file" ]; then
            echo -e "${YELLOW}⊘${NC} ${strip_name}.jpg not found, skipping..."
            ((skipped++))
            continue
        fi
        
        echo -n "Processing ${strip_name}.jpg... "
        
        if [ "$DRY_RUN" = "true" ]; then
            echo -e "${GREEN}[DRY RUN]${NC}"
            continue
        fi
        
        # Transcribe image
        local text=$(transcribe_image "$jpg_file")
        
        if [ -z "$text" ]; then
            echo -e "${RED}✗ Error: No text returned from API${NC}"
            ((errors++))
            continue
        fi
        
        # Save to file
        if echo -n "$text" > "$txt_file"; then
            local char_count=${#text}
            echo -e "${GREEN}✓${NC} Saved (${char_count} chars)"
            ((processed++))
        else
            echo -e "${RED}✗ Error: Failed to write file${NC}"
            ((errors++))
        fi
    done
    
    # Summary
    echo ""
    echo "============================"
    echo -e "Summary: ${GREEN}$processed processed${NC}, ${YELLOW}$skipped skipped${NC}, ${RED}$errors errors${NC}"
    if [ "$DRY_RUN" = "true" ]; then
        echo "(Dry run mode - no files were modified)"
    fi
}

# Show usage
show_usage() {
    cat <<EOF
Vision-based batch OCR for ROI strip images

Usage: $0 <source_dir> [start_strip] [end_strip]

Arguments:
  source_dir      Path to roi_strips directory
  start_strip     Starting strip number (default: 1)
  end_strip       Ending strip number (default: 23)

Environment Variables:
  ANTHROPIC_API_KEY  Your Anthropic API key (required)
  DRY_RUN            Set to 'true' for dry run mode

Examples:
  # Process all strips (1-23)
  $0 ./roi_strips

  # Process strips 10-23
  $0 ./roi_strips 10 23

  # Dry run
  DRY_RUN=true $0 ./roi_strips

EOF
}

# Main
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_usage
    exit 0
fi

check_prerequisites
process_roi_strips
