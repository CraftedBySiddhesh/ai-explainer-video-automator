#!/usr/bin/env python3
"""
AI Explainer Video Prompt Generator
Processes script sections and generates complete CSV with image/animation prompts
"""

import sys
import csv
import re
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API call function
def call_claude_api(prompt, system_prompt=""):
    """Make API call to Claude"""
    try:
        import requests
        
        # Get API key from environment
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            print("❌ Error: ANTHROPIC_API_KEY not found in .env file")
            print("Create a .env file with: ANTHROPIC_API_KEY=your_key_here")
            return None
        
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        messages = [{"role": "user", "content": prompt}]
        
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 8000,
            "messages": messages
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data["content"][0]["text"]
    
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None


def parse_script_sections(script_text):
    """Parse script into sections"""
    lines = script_text.strip().split('\n')
    sections = []
    current_section = None
    current_content = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines between sections
        if not line:
            if current_content:
                continue
            else:
                # End of section
                if current_section and current_content:
                    sections.append({
                        'title': current_section,
                        'content': '\n'.join(current_content)
                    })
                    current_section = None
                    current_content = []
                continue
        
        # Detect section title (standalone line before paragraphs)
        # Title detection: short line (< 150 chars) that looks like a heading
        if len(line) < 150 and ':' in line and not current_content:
            if current_section and current_content:
                sections.append({
                    'title': current_section,
                    'content': '\n'.join(current_content)
                })
                current_content = []
            current_section = line
        else:
            current_content.append(line)
    
    # Add last section
    if current_section and current_content:
        sections.append({
            'title': current_section,
            'content': '\n'.join(current_content)
        })
    
    return sections


def generate_section_prompts(section_num, section_title, section_content):
    """Generate all prompts for a single section"""
    
    system_prompt = """You are an expert AI explainer video prompt generator. 
You create minimalistic flat 2-color stick figure style educational videos.
You MUST respond ONLY with valid JSON - no preamble, no explanation, no markdown.
"""
    
    prompt = f"""Generate complete explainer video prompts for this section.

SECTION {section_num}: {section_title}

CONTENT:
{section_content}

RULES:
- Analyze the content depth and story complexity
- Determine optimal scene count between 14-25 scenes for THIS section
- Identify all unique character types needed (can be 1-2 or 10-15 depending on content)
- Create character sheets with: simple black stick figures, only clothing/accessories colored
- Generate image prompts: minimalistic flat 2-color design
- Generate animation prompts: detailed camera movements and character animations

OUTPUT FORMAT (JSON ONLY - NO OTHER TEXT):
{{
  "section_number": {section_num},
  "section_title": "{section_title}",
  "total_scenes": <number between 14-25>,
  "character_sheets": [
    {{
      "name": "Character Name",
      "description": "Simple black stick figure, [clothing color and style], [accessories]. White background. Show in 3-4 directions."
    }}
  ],
  "scenes": [
    {{
      "scene_number": 1,
      "description": "Brief scene description",
      "characters": ["Character Name"],
      "image_prompt": "Scene 1: Minimalistic flat design, 2-color palette ([color1], [color2]). Simple black stick figure [character] with [colored clothing]. [Visual description].",
      "animation_prompt": "Scene 1: Camera [movement]. [Character] [animation]. Pacing is [pacing]. [Additional motion details]."
    }}
  ]
}}

RESPOND WITH JSON ONLY."""

    print(f"  → Calling Claude API for Section {section_num}...")
    response = call_claude_api(prompt, system_prompt)
    
    if not response:
        return None
    
    # Clean response - remove markdown fences if present
    response = response.strip()
    if response.startswith('```json'):
        response = response[7:]
    if response.startswith('```'):
        response = response[3:]
    if response.endswith('```'):
        response = response[:-3]
    response = response.strip()
    
    try:
        data = json.loads(response)
        return data
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON Parse Error: {e}")
        print(f"  Response preview: {response[:200]}")
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_video_prompts.py <script.txt>")
        sys.exit(1)
    
    script_file = Path(sys.argv[1])
    
    if not script_file.exists():
        print(f"❌ File not found: {script_file}")
        sys.exit(1)
    
    print(f"📖 Reading script: {script_file}")
    script_text = script_file.read_text(encoding='utf-8')
    
    print("🔍 Parsing sections...")
    sections = parse_script_sections(script_text)
    print(f"✓ Found {len(sections)} sections\n")
    
    if not sections:
        print("❌ No sections detected. Check your script format.")
        sys.exit(1)
    
    # Generate prompts for each section
    all_data = []
    global_scene_counter = 1
    
    for idx, section in enumerate(sections, 1):
        print(f"🎬 Processing Section {idx}: {section['title'][:50]}...")
        
        section_data = generate_section_prompts(idx, section['title'], section['content'])
        
        if not section_data:
            print(f"  ⚠️  Skipping section {idx} due to errors")
            continue
        
        total_scenes = section_data.get('total_scenes', 0)
        print(f"  ✓ Generated {total_scenes} scenes")
        
        # Prepare character sheets reference
        char_sheets = section_data.get('character_sheets', [])
        char_sheet_text = "; ".join([f"{c['name']}: {c['description']}" for c in char_sheets])
        
        # Add scenes to CSV data
        for scene in section_data.get('scenes', []):
            all_data.append({
                'Section_Number': idx,
                'Section_Title': section['title'],
                'Total_Scenes_In_Section': total_scenes,
                'Scene_Number_Global': global_scene_counter,
                'Scene_Number_In_Section': scene['scene_number'],
                'Scene_Description': scene['description'],
                'Character_Sheets': char_sheet_text if scene['scene_number'] == 1 else '',
                'Characters_In_Scene': ', '.join(scene.get('characters', [])),
                'Image_Prompt': scene['image_prompt'],
                'Animation_Prompt': scene['animation_prompt']
            })
            global_scene_counter += 1
        
        print()
    
    # Write CSV
    output_file = script_file.stem + '_prompts.csv'
    output_path = Path(output_file)
    
    print(f"💾 Writing CSV: {output_path}")
    
    with output_path.open('w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'Section_Number',
            'Section_Title',
            'Total_Scenes_In_Section',
            'Scene_Number_Global',
            'Scene_Number_In_Section',
            'Scene_Description',
            'Character_Sheets',
            'Characters_In_Scene',
            'Image_Prompt',
            'Animation_Prompt'
        ]
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)
    
    print(f"\n✅ SUCCESS!")
    print(f"✓ Total sections processed: {len(sections)}")
    print(f"✓ Total scenes generated: {global_scene_counter - 1}")
    print(f"✓ Output file: {output_path}")


if __name__ == '__main__':
    main()
