import json
from pathlib import Path


def main():
    p = Path("src/iva/eval/datasets/golden.jsonl")
    lines = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    print(f"Loaded {len(lines)} golden examples.")


if __name__ == "__main__":
    main()
