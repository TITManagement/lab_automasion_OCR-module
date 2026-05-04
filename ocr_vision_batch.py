#!/usr/bin/env python3
"""
Vision-based batch OCR script for ROI strip images.
Transcribes Japanese text from strip images using Claude's vision capability.
"""

import os
import sys
import base64
import argparse
from pathlib import Path
from anthropic import Anthropic

def encode_image_to_base64(image_path: str) -> str:
    """Encode image file to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.standard_b64encode(image_file.read()).decode("utf-8")

def transcribe_image(client: Anthropic, image_path: str) -> str:
    """
    Transcribe Japanese text from an image using Claude's vision capability.
    
    Args:
        client: Anthropic client instance
        image_path: Path to the image file
        
    Returns:
        Transcribed text
    """
    image_data = encode_image_to_base64(image_path)
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": "このページの日本語テキストをすべて転記してください。改行や段落構造を保持してください。余分なコメントや説明は不要です。テキストのみを出力してください。"
                    }
                ],
            }
        ],
    )
    
    return message.content[0].text

def process_roi_strips(
    source_dir: str,
    start_strip: int = 1,
    end_strip: int = 23,
    dry_run: bool = False
) -> None:
    """
    Process ROI strip images in batch and save transcriptions.
    
    Args:
        source_dir: Directory containing roi_strips
        start_strip: Starting strip number (1-based)
        end_strip: Ending strip number (inclusive)
        dry_run: If True, only shows what would be done without saving
    """
    client = Anthropic()
    source_path = Path(source_dir)
    
    if not source_path.exists():
        print(f"Error: Directory not found: {source_dir}")
        sys.exit(1)
    
    processed = 0
    skipped = 0
    errors = 0
    
    for strip_num in range(start_strip, end_strip + 1):
        jpg_file = source_path / f"strip_{strip_num:04d}.jpg"
        txt_file = source_path / f"strip_{strip_num:04d}.txt"
        
        if not jpg_file.exists():
            print(f"⊘ strip_{strip_num:04d}.jpg not found, skipping...")
            skipped += 1
            continue
        
        print(f"Processing strip_{strip_num:04d}.jpg...", end=" ", flush=True)
        
        try:
            text = transcribe_image(client, str(jpg_file))
            
            if dry_run:
                print(f"[DRY RUN] Would save {len(text)} characters")
                print(f"  Preview: {text[:100]}...")
            else:
                txt_file.write_text(text, encoding="utf-8")
                print(f"✓ Saved to {txt_file.name} ({len(text)} chars)")
                processed += 1
                
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            errors += 1
    
    # Summary
    print("\n" + "="*60)
    print(f"Summary: {processed} processed, {skipped} skipped, {errors} errors")
    if dry_run:
        print("(Dry run mode - no files were modified)")

def main():
    parser = argparse.ArgumentParser(
        description="Vision-based batch OCR for ROI strip images"
    )
    parser.add_argument(
        "source_dir",
        help="Path to roi_strips directory"
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="Starting strip number (default: 1)"
    )
    parser.add_argument(
        "--end",
        type=int,
        default=23,
        help="Ending strip number (default: 23)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without saving"
    )
    
    args = parser.parse_args()
    
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)
    
    process_roi_strips(
        args.source_dir,
        start_strip=args.start,
        end_strip=args.end,
        dry_run=args.dry_run
    )

if __name__ == "__main__":
    main()
