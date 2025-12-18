#!/usr/bin/env python3
"""
CLI Script for generating synthetic supply chain data.

Generates datasets of various sizes for development, testing, and demonstration.

Usage:
    python scripts/seed_database.py small   # ~100 nodes
    python scripts/seed_database.py medium  # ~5000 nodes
    python scripts/seed_database.py large   # ~50000 nodes
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_data import (
    SupplyChainGenerator,
    RiskEventGenerator,
    generate_small_dataset,
    generate_medium_dataset,
    generate_large_dataset,
)


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic supply chain data"
    )
    parser.add_argument(
        "size",
        choices=["small", "medium", "large", "custom"],
        help="Dataset size to generate",
    )
    parser.add_argument(
        "--suppliers",
        type=int,
        default=50,
        help="Number of suppliers (custom mode)",
    )
    parser.add_argument(
        "--components",
        type=int,
        default=100,
        help="Number of components (custom mode)",
    )
    parser.add_argument(
        "--products",
        type=int,
        default=5,
        help="Number of products (custom mode)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: data/{size}_supply_chain.json)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--graph-format",
        action="store_true",
        help="Export in graph format (nodes/edges) for Neo4j",
    )
    parser.add_argument(
        "--include-events",
        type=int,
        default=0,
        help="Number of risk events to generate",
    )

    args = parser.parse_args()

    print(f"Generating {args.size} dataset with seed {args.seed}...")

    # Generate data based on size
    if args.size == "small":
        data = generate_small_dataset(seed=args.seed)
        default_output = "data/small_supply_chain.json"
    elif args.size == "medium":
        data = generate_medium_dataset(seed=args.seed)
        default_output = "data/medium_supply_chain.json"
    elif args.size == "large":
        data = generate_large_dataset(seed=args.seed)
        default_output = "data/large_supply_chain.json"
    else:  # custom
        generator = SupplyChainGenerator(seed=args.seed)
        data = generator.generate(
            num_suppliers=args.suppliers,
            num_components=args.components,
            num_products=args.products,
        )
        default_output = "data/custom_supply_chain.json"

    # Generate risk events if requested
    if args.include_events > 0:
        event_gen = RiskEventGenerator(seed=args.seed)
        companies = [s["name"] for s in data["suppliers"]]
        locations = list(set(s["location"] for s in data["suppliers"]))
        events = event_gen.generate_events(
            count=args.include_events,
            locations=locations,
            companies=companies,
        )
        data["risk_events"] = [e.model_dump() for e in events]

    # Convert to graph format if requested
    if args.graph_format:
        generator = SupplyChainGenerator(seed=args.seed)
        # Regenerate to get graph format
        if args.size == "small":
            generator.generate(num_suppliers=20, num_components=50, num_products=3)
        elif args.size == "medium":
            generator.generate(num_suppliers=500, num_components=2000, num_products=20)
        elif args.size == "large":
            generator.generate(num_suppliers=5000, num_components=20000, num_products=100)
        else:
            generator.generate(
                num_suppliers=args.suppliers,
                num_components=args.components,
                num_products=args.products,
            )
        data = generator.to_graph_json()

    # Determine output path
    output_path = Path(args.output) if args.output else Path(default_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save to file
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    # Print summary
    print(f"\n✅ Dataset generated successfully!")
    print(f"   Output: {output_path}")

    if "metadata" in data:
        counts = data["metadata"]["counts"]
        print(f"\n   Summary:")
        print(f"   - Suppliers: {counts['suppliers']}")
        print(f"   - Components: {counts['components']}")
        print(f"   - Products: {counts['products']}")
        print(f"   - Locations: {counts['locations']}")
        print(f"   - Supplier→Component links: {counts['supplier_component_links']}")
        print(f"   - Component→Product links: {counts['component_product_links']}")
    elif "nodes" in data:
        print(f"\n   Summary (Graph Format):")
        print(f"   - Nodes: {len(data['nodes'])}")
        print(f"   - Edges: {len(data['edges'])}")

    if "risk_events" in data:
        print(f"   - Risk Events: {len(data['risk_events'])}")


if __name__ == "__main__":
    main()
