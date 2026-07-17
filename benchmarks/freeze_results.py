"""
SOLVENS CORE - Benchmark Results Freeze Script
============================================

This script freezes benchmark results into a reproducible package.

Usage:
    python benchmarks/freeze_results.py --version 1.0.0

Output:
    SOLVENS_BENCHMARK_v{version}/
    ├── BENCHMARKS.md
    ├── METHODOLOGY.md
    ├── REPRODUCIBILITY.md
    ├── data/
    ├── plots/
    ├── environment/
    └── scripts/

Author: Luis Alberto Burciaga Miker
Version: 1.0.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# ============================================================
# CONFIGURATION
# ============================================================

class FreezeConfig:
    """Configuration for freezing results."""
    
    def __init__(
        self,
        version: str,
        output_dir: Path = Path("benchmark_releases"),
        source_dir: Path = Path("benchmarks/scientific_output"),
    ):
        self.version = version
        self.output_dir = Path(output_dir) / f"SOLVENS_BENCHMARK_v{version}"
        self.source_dir = Path(source_dir)
        
    @property
    def tarball_path(self) -> Path:
        """Path to the tarball to be created."""
        return Path(f"{self.output_dir}.tar.gz")


# ============================================================
# FILE GENERATORS
# ============================================================

def generate_methodology_md(config: FreezeConfig) -> str:
    """Generate METHODOLOGY.md content."""
    return '''# Benchmark Methodology

**Version:** {version}  
**Date:** {date}  
**Author:** Luis Alberto Burciaga Miker

---

## Experimental Setup

### Hardware
- CPU: [See environment.yml]
- Memory: [See environment.yml]
- Network: [See environment.yml]

### Software
- Python: [See environment.yml]
- Model: gpt-4o-mini (OpenAI)
- Temperature: 0.0
- Max Tokens: 2048

### Tasks
8 standardized tasks were used:
1. Code Generation
2. Data Analysis
3. Research Synthesis
4. Text Summarization
5. Question Answering
6. Agent Coordination
7. Parallel Executor
8. Sequential Workflow

### Metrics
- **Mean Execution Time**: Arithmetic mean of all runs
- **P50 (Median)**: 50th percentile
- **P95**: 95th percentile
- **P99**: 99th percentile
- **Cost per Task**: Calculated from token counts using OpenAI pricing
- **Success Rate**: Percentage of successful runs

### Pricing Used
```
gpt-4o-mini:
  - Input: $0.15 per 1M tokens
  - Output: $0.60 per 1M tokens
```

---

## Statistical Methods

### Confidence Intervals
95% confidence intervals were calculated using bootstrap resampling (1000 iterations).

### Significance Testing
Statistical significance was assessed using Welch's t-test for unequal variances.

### Multiple Comparison Correction
Bonferroni correction was applied for comparisons across multiple tasks.

---

## Limitations

1. **Network Variance**: Not controlled in current benchmarks
2. **API Drift**: OpenAI API behavior may change over time
3. **Temperature**: Fixed at 0 for reproducibility; may not reflect production use
4. **Sample Size**: 1000 runs per framework may not capture all edge cases

---

## How to Reproduce

See REPRODUCIBILITY.md for detailed instructions.

---

## Citation

```bibtex
@misc{{solvens2025benchmark,
  title={{SOLVENS CORE Benchmark Results v{version}}},
  author={{Luis Alberto Burciaga Miker}},
  year={{2025}},
  howpublished={{\\url{{https://github.com/SolvensAmoris/solvens-core}}}},
  version={{{version}}}
}}
```
'''.format(version=config.version, date=datetime.now().date())


def generate_reproducibility_md(config: FreezeConfig) -> str:
    """Generate REPRODUCIBILITY.md content."""
    return '''# Reproducibility Guide

**Version:** {version}  
**Date:** {date}

---

## Prerequisites

1. Python 3.12+
2. pip or conda
3. OpenAI API key
4. ~$50 for running benchmarks

---

## Environment Setup

### Option 1: Conda (Recommended)

```bash
# Create environment
conda env create -f environment.yml

# Activate
conda activate solvens-benchmark
```

### Option 2: pip

```bash
# Install dependencies
pip install -r requirements.txt
```

---

## Running Benchmarks

### 1. Configure API Key

```bash
export OPENAI_API_KEY="your-key-here"
```

### Option 2: .env file

```bash
cp .env.example .env
# Edit .env with your API key
```

### 2. Run Calibration (Recommended First)

```bash
python benchmarks/calibration.py --runs 50
```

Verify output in `calibration_output/calibration.csv`.

### 3. Run Full Benchmarks

```bash
# SOLVENS
python benchmarks/scientific.py --framework solvens --runs 1000

# LangGraph (if implemented)
./scripts/run_langgraph.sh

# AutoGen (if implemented)
./scripts/run_autogen.sh
```

### 4. Generate Reports

```bash
python benchmarks/plot_generator.py --input benchmarks/scientific_output/json/results.json
```

---

## Expected Output

After running, you should have:
- `data/SOLVENS_results.csv` - Raw SOLVENS data
- `plots/dashboard.png` - Summary visualization
- `BENCHMARKS.md` - Complete report

---

## Verifying Results

### Check Token Counts

Compare token counts in results with your OpenAI usage dashboard.

### Check Costs

Calculate expected cost:
```
Total Input Tokens × $0.15/1M + Total Output Tokens × $0.60/1M
```

Compare with API billing.

### Statistical Verification

Run provided statistical tests to verify reported confidence intervals.

---

## Troubleshooting

### "API key not configured"
Set `OPENAI_API_KEY` environment variable.

### "Rate limit exceeded"
Add delays between runs or use exponential backoff.

### "Unexpected high costs"
Check for token multiplier bugs in call counting.

---

## Contact

For questions about reproducibility:
- GitHub Issues: https://github.com/SolvensAmoris/solvens-core/issues
- Discussions: https://github.com/SolvensAmoris/solvens-core/discussions
'''.format(version=config.version, date=datetime.now().date())


# ============================================================
# FREEZE PROCESS
# ============================================================

def get_git_info() -> dict:
    """Get current git commit information."""
    try:
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
        
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
        
        return {
            "commit_hash": commit_hash,
            "branch": branch,
            "clean": subprocess.call(["git", "diff-index", "--quiet", "HEAD"]) == 0,
        }
    except subprocess.CalledProcessError:
        return {
            "commit_hash": "unknown",
            "branch": "unknown",
            "clean": False,
        }


def freeze_environment(output_dir: Path):
    """Freeze Python environment."""
    env_dir = output_dir / "environment"
    env_dir.mkdir(parents=True, exist_ok=True)
    
    # Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    with open(env_dir / "commit_hash.txt", "w") as f:
        git_info = get_git_info()
        f.write(f"Commit: {git_info['commit_hash']}\n")
        f.write(f"Branch: {git_info['branch']}\n")
        f.write(f"Clean: {git_info['clean']}\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
    
    # Python version
    with open(env_dir / "python_version.txt", "w") as f:
        f.write(python_version)
    
    # pip freeze
    try:
        subprocess.run(
            ["pip", "freeze"],
            stdout=open(env_dir / "requirements.txt", "w"),
            check=True,
        )
    except subprocess.CalledProcessError:
        pass
    
    # Environment.yml (simplified)
    with open(env_dir / "environment.yml", "w") as f:
        f.write(f'''# Environment specification
name: solvens-benchmark
channels:
  - defaults
  - conda-forge
dependencies:
  - python={python_version}
  - pip
  - pip:
    - -r requirements.txt
''')


def copy_source_data(config: FreezeConfig, output_dir: Path):
    """Copy source data to output directory."""
    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy results
    source_json = config.source_dir / "json" / "results.json"
    if source_json.exists():
        shutil.copy(source_json, data_dir / "SOLVENS_results.json")
    
    source_csv = config.source_dir / "csv" / "results.csv"
    if source_csv.exists():
        shutil.copy(source_csv, data_dir / "SOLVENS_results.csv")
    
    # Copy plots
    plots_dir = output_dir / "plots"
    plots_source = config.source_dir / "plots"
    if plots_source.exists():
        shutil.copytree(plots_source, plots_dir, dirs_exist_ok=True)


def create_scripts(output_dir: Path):
    """Create benchmark execution scripts."""
    scripts_dir = output_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    
    # SOLVENS script
    with open(scripts_dir / "run_solvens.sh", "w") as f:
        f.write('''#!/bin/bash
# Run SOLVENS benchmarks

set -e

export OPENAI_API_KEY="${OPENAI_API_KEY:-$1}"

if [ -z "$OPENAI_API_KEY" ]; then
    echo "Usage: $0 <api_key>"
    exit 1
fi

echo "Running SOLVENS benchmarks..."
python benchmarks/scientific.py --framework solvens --runs 1000

echo "Generating plots..."
python benchmarks/plot_generator.py

echo "Done! Results in benchmarks/scientific_output/"
''')
    
    # Make executable
    os.chmod(scripts_dir / "run_solvens.sh", 0o755)


def create_api_config(output_dir: Path):
    """Create API configuration template."""
    config_dir = output_dir / "environment"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    with open(config_dir / "api_config.example.json", "w") as f:
        json.dump({
            "model": "gpt-4o-mini",
            "temperature": 0.0,
            "max_tokens": 2048,
            "pricing": {
                "input_per_1m": 0.15,
                "output_per_1m": 0.60,
            },
            "note": "API key should be set via environment variable OPENAI_API_KEY"
        }, f, indent=2)


def create_tarball(output_dir: Path) -> Path:
    """Create tarball of frozen results."""
    import tarfile
    
    tarball_path = Path(f"{output_dir}.tar.gz")
    
    with tarfile.open(tarball_path, "w:gz") as tar:
        tar.add(output_dir, arcname=output_dir.name)
    
    return tarball_path


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Freeze benchmark results")
    parser.add_argument(
        "--version",
        type=str,
        required=True,
        help="Version string (e.g., 1.0.0)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmark_releases",
        help="Output directory"
    )
    parser.add_argument(
        "--no-tarball",
        action="store_true",
        help="Skip creating tarball"
    )
    
    args = parser.parse_args()
    
    config = FreezeConfig(
        version=args.version,
        output_dir=Path(args.output),
    )
    
    print("=" * 60)
    print("  SOLVENS CORE - Benchmark Freeze")
    print("=" * 60)
    print(f"\nVersion: {config.version}")
    print(f"Output: {config.output_dir}")
    
    # Create output directory
    config.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate documentation
    print("\nGenerating documentation...")
    
    with open(config.output_dir / "METHODOLOGY.md", "w") as f:
        f.write(generate_methodology_md(config))
    
    with open(config.output_dir / "REPRODUCIBILITY.md", "w") as f:
        f.write(generate_reproducibility_md(config))
    
    # Copy benchmark report
    benchmarks_src = Path("docs/BENCHMARKS.md")
    if benchmarks_src.exists():
        shutil.copy(benchmarks_src, config.output_dir / "BENCHMARKS.md")
    
    # Freeze environment
    print("Freezing environment...")
    freeze_environment(config.output_dir)
    
    # Copy data
    print("Copying data...")
    copy_source_data(config, config.output_dir)
    
    # Create scripts
    print("Creating scripts...")
    create_scripts(config.output_dir)
    
    # Create API config
    print("Creating API config...")
    create_api_config(config.output_dir)
    
    # List contents
    print("\nGenerated files:")
    for f in sorted(config.output_dir.rglob("*")):
        if f.is_file():
            rel_path = f.relative_to(config.output_dir)
            size = f.stat().st_size
            print(f"  {rel_path} ({size} bytes)")
    
    # Create tarball
    if not args.no_tarball:
        print("\nCreating tarball...")
        tarball = create_tarball(config.output_dir)
        print(f"  Created: {tarball} ({tarball.stat().st_size} bytes)")
    
    print("\n" + "=" * 60)
    print("  Freeze Complete!")
    print("=" * 60)
    print(f"\nPackage: {config.output_dir}")
    if not args.no_tarball:
        print(f"Archive: {tarball}")
    print("\nNext steps:")
    print("  1. Review generated files")
    print("  2. Upload to GitHub Release")
    print("  3. Request external audit")


if __name__ == "__main__":
    main()
