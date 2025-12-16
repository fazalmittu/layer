#!/usr/bin/env python3
"""
Generate OpenAPI specification for the Layer API.
Run from project root: python openapi/generate_openapi.py
Or from openapi dir: cd openapi && python generate_openapi.py
"""

import json
import sys
from pathlib import Path

# Add parent directory to path so we can import main
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

import yaml
from main import app


def generate_openapi_spec():
    """Generate and save the OpenAPI spec in both JSON and YAML formats."""
    openapi_schema = app.openapi()
    
    # Output files go in the same directory as this script
    output_dir = script_dir
    
    # Save as JSON
    json_path = output_dir / "openapi.json"
    with open(json_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"✓ Generated {json_path}")
    
    # Save as YAML
    yaml_path = output_dir / "openapi.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(openapi_schema, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
    print(f"✓ Generated {yaml_path}")
    
    return openapi_schema


if __name__ == "__main__":
    schema = generate_openapi_spec()
    print(f"\nOpenAPI {schema.get('openapi', '3.x')} spec generated")
    print(f"Title: {schema.get('info', {}).get('title')}")
    print(f"Paths: {len(schema.get('paths', {}))}")
