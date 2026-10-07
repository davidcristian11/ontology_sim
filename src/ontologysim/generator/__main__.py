import argparse
from pathlib import Path

from ontologysim.generator.config import load_generator_config
from ontologysim.generator.pipeline import generate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OntologySim synthetic engineering data.")

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/generator.toml"),
        help="Path to generator TOML configuration.",
    )

    args = parser.parse_args()

    config = load_generator_config(args.config)
    summary = generate_dataset(config)

    print()
    print(f"Profile: {summary.profile_name}")
    print(f"Output:  {summary.output_dir}")

    print()
    print("Ground truth:")
    for name, count in summary.ground_truth_counts.items():
        print(f"  {name}: {count:,}")

    print()
    print("Generated source records:")
    for name, count in summary.source_counts.items():
        print(f"  {name}: {count:,}")

    print()
    print("Files:")
    for path in summary.files:
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"  {path} ({size_mb:.2f} MB)")

    total_mb = summary.total_bytes / (1024 * 1024)

    print()
    print(f"Total generated size: {total_mb:.2f} MB")


if __name__ == "__main__":
    main()
