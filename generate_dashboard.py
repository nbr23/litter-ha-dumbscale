#!/usr/bin/env python3
# /// script
# dependencies = [
#   "jinja2>=3.0",
# ]
# ///

import argparse
import json
import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "_", slug)
    return slug


def validate_entity_id(entity_id: str) -> bool:
    pattern = r"^[a-z_]+\.[a-z0-9_]+$"
    return bool(re.match(pattern, entity_id.lower()))


def prompt_entity(prompt: str, default: str) -> str:
    while True:
        value = input(f"{prompt} [{default}]: ").strip() or default
        if validate_entity_id(value):
            return value
        print("  Invalid entity ID format. Expected: domain.entity_name")


def prompt_cats() -> list[dict]:
    cats = []
    print("\nEnter cat names (one per line, empty line to finish):")
    while True:
        name = input(f"  Cat {len(cats) + 1}: ").strip()
        if not name:
            if not cats:
                print("  You must enter at least one cat.")
                continue
            break
        cats.append({"name": name, "slug": slugify(name)})
    return cats


def parse_cats(cats_str: str) -> list[dict]:
    cats = []
    for name in cats_str.split(","):
        name = name.strip()
        if name:
            cats.append({"name": name, "slug": slugify(name)})
    return cats


def interactive_mode() -> dict:
    print("Litter Robot Dashboard Generator")
    print("=" * 40)
    print("\nEnter your Litter-Robot entity IDs:")

    config = {
        "weight_sensor_entity": prompt_entity(
            "  Pet weight sensor", "sensor.litter_robot_pet_weight"
        ),
        "litter_level_entity": prompt_entity(
            "  Litter level sensor", "sensor.litter_robot_litter_level"
        ),
        "waste_drawer_entity": prompt_entity(
            "  Waste drawer sensor", "sensor.litter_robot_waste_drawer"
        ),
        "vacuum_entity": prompt_entity("  Robot status entity", "vacuum.litter_robot"),
        "cats": prompt_cats(),
    }

    return config


def cli_mode(args: argparse.Namespace) -> dict:
    cats = parse_cats(args.cats)
    if not cats:
        print("Error: At least one cat name is required.", file=sys.stderr)
        sys.exit(1)

    for entity_name, entity_id in [
        ("--weight-sensor", args.weight_sensor),
        ("--litter-level", args.litter_level),
        ("--waste-drawer", args.waste_drawer),
        ("--vacuum", args.vacuum),
    ]:
        if not validate_entity_id(entity_id):
            print(
                f"Error: Invalid entity ID for {entity_name}: {entity_id}",
                file=sys.stderr,
            )
            sys.exit(1)

    return {
        "weight_sensor_entity": args.weight_sensor,
        "litter_level_entity": args.litter_level,
        "waste_drawer_entity": args.waste_drawer,
        "vacuum_entity": args.vacuum,
        "cats": cats,
    }


def config_file_mode(config_path: Path) -> dict:
    with open(config_path) as f:
        raw = json.load(f)

    cats = [{"name": name, "slug": slugify(name)} for name in raw.get("cats", [])]
    if not cats:
        print("Error: At least one cat name is required in config.", file=sys.stderr)
        sys.exit(1)

    entity_fields = [
        ("weight_sensor_entity", "sensor.litter_robot_pet_weight"),
        ("litter_level_entity", "sensor.litter_robot_litter_level"),
        ("waste_drawer_entity", "sensor.litter_robot_waste_drawer"),
        ("vacuum_entity", "vacuum.litter_robot"),
    ]

    config = {"cats": cats}
    for field, default in entity_fields:
        entity_id = raw.get(field, default)
        if not validate_entity_id(entity_id):
            print(f"Error: Invalid entity ID for {field}: {entity_id}", file=sys.stderr)
            sys.exit(1)
        config[field] = entity_id

    return config


def render_template(config: dict) -> str:
    template_dir = Path(__file__).parent / "dashboards"
    env = Environment(
        loader=FileSystemLoader(template_dir),
        keep_trailing_newline=True,
    )
    template = env.get_template("litter_robot.yaml.j2")
    return template.render(**config)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a customized Litter Robot dashboard for Home Assistant.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using config file (recommended)
  uv run --script generate_dashboard.py --config cats.json -o my_dashboard.yaml

  # Interactive mode
  uv run --script generate_dashboard.py

  # CLI mode
  uv run --script generate_dashboard.py \\
    --cats "Whiskers,Mittens" \\
    --weight-sensor sensor.litter_robot_pet_weight \\
    --litter-level sensor.litter_robot_litter_level \\
    --waste-drawer sensor.litter_robot_waste_drawer \\
    --vacuum vacuum.litter_robot \\
    -o my_dashboard.yaml
""",
    )

    parser.add_argument(
        "--config",
        "-c",
        help="Path to JSON config file (see cats.sample.json)",
    )
    parser.add_argument(
        "--cats",
        help="Comma-separated list of cat names",
    )
    parser.add_argument(
        "--weight-sensor",
        default="sensor.litter_robot_pet_weight",
        help="Pet weight sensor entity ID",
    )
    parser.add_argument(
        "--litter-level",
        default="sensor.litter_robot_litter_level",
        help="Litter level sensor entity ID",
    )
    parser.add_argument(
        "--waste-drawer",
        default="sensor.litter_robot_waste_drawer",
        help="Waste drawer sensor entity ID",
    )
    parser.add_argument(
        "--vacuum",
        default="vacuum.litter_robot",
        help="Robot status entity ID",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: stdout)",
    )

    args = parser.parse_args()

    if args.config:
        config = config_file_mode(Path(args.config))
    elif args.cats:
        config = cli_mode(args)
    else:
        config = interactive_mode()

    # Render template
    output = render_template(config)

    # Write output
    if args.output:
        Path(args.output).write_text(output)
        print(f"Dashboard written to: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
