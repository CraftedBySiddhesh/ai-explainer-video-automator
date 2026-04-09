import json
import os
import re
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Keep this between 15 and 25 as per your requirement
SCENE_COUNT = 20

SYSTEM_PROMPT = """
You convert a historical or documentary script into three tightly structured prompt lists for a visual generation pipeline.

Your job is to:
1. Extract timeline-aware personas directly from the script.
2. Create character prompts first.
3. Create image scene prompts based on those characters and the script timeline.
4. Create animation prompts based on those image scenes.

Output requirements:
1. Use the provided tool to return structured data.
2. Persona names must be single words only.
3. Do not include explanations, markdown, or extra commentary.
4. The number of image prompts and animation prompts must exactly match the requested number of scenes.
5. Image scene names must be Scene1, Scene2, Scene3 and so on.
6. Animation names must match image scene names exactly.

Character prompt rules:
1. Each character must be visually complete and self-contained.
2. Every character prompt must fully describe the stick figure so it can be generated independently.
3. Use flat 2D colored minimalistic illustration style.
4. Character style must be:
   - simple black stick figure body
   - clean black outlines
   - colored clothing and accessories
   - minimal facial detail
   - white background
   - no text
   - full body visible
   - shown in 3 to 4 directions when appropriate
5. Clothing, tools, accessories, hairstyle, headwear, and props must match the script timeline, geography, and role.
6. Avoid generic modern details unless the script clearly requires them.
7. Keep the design simple, readable, and consistent for reuse in later scene generation.

Image prompt rules:
1. Each image prompt must create a full scene based on the script timeline.
2. Each image prompt must directly use the character names from the character list.
3. Do not fully repeat the complete character design description inside image prompts.
4. Instead, reference the character names clearly and describe:
   - what they are doing
   - where they are
   - what objects or environment are around them
   - what event from the script is happening
   - the emotional or historical context if relevant
5. Assume the referenced character names already define the visual design.
6. Keep image prompts visually clean and generation-friendly.
7. Images must not contain unnecessary text, labels, captions, symbols, or typography.
8. Scene style must remain:
   - flat 2D colored minimalistic illustration
   - simple black stick figures with clean black outlines
   - colored clothing and props
   - white background unless the scene absolutely needs a minimal ground, river, crop field, settlement, mountain, desert, ruins, water system, or other simple environmental element
   - no text

Animation prompt rules:
1. Each animation prompt must be written for the corresponding image scene.
2. Reference the related image scene name or characters clearly.
3. Describe motion, action, transition, and emotional tone.
4. Keep movement simple, clean, and suitable for minimalistic 2D animation.
5. Do not introduce new characters or events that are not present in the script.
6. No text should appear in the animation.

Consistency rules:
1. The same character name must represent the same visual persona across all outputs.
2. Scene prompts must progress in the same order as the script timeline.
3. Prompts must be concise but descriptive enough for direct use in generation.
4. If the script is long or event-rich, create detailed scene progression.
5. Use exactly the requested number of scenes.
"""

USER_TEMPLATE = """
Heading:
{heading}

Script:
{script}

Number of scenes: {num_scenes}

Instructions:
- Generate EXACTLY {num_scenes} image scenes based on the script timeline.
- Generate EXACTLY {num_scenes} animation prompts matching those image scenes.
- Image scene names must be Scene1, Scene2, Scene3 and so on.
- Animation names must match image scene names exactly.
- Use single-word names for character personas.
- Keep all prompts generation-ready.
"""

TOOL_SCHEMA = {
    "name": "save_prompt_data",
    "description": "Return structured prompt data for characters, images, and animations.",
    "input_schema": {
        "type": "object",
        "properties": {
            "characters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "prompt": {"type": "string"},
                    },
                    "required": ["name", "prompt"],
                },
            },
            "images": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "prompt": {"type": "string"},
                    },
                    "required": ["name", "prompt"],
                },
            },
            "animations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "prompt": {"type": "string"},
                    },
                    "required": ["name", "prompt"],
                },
            },
        },
        "required": ["characters", "images", "animations"],
    },
}


def sanitize_name(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_-]+", "", name.strip())
    return name or "Item"


def slugify_heading(heading: str) -> str:
    heading = heading.strip()
    heading = re.sub(r"[^\w\s-]", "", heading)
    heading = re.sub(r"[-\s]+", "_", heading)
    return heading[:120] or "Untitled"


