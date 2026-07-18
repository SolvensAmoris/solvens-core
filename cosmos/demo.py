#!/usr/bin/env python3
"""
Cosmos Engine Demo

Demonstrates the complete orchestration flow:
Task → Plan → Schedule → Execute → Result

Usage:
    python cosmos/demo.py
    python cosmos/demo.py --task "your task here"
"""

import argparse
import asyncio
import sys

from cosmos import Engine, EngineConfig


async def run_demo(task: str = None):
    """Run the demo."""
    print("=" * 70)
    print("  COSMOS ENGINE DEMO")
    print("  Task → Plan → Schedule → Execute → Result")
    print("=" * 70)
    
    if task is None:
        task = (
            "Research the top 5 coffee providers in Mexico, "
            "analyze their prices, and create a summary report"
        )
    
    print(f"\n📋 Task: {task}\n")
    
    # Create engine
    config = EngineConfig(max_concurrent=5)
    engine = Engine(config)
    
    print("⏳ Running task through Cosmos Engine...\n")
    
    # Execute
    result = await engine.run(task)
    
    # Display results
    print("=" * 70)
    print("  RESULTS")
    print("=" * 70)
    
    print(f"\n✅ Plan ID: {result.id}")
    print(f"📊 Status: {result.status.value}")
    print(f"📝 Steps: {len(result.nodes)}")
    
    print("\n📋 Step Execution:")
    print("-" * 70)
    
    for i, node in enumerate(result.nodes, 1):
        status_icon = {
            "completed": "✅",
            "failed": "❌",
            "running": "⏳",
            "pending": "⏳",
            "waiting": "⏳",
        }.get(node.status.value, "❓")
        
        print(f"\n{status_icon} Step {i}: {node.name}")
        print(f"   Type: {node.step_type}")
        print(f"   Provider: {node.provider}")
        print(f"   Status: {node.status.value}")
        
        if node.dependencies:
            dep_names = [n.name for n in result.nodes if n.id in node.dependencies]
            print(f"   Dependencies: {dep_names}")
        
        if node.outputs.get("result"):
            result_text = str(node.outputs["result"])[:60]
            print(f"   Result: {result_text}...")
        
        if node.error:
            print(f"   ❌ Error: {node.error}")
        
        if node.duration_ms > 0:
            print(f"   ⏱️  Duration: {node.duration_ms:.0f}ms")
    
    # Audit log
    print("\n" + "-" * 70)
    print("📜 Audit Log:")
    for entry in engine.get_audit_log():
        event = entry.get("event", "?")
        step = entry.get("step_name", "")
        if event == "step_complete":
            print(f"   ✅ {step}: completed")
        elif event == "task_start":
            print(f"   🚀 Task started")
        elif event == "task_complete":
            print(f"   🎉 Task completed")
    
    print("\n" + "=" * 70)
    print("  DEMO COMPLETE")
    print("=" * 70)
    
    return result


async def run_complex_demo():
    """Run a more complex demo with multiple plans."""
    print("\n" + "=" * 70)
    print("  COMPLEX DEMO: Multiple Tasks")
    print("=" * 70)
    
    tasks = [
        "Research Python web frameworks",
        "Analyze database options for SaaS",
        "Compare cloud providers for ML",
    ]
    
    engine = Engine(EngineConfig(max_concurrent=2))
    
    for i, task in enumerate(tasks, 1):
        print(f"\n📋 Task {i}/3: {task[:50]}...")
        result = await engine.run(task)
        print(f"   ✅ Completed: {len(result.nodes)} steps")


def main():
    parser = argparse.ArgumentParser(description="Cosmos Engine Demo")
    parser.add_argument(
        "--task", "-t",
        type=str,
        default=None,
        help="Task to execute"
    )
    parser.add_argument(
        "--complex", "-c",
        action="store_true",
        help="Run complex demo with multiple tasks"
    )
    
    args = parser.parse_args()
    
    if args.complex:
        asyncio.run(run_complex_demo())
    else:
        asyncio.run(run_demo(args.task))


if __name__ == "__main__":
    main()
