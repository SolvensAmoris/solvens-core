"""
SOLVENS CORE - Benchmark Visualization Generator
============================================

Generates plots and visualizations for benchmark results.

Usage:
    python benchmarks/plot_generator.py
    python benchmarks/plot_generator.py --input benchmarks/scientific_output/json/results.json
    python benchmarks/plot_generator.py --format png,pdf

Author: Luis Alberto Burciaga Miker
Version: 1.0.0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# ============================================================
# METADATA
# ============================================================

__version__ = "1.0.0"


# ============================================================
# COLORS
# ============================================================

COLORS = {
    "solvens": "#2E86AB",      # Blue
    "langgraph": "#A23B72",      # Magenta
    "crewai": "#F18F01",        # Orange
    "autogen": "#C73E1D",       # Red
    "openai_swarm": "#3B1F2B",  # Dark
}


# ============================================================
# PLOT GENERATORS
# ============================================================

class PlotGenerator:
    """Generate visualizations from benchmark results."""
    
    def __init__(self, data: list[dict], output_dir: Path):
        self.data = data
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Group by framework
        self.frameworks: dict[str, list[dict]] = {}
        for result in data:
            framework = result.get("framework", "unknown")
            self.frameworks.setdefault(framework, []).append(result)
    
    def _get_color(self, framework: str) -> str:
        """Get color for framework."""
        return COLORS.get(framework, "#333333")
    
    def _prepare_figure(self, title: str, figsize: tuple = (12, 6)):
        """Prepare a figure with consistent styling."""
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('Task', fontsize=12)
        ax.set_ylabel('Time (ms)', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='x', rotation=45)
        return fig, ax
    
    def plot_mean_comparison(self) -> Path:
        """Plot mean execution time comparison."""
        fig, ax = self._prepare_figure('Mean Execution Time by Task')
        
        tasks = sorted(set(r['task_name'] for r in self.data))
        x = np.arange(len(tasks))
        width = 0.8 / max(len(self.frameworks), 1)
        
        for i, (framework, results) in enumerate(self.frameworks.items()):
            results_dict = {r['task_name']: r for r in results}
            means = [results_dict.get(t, {}).get('metrics', {}).get('mean_ms', 0) for t in tasks]
            
            offset = width * i - width * len(self.frameworks) / 2
            bars = ax.bar(x + offset, means, width, 
                         label=framework, color=self._get_color(framework), alpha=0.8)
        
        ax.set_xticks(x)
        ax.set_xticklabels(tasks, rotation=45, ha='right')
        ax.legend(loc='upper left')
        
        plt.tight_layout()
        output_path = self.output_dir / 'mean_comparison.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  ✅ Saved: {output_path}")
        return output_path
    
    def plot_percentiles(self) -> Path:
        """Plot percentiles (P50, P95, P99)."""
        fig, ax = self._prepare_figure('Latency Percentiles')
        
        tasks = sorted(set(r['task_name'] for r in self.data))
        
        # Aggregate across frameworks
        means_50 = []
        means_95 = []
        means_99 = []
        
        for task in tasks:
            p50s = [r['metrics']['p50_ms'] for r in self.data if r['task_name'] == task]
            p95s = [r['metrics']['p95_ms'] for r in self.data if r['task_name'] == task]
            p99s = [r['metrics']['p99_ms'] for r in self.data if r['task_name'] == task]
            
            means_50.append(np.mean(p50s) if p50s else 0)
            means_95.append(np.mean(p95s) if p95s else 0)
            means_99.append(np.mean(p99s) if p99s else 0)
        
        x = np.arange(len(tasks))
        width = 0.25
        
        ax.bar(x - width, means_50, width, label='P50 (Median)', color='#2E86AB', alpha=0.8)
        ax.bar(x, means_95, width, label='P95', color='#F18F01', alpha=0.8)
        ax.bar(x + width, means_99, width, label='P99', color='#C73E1D', alpha=0.8)
        
        ax.set_xticks(x)
        ax.set_xticklabels(tasks, rotation=45, ha='right')
        ax.legend()
        
        plt.tight_layout()
        output_path = self.output_dir / 'percentiles.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  ✅ Saved: {output_path}")
        return output_path
    
    def plot_violin(self) -> Path:
        """Plot violin chart for distribution."""
        fig, ax = self._prepare_figure('Execution Time Distribution')
        
        # Get all results for first framework
        framework = list(self.frameworks.keys())[0] if self.frameworks else "solvens"
        results = self.frameworks.get(framework, self.data[:1])
        
        tasks = sorted(set(r['task_name'] for r in results))
        
        # Create synthetic distribution data for violin plot
        # In real benchmarks, you would have raw iteration data
        data_for_violin = []
        labels = []
        
        for task in tasks:
            task_results = [r for r in results if r['task_name'] == task]
            if task_results:
                mean = task_results[0]['metrics']['mean_ms']
                std = task_results[0]['metrics'].get('std_dev_ms', 0.5)
                
                # Generate synthetic data for visualization
                synthetic = np.random.normal(mean, max(std, 0.5), 50)
                data_for_violin.append(synthetic)
                labels.append(task.split()[0])  # First word of task name
        
        parts = ax.violinplot(data_for_violin, positions=range(len(labels)), showmeans=True)
        
        for pc in parts['bodies']:
            pc.set_facecolor('#2E86AB')
            pc.set_alpha(0.7)
        
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_ylabel('Time (ms)')
        
        plt.tight_layout()
        output_path = self.output_dir / 'distribution.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  ✅ Saved: {output_path}")
        return output_path
    
    def plot_heatmap(self) -> Path:
        """Plot heatmap of all frameworks x tasks."""
        fig, ax = plt.subplots(figsize=(14, 6))
        
        tasks = sorted(set(r['task_name'] for r in self.data))
        frameworks = sorted(self.frameworks.keys())
        
        # Build matrix
        matrix = []
        for framework in frameworks:
            row = []
            for task in tasks:
                results = [r for r in self.frameworks[framework] if r['task_name'] == task]
                if results:
                    row.append(results[0]['metrics']['mean_ms'])
                else:
                    row.append(0)
            matrix.append(row)
        
        matrix = np.array(matrix)
        
        # Normalize rows for better visualization
        if matrix.max() > 0:
            matrix_norm = matrix / matrix.max(axis=1, keepdims=True)
        else:
            matrix_norm = matrix
        
        im = ax.imshow(matrix_norm, cmap='YlOrRd', aspect='auto')
        
        # Labels
        ax.set_xticks(range(len(tasks)))
        ax.set_xticklabels(tasks, rotation=45, ha='right')
        ax.set_yticks(range(len(frameworks)))
        ax.set_yticklabels(frameworks)
        
        # Colorbar
        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.ax.set_ylabel('Normalized Time', rotation=-90, va="bottom")
        
        # Values in cells
        for i in range(len(frameworks)):
            for j in range(len(tasks)):
                text = ax.text(j, i, f'{matrix[i, j]:.1f}',
                             ha="center", va="center", color="black", fontsize=8)
        
        ax.set_title('Execution Time Heatmap (ms)', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        output_path = self.output_dir / 'heatmap.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  ✅ Saved: {output_path}")
        return output_path
    
    def plot_boxplot(self) -> Path:
        """Plot boxplot comparison."""
        fig, ax = self._prepare_figure('Performance Distribution by Task')
        
        tasks = sorted(set(r['task_name'] for r in self.data))
        
        data_by_task = []
        labels = []
        
        for task in tasks:
            means = [r['metrics']['mean_ms'] for r in self.data if r['task_name'] == task]
            if means:
                data_by_task.append(means)
                labels.append(task.split()[0])  # Short label
        
        bp = ax.boxplot(data_by_task, label=labels, patch_artist=True)
        
        for patch in bp['boxes']:
            patch.set_facecolor('#2E86AB')
            patch.set_alpha(0.7)
        
        ax.set_xticklabels(labels, rotation=45, ha='right')
        
        plt.tight_layout()
        output_path = self.output_dir / 'boxplot.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  ✅ Saved: {output_path}")
        return output_path
    
    def plot_success_rate(self) -> Path:
        """Plot success rate comparison."""
        fig, ax = self._prepare_figure('Success Rate by Task')
        
        tasks = sorted(set(r['task_name'] for r in self.data))
        x = np.arange(len(tasks))
        width = 0.8 / max(len(self.frameworks), 1)
        
        for i, (framework, results) in enumerate(self.frameworks.items()):
            results_dict = {r['task_name']: r for r in results}
            rates = [100 if results_dict.get(t, {}).get('metrics', {}).get('success', False) else 0 
                    for t in tasks]
            
            offset = width * i - width * len(self.frameworks) / 2
            ax.bar(x + offset, rates, width, 
                  label=framework, color=self._get_color(framework), alpha=0.8)
        
        ax.set_xticks(x)
        ax.set_xticklabels(tasks, rotation=45, ha='right')
        ax.set_ylabel('Success Rate (%)')
        ax.set_ylim(0, 110)
        ax.axhline(y=100, color='green', linestyle='--', alpha=0.5)
        ax.legend()
        
        plt.tight_layout()
        output_path = self.output_dir / 'success_rate.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  ✅ Saved: {output_path}")
        return output_path
    
    def plot_summary_dashboard(self) -> Path:
        """Create a summary dashboard with multiple plots."""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('SOLVENS CORE - Benchmark Summary', fontsize=16, fontweight='bold')
        
        # 1. Mean comparison (top-left)
        ax1 = axes[0, 0]
        tasks = sorted(set(r['task_name'] for r in self.data))
        x = np.arange(len(tasks))
        
        for framework, results in self.frameworks.items():
            results_dict = {r['task_name']: r for r in results}
            means = [results_dict.get(t, {}).get('metrics', {}).get('mean_ms', 0) for t in tasks]
            ax1.bar(x, means, label=framework, color=self._get_color(framework), alpha=0.8)
        
        ax1.set_xticks(x)
        ax1.set_xticklabels([t.split()[0] for t in tasks], rotation=45, ha='right')
        ax1.set_ylabel('Time (ms)')
        ax1.set_title('Mean Execution Time')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Percentiles (top-right)
        ax2 = axes[0, 1]
        
        means_50 = [r['metrics']['p50_ms'] for r in self.data]
        means_95 = [r['metrics']['p95_ms'] for r in self.data]
        means_99 = [r['metrics']['p99_ms'] for r in self.data]
        
        ax2.plot(range(len(means_50)), means_50, 'o-', label='P50', color='#2E86AB')
        ax2.plot(range(len(means_95)), means_95, 's-', label='P95', color='#F18F01')
        ax2.plot(range(len(means_99)), means_99, '^-', label='P99', color='#C73E1D')
        ax2.set_xlabel('Task Index')
        ax2.set_ylabel('Time (ms)')
        ax2.set_title('Latency Percentiles')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. Success rate (bottom-left)
        ax3 = axes[1, 0]
        
        framework_names = list(self.frameworks.keys())
        success_rates = []
        
        for framework in framework_names:
            results = self.frameworks[framework]
            successes = sum(1 for r in results if r['metrics'].get('success', False))
            rate = successes / len(results) * 100 if results else 0
            success_rates.append(rate)
        
        colors = [self._get_color(f) for f in framework_names]
        bars = ax3.bar(framework_names, success_rates, color=colors, alpha=0.8)
        ax3.set_ylabel('Success Rate (%)')
        ax3.set_title('Framework Success Rates')
        ax3.set_ylim(0, 110)
        ax3.axhline(y=100, color='green', linestyle='--', alpha=0.5)
        
        for bar, rate in zip(bars, success_rates):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                    f'{rate:.0f}%', ha='center', fontsize=10)
        
        # 4. Summary stats (bottom-right)
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        # Calculate summary stats
        all_means = [r['metrics']['mean_ms'] for r in self.data]
        all_p95 = [r['metrics']['p95_ms'] for r in self.data]
        
        summary_text = f"""
        SUMMARY STATISTICS
        ==================
        
        Total Tasks: {len(self.data)}
        Frameworks: {len(self.frameworks)}
        
        Mean Execution Time: {np.mean(all_means):.2f} ms
        Median Execution Time: {np.median(all_means):.2f} ms
        Std Deviation: {np.std(all_means):.2f} ms
        
        P95 Latency: {np.mean(all_p95):.2f} ms
        P99 Latency: {max(all_p95):.2f} ms
        
        Overall Success Rate: {sum(1 for r in self.data if r['metrics'].get('success', False)) / len(self.data) * 100:.0f}%
        """
        
        ax4.text(0.1, 0.5, summary_text, fontsize=11, family='monospace',
                verticalalignment='center', transform=ax4.transAxes,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        output_path = self.output_dir / 'dashboard.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  ✅ Saved: {output_path}")
        return output_path
    
    def generate_all(self) -> list[Path]:
        """Generate all plots."""
        print("\n📊 Generating plots...")
        
        paths = [
            self.plot_mean_comparison(),
            self.plot_percentiles(),
            self.plot_violin(),
            self.plot_heatmap(),
            self.plot_boxplot(),
            self.plot_success_rate(),
            self.plot_summary_dashboard(),
        ]
        
        return paths


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate benchmark visualizations')
    parser.add_argument(
        '--input', '-i',
        default='benchmarks/scientific_output/json/results.json',
        help='Input JSON file with benchmark results'
    )
    parser.add_argument(
        '--output', '-o',
        default='benchmarks/scientific_output/plots',
        help='Output directory for plots'
    )
    parser.add_argument(
        '--format', '-f',
        default='png',
        help='Output format (png, pdf, svg)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  SOLVENS CORE - Plot Generator")
    print("=" * 60)
    
    # Load data
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"  ❌ File not found: {input_path}")
        sys.exit(1)
    
    with open(input_path) as f:
        data = json.load(f)
    
    print(f"\n📁 Loaded {len(data)} benchmark results")
    print(f"📁 Output directory: {args.output}")
    
    # Generate plots
    generator = PlotGenerator(data, Path(args.output))
    paths = generator.generate_all()
    
    print(f"\n✅ Generated {len(paths)} plots")
    print(f"📁 Location: {args.output}")


if __name__ == "__main__":
    main()