def format_entries(items):
    blocks = []
    for item in items:
        name = sanitize_name(item["name"])
        prompt = " ".join(item["prompt"].strip().split())
        blocks.append(f"{name} - {prompt}")
    return "\n\n".join(blocks) + "\n\n"


def parse_multi_script_file(text: str):
    """
    Splits a text file where each script starts with:
    **Heading**
    followed by that section's body until the next bold heading.
    """
    pattern = re.compile(r"^\*\*(.+?)\*\*\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))

    if not matches:
        raise ValueError(
            "No script headings found. Each script must start with a heading like **My Heading**"
        )

    sections = []
    for i, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        if body:
            sections.append({
                "heading": heading,
                "script": body,
            })

    if not sections:
        raise ValueError("Headings were found, but no script content was found under them.")

    return sections


def extract_tool_data(response):
    tool_block = next(
        (block for block in response.content if getattr(block, "type", "") == "tool_use"),
        None,
    )

    if not tool_block:
        raise ValueError(f"No tool output returned. Full response: {response}")

    data = tool_block.input
    required = {"characters", "images", "animations"}
    if not required.issubset(data.keys()):
        raise ValueError(f"Missing required keys. Found: {list(data.keys())}")

    return data


def validate_counts(data, expected_scene_count: int):
    if len(data["images"]) != expected_scene_count:
        raise ValueError(
            f"Expected {expected_scene_count} image scenes, got {len(data['images'])}."
        )

    if len(data["animations"]) != expected_scene_count:
        raise ValueError(
            f"Expected {expected_scene_count} animation scenes, got {len(data['animations'])}."
        )

    expected_names = [f"Scene{i}" for i in range(1, expected_scene_count + 1)]
    image_names = [item["name"] for item in data["images"]]
    animation_names = [item["name"] for item in data["animations"]]

    if image_names != expected_names:
        raise ValueError(
            f"Image scene names must be sequential: {expected_names}\nGot: {image_names}"
        )

    if animation_names != expected_names:
        raise ValueError(
            f"Animation scene names must match image scene names exactly.\nExpected: {expected_names}\nGot: {animation_names}"
        )


def save_outputs(data, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "characters_prompts.txt": format_entries(data["characters"]),
        "image_prompts.txt": format_entries(data["images"]),
        "animation_prompts.txt": format_entries(data["animations"]),
    }

    for filename, content in files.items():
        (output_dir / filename).write_text(content, encoding="utf-8")

    return output_dir


def generate_prompt_data(client: Anthropic, heading: str, script_text: str, num_scenes: int):
    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        temperature=0.2,
        system=SYSTEM_PROMPT,
        tools=[TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "save_prompt_data"},
        messages=[
            {
                "role": "user",
                "content": USER_TEMPLATE.format(
                    heading=heading,
                    script=script_text,
                    num_scenes=num_scenes,
                ),
            }
        ],
    )

    data = extract_tool_data(response)
    validate_counts(data, num_scenes)
    return data


def generate_prompt_files_for_sections(
    input_file: str,
    output_root: str = "outputs",
    num_scenes: int = SCENE_COUNT,
):
    if not API_KEY:
        raise ValueError("Set ANTHROPIC_API_KEY in your .env file or environment.")

    if not (15 <= num_scenes <= 25):
        raise ValueError("num_scenes must be between 15 and 25.")

    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    text = input_path.read_text(encoding="utf-8")
    sections = parse_multi_script_file(text)

    client = Anthropic(api_key=API_KEY)
    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)

    summary = []

    for index, section in enumerate(sections, start=1):
        heading = section["heading"]
        script_text = section["script"]

        folder_name = f"{index:02d}_{slugify_heading(heading)}"
        section_output_dir = output_root_path / folder_name

        print(f"Processing {index}/{len(sections)}: {heading}")

        data = generate_prompt_data(
            client=client,
            heading=heading,
            script_text=script_text,
            num_scenes=num_scenes,
        )

        save_outputs(data, section_output_dir)
        summary.append((heading, section_output_dir))

    return summary


if __name__ == "__main__":
    # Change this to your actual multi-script txt file
    INPUT_FILE = "test_script.txt"

    # Change this anywhere from 15 to 25
    NUM_SCENES = 20

    results = generate_prompt_files_for_sections(
        input_file=INPUT_FILE,
        output_root="outputs",
        num_scenes=NUM_SCENES,
    )

    print("\nDone.\n")
    for heading, folder in results:
        print(f"{heading} -> {folder.resolve()}")
