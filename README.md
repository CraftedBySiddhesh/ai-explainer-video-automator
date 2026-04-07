# AI Explainer Video Prompt Generator

Automated script that converts your educational script into complete CSV with image and animation prompts.

## Installation

1. Install Python 3.8+ (if not already installed)

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. **Setup API Key:**

Create a `.env` file in the project folder:
```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-api03-your_actual_key_here
```

Get your API key from: https://console.anthropic.com/settings/keys

## Usage

### Basic Command
```bash
python generate_video_prompts.py your_script.txt
```

### Example
```bash
python generate_video_prompts.py test_script.txt
```

## Input Format

Your script file should have sections separated by blank lines:

```
Section Title: Subtitle Here
First paragraph of narration explaining the concept...

Second paragraph continuing the story...

Third paragraph with the conclusion...

Next Section Title: Another Subtitle
First paragraph of the next section...
```

**Important:**
- Section titles should be standalone lines (with a colon `:`)
- Each section should have 2-4 paragraphs
- Separate sections with blank lines

## Output

The script generates a single CSV file: `your_script_prompts.csv`

### CSV Columns:
- `Section_Number` - Section index (1, 2, 3...)
- `Section_Title` - Full section title
- `Total_Scenes_In_Section` - Scene count for this section (14-25)
- `Scene_Number_Global` - Global scene counter (1→250+)
- `Scene_Number_In_Section` - Scene number within section
- `Scene_Description` - What happens in this scene
- `Character_Sheets` - Character descriptions (only in first scene of section)
- `Characters_In_Scene` - Which characters appear in this scene
- `Image_Prompt` - Minimalistic flat 2-color image prompt
- `Animation_Prompt` - Camera and motion animation prompt

## How It Works

For each section:
1. **Analyzes content** to determine complexity
2. **Decides scene count** (14-25 based on story depth)
3. **Identifies characters** (1-15 depending on content)
4. **Generates character sheets** (stick figures with colored clothing)
5. **Creates image prompts** (minimalistic 2-color flat design)
6. **Creates animation prompts** (camera movements + character animations)

## Example Output

```csv
Section_Number,Section_Title,Total_Scenes_In_Section,Scene_Number_Global,Scene_Number_In_Section,Scene_Description,Character_Sheets,Characters_In_Scene,Image_Prompt,Animation_Prompt
1,Mississippian Depopulation: Cahokia's Diluvian Demise,19,1,1,Cahokia city thriving,"Cahokian Farmer: Simple black stick figure, brown tunic...",Cahokian Farmer,Scene 1: Minimalistic flat design...,Camera moves in smooth aerial glide...
```

## Troubleshooting

### "File not found"
- Check the script file path
- Use `python generate_video_prompts.py test_script.txt` for the test file

### "No sections detected"
- Verify your script has section titles with colons
- Check that sections are separated by blank lines

### API Errors
- Ensure you have internet connection
- The script uses Anthropic's Claude API (handled automatically in claude.ai)

## Test Run

Try with the included test file:
```bash
python generate_video_prompts.py test_script.txt
```

Expected output:
```
📖 Reading script: test_script.txt
🔍 Parsing sections...
✓ Found 2 sections

🎬 Processing Section 1: Mississippian Depopulation: Cahokia's Diluvian Demise...
  → Calling Claude API for Section 1...
  ✓ Generated 18 scenes

🎬 Processing Section 2: Saharan Hydrological Crisis: The Garamantian Desert Empire...
  → Calling Claude API for Section 2...
  ✓ Generated 20 scenes

💾 Writing CSV: test_script_prompts.csv

✅ SUCCESS!
✓ Total sections processed: 2
✓ Total scenes generated: 38
✓ Output file: test_script_prompts.csv
```

## For Your Full 12-Section Script

Replace `test_script.txt` with your complete script file:
```bash
python generate_video_prompts.py my_full_script.txt
```

Expected processing time: ~2-3 minutes for 12 sections

---

**One command. One CSV. Ready for production.**
