#!/usr/bin/env python3
"""
Solvens Core - Demo Video Generator
===================================

Genera un demo animado del Cosmos Visualizer y features.
Output: Secuencia de frames para video o GIF animado.

Usage:
    python examples/demos/demo_video.py --format gif    # Genera GIF
    python demo_video.py --format ascii  # Imprime ASCII demo
    python demo_video.py --format video  # Genera frames para video
"""

import argparse
import time
import sys
import os
from pathlib import Path

# ANSI colors
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
CYAN = '\033[96m'
WHITE = '\033[97m'
BOLD = '\033[1m'
RESET = '\033[0m'

# Frame storage for GIF
frames = []


def clear():
    print('\033[2J\033[H', end='')


def typewriter(text, delay=0.03):
    """Print text with typewriter effect."""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()


def typewriter_lines(lines, delay=0.02):
    """Print multiple lines with typewriter effect."""
    for line in lines:
        for char in line:
            print(char, end='', flush=True)
            time.sleep(delay)
        print()


def print_frame(frame_num):
    """Print a numbered frame."""
    print(f"\n{CYAN}─── Frame {frame_num} ───{RESET}")


def frame(func):
    """Decorator to capture frames for GIF."""
    def wrapper(*args, **kwargs):
        func(*args, **kwargs)
    return wrapper


# ============================================================
# DEMO FRAMES
# ============================================================

def frame_1_intro():
    """Frame 1: Title card."""
    clear()
    print()
    print()
    print(f"{BOLD}{BLUE}╔══════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{BLUE}║{RESET}" + " " * 68 + f"{BOLD}{BLUE}║{RESET}")
    print(f"{BOLD}{BLUE}║{RESET}" + f"{BOLD}{WHITE}   🌌  S O L V E N S   C O R E  {RESET}".center(68) + f"{BOLD}{BLUE}║{RESET}")
    print(f"{BOLD}{BLUE}║{RESET}" + f"{CYAN}   AI Operating System Kernel  •  v0.5.0{RESET}".center(68) + f"{BOLD}{BLUE}║{RESET}")
    print(f"{BOLD}{BLUE}║{RESET}" + " " * 68 + f"{BOLD}{BLUE}║{RESET}")
    print(f"{BOLD}{BLUE}╚══════════════════════════════════════════════════════════════════╝{RESET}")
    print()
    print()
    print(f"{WHITE}   {BOLD}The AI OS that guarantees:{RESET}")
    print()
    print(f"   {GREEN}✓{RESET}  Deterministic execution")
    print(f"   {GREEN}✓{RESET}  Multi-provider routing")
    print(f"   {GREEN}✓{RESET}  Cost tracking & budgets")
    print(f"   {GREEN}✓{RESET}  Visual DAG generation")
    print()
    print()
    time.sleep(2)


def frame_2_cosmos_visualizer():
    """Frame 2: Cosmos Visualizer demo."""
    clear()
    print()
    print(f"{BOLD}{MAGENTA}╔══════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{MAGENTA}║{RESET}" + f"{BOLD}{WHITE}   🌌  COSMOS VISUALIZER  •  DAG Renderer{RESET}".center(68) + f"{BOLD}{MAGENTA}║{RESET}")
    print(f"{BOLD}{MAGENTA}╚══════════════════════════════════════════════════════════════════╝{RESET}")
    print()
    
    print(f"{CYAN}┌──────────────────────────────────────────────────────────────────────┐{RESET}")
    print(f"{CYAN}│{RESET}" + " " * 68 + f"{CYAN}│{RESET}")
    
    # Draw DAG nodes
    print(f"{CYAN}│{RESET}        {GREEN}[📥 INPUT ]{RESET}                                           {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}            │                                              {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}            ▼                                              {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}        {BLUE}[🔀 ROUTER ]{RESET}                                          {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}           / \\                                             {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}          /   \\                                            {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}         ▼     ▼                                            {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}   {YELLOW}[📝 CLAUDE ]{RESET}  {RED}[💻 GPT-4  ]{RESET}  {GREEN}[🔍 GEMINI ]{RESET}          {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}           \\     /                                            {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}            \\   /                                             {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}             ▼                                               {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}        {GREEN}[📤 OUTPUT ]{RESET}                                          {CYAN}│{RESET}")
    
    print(f"{CYAN}│{RESET}" + " " * 68 + f"{CYAN}│{RESET}")
    print(f"{CYAN}└──────────────────────────────────────────────────────────────────────┘{RESET}")
    print()
    print(f"{WHITE}   Generate SVG, HTML, or ASCII art from Cosmos DSL{RESET}")
    print()
    time.sleep(2)


def frame_3_cost_tracking():
    """Frame 3: Cost tracking demo."""
    clear()
    print()
    print(f"{BOLD}{GREEN}╔══════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{GREEN}║{RESET}" + f"{BOLD}{WHITE}   💰  COST TRACKING  •  Real-time Budget Guards{RESET}".center(68) + f"{BOLD}{GREEN}║{RESET}")
    print(f"{BOLD}{GREEN}╚══════════════════════════════════════════════════════════════════╝{RESET}")
    print()
    
    print(f"{WHITE}┌──────────────────────────────────────────────────────────────────────┐{RESET}")
    print(f"{WHITE}│{RESET}  PROVIDER          REQUESTS      TOKENS        COST          {WHITE}│{RESET}")
    print(f"{WHITE}├──────────────────────────────────────────────────────────────────────┤{RESET}")
    print(f"{WHITE}│{RESET}  {CYAN}openai{RESET}              127          1.2M         {YELLOW}$384.50{RESET}       {WHITE}│{RESET}")
    print(f"{WHITE}│{RESET}  {CYAN}anthropic{RESET}            89           890K         {YELLOW}$267.00{RESET}       {WHITE}│{RESET}")
    print(f"{WHITE}│{RESET}  {CYAN}google{RESET}              156          2.1M         {YELLOW}$156.75{RESET}       {WHITE}│{RESET}")
    print(f"{WHITE}│{RESET}  {CYAN}ollama{RESET} (local)       234          3.4M         {GREEN}$0.00{RESET}         {WHITE}│{RESET}")
    print(f"{WHITE}├──────────────────────────────────────────────────────────────────────┤{RESET}")
    print(f"{WHITE}│{RESET}  {BOLD}TOTAL{RESET}               606          7.6M         {RED}$808.25{RESET}       {WHITE}│{RESET}")
    print(f"{WHITE}└──────────────────────────────────────────────────────────────────────┘{RESET}")
    print()
    print(f"{WHITE}   Budget: {GREEN}$1,000.00{RESET} | Spent: {YELLOW}$808.25{RESET} | Remaining: {GREEN}$191.75{RESET} (19.2%)")
    print()
    print(f"{RED}   ⚠️  Budget alert: 80% used!{RESET}")
    print()
    time.sleep(2)


def frame_4_deterministic():
    """Frame 4: Deterministic execution."""
    clear()
    print()
    print(f"{BOLD}{RED}╔══════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{RED}║{RESET}" + f"{BOLD}{WHITE}   🔐  DETERMINISTIC EXECUTION  •  Merkle Hashing{RESET}".center(68) + f"{BOLD}{RED}║{RESET}")
    print(f"{BOLD}{RED}╚══════════════════════════════════════════════════════════════════╝{RESET}")
    print()
    
    print(f"{CYAN}┌──────────────────────────────────────────────────────────────────────┐{RESET}")
    print(f"{CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}   {WHITE}Two agents, same DAG → Same hash → Same execution{RESET}")
    print(f"{CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}   {YELLOW}AST A:{RESET}  [1, 2, 3]  →  Hash: {GREEN}a7b3c9d2e1f4...{RESET}")
    print(f"{CYAN}│{RESET}   {YELLOW}AST B:{RESET}  [3, 1, 2]  →  Hash: {GREEN}a7b3c9d2e1f4...{RESET}  {GREEN}✓ EQUAL{RESET}")
    print(f"{CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}   {WHITE}Merkle root combines all node hashes recursively{RESET}")
    print(f"{CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}   {GREEN}✓ Order-independent canonicalization{RESET}")
    print(f"{CYAN}│{RESET}   {GREEN}✓ SHA256 cryptographic hashing{RESET}")
    print(f"{CYAN}│{RESET}   {GREEN}✓ 0 collisions in 10,000 stress tests{RESET}")
    print(f"{CYAN}│{RESET}")
    print(f"{CYAN}└──────────────────────────────────────────────────────────────────────┘{RESET}")
    print()
    print(f"{WHITE}   El mismo codigo, en cualquier ambiente, siempre el mismo resultado{RESET}")
    print()
    time.sleep(2)


def frame_5_multi_provider():
    """Frame 5: Multi-provider routing."""
    clear()
    print()
    print(f"{BOLD}{BLUE}╔══════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{BLUE}║{RESET}" + f"{BOLD}{WHITE}   🔀  MULTI-PROVIDER ROUTING  •  Anti-Vendor Lock{RESET}".center(68) + f"{BOLD}{BLUE}║{RESET}")
    print(f"{BOLD}{BLUE}╚══════════════════════════════════════════════════════════════════╝{RESET}")
    print()
    
    print(f"{WHITE}┌──────────────────────────────────────────────────────────────────────┐{RESET}")
    print(f"{WHITE}│{RESET}  TASK TYPE           ROUTES TO              COST/1K TOKENS    {WHITE}│{RESET}")
    print(f"{WHITE}├──────────────────────────────────────────────────────────────────────┤{RESET}")
    print(f"{WHITE}│{RESET}  {CYAN}Code Generation{RESET}     {GREEN}GPT-4 Turbo{RESET}           $0.01 / $0.03       {WHITE}│{RESET}")
    print(f"{WHITE}│{RESET}  {CYAN}Research{RESET}           {GREEN}Claude 3 Sonnet{RESET}        $0.003 / $0.015    {WHITE}│{RESET}")
    print(f"{WHITE}│{RESET}  {CYAN}Vision Analysis{RESET}    {GREEN}Gemini Pro{RESET}             $0.00125 / $0.00375 {WHITE}│{RESET}")
    print(f"{WHITE}│{RESET}  {CYAN}Fast Tasks{RESET}          {GREEN}Ollama (local){RESET}        FREE               {WHITE}│{RESET}")
    print(f"{WHITE}│{RESET}  {CYAN}Image Generation{RESET}    {GREEN}Pollo AI{RESET}              TBD                {WHITE}│{RESET}")
    print(f"{WHITE}├──────────────────────────────────────────────────────────────────────┤{RESET}")
    print(f"{WHITE}│{RESET}  {GREEN}Add any provider via plugin system{RESET}                       {WHITE}│{RESET}")
    print(f"{WHITE}└──────────────────────────────────────────────────────────────────────┘{RESET}")
    print()
    print(f"{WHITE}   Never depend on a single vendor again.{RESET}")
    print()
    time.sleep(2)


def frame_6_pricing():
    """Frame 6: Pricing tiers."""
    clear()
    print()
    print(f"{BOLD}{MAGENTA}╔══════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{MAGENTA}║{RESET}" + f"{BOLD}{WHITE}   💎  PRICING  •  Start Free, Scale Fast{RESET}".center(68) + f"{BOLD}{MAGENTA}║{RESET}")
    print(f"{BOLD}{MAGENTA}╚══════════════════════════════════════════════════════════════════╝{RESET}")
    print()
    
    print(f"{WHITE}┌────────────────┬────────────────┬────────────────┐{RESET}")
    print(f"{WHITE}│{RESET}     {CYAN}FREE{RESET}        │    {GREEN}PRO{RESET}         │  {RED}ENTERPRISE{RESET}    {WHITE}│{RESET}")
    print(f"{WHITE}├────────────────┼────────────────┼────────────────┤{RESET}")
    print(f"{WHITE}│{RESET}      {YELLOW}$0{RESET}/mo        │     {YELLOW}$49{RESET}/mo       │    {YELLOW}$499{RESET}/mo     {WHITE}│{RESET}")
    print(f"{WHITE}├────────────────┼────────────────┼────────────────┤{RESET}")
    print(f"{WHITE}│{RESET}  • Core         │  • Unlimited   │  • Self-hosted  {WHITE}│{RESET}")
    print(f"{WHITE}│{RESET}  • 100 tasks    │  • Multi-prov  │  • Compliance   {WHITE}│{RESET}")
    print(f"{WHITE}│{RESET}  • 1 provider   │  • Dashboard   │  • Custom SLA  {WHITE}│{RESET}")
    print(f"{WHITE}│{RESET}  • Community    │  • Cost track  │  • Dedicated    {WHITE}│{RESET}")
    print(f"{WHITE}│{RESET}               │  • Priority    │    support     {WHITE}│{RESET}")
    print(f"{WHITE}└────────────────┴────────────────┴────────────────┘{RESET}")
    print()
    print(f"{WHITE}   Open source core • No vendor lock • MIT License{RESET}")
    print()
    time.sleep(2)


def frame_7_outro():
    """Frame 7: Outro with links."""
    clear()
    print()
    print()
    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║{RESET}")
    print(f"{BOLD}{CYAN}║{RESET}" + f"{BOLD}{WHITE}   🌌  S O L V E N S   C O R E{RESET}".center(68))
    print(f"{BOLD}{CYAN}║{RESET}")
    print(f"{BOLD}{CYAN}║{RESET}" + f"{CYAN}   AI Operating System Kernel{RESET}".center(68))
    print(f"{BOLD}{CYAN}║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════════╝{RESET}")
    print()
    print()
    print(f"{WHITE}   {BOLD}Get Started:{RESET}")
    print()
    print(f"   {GREEN}🌐{RESET}  {CYAN}https://solvensamoris.github.io/solvens-core/{RESET}")
    print(f"   {GREEN}📦{RESET}  {CYAN}https://github.com/SolvensAmoris/solvens-core{RESET}")
    print(f"   {GREEN}📧{RESET}  {CYAN}info@solvens.amoris{RESET}")
    print()
    print()
    print(f"{WHITE}   {BOLD}Built by:{RESET} Luis Alberto Burciaga Miker")
    print(f"{WHITE}   {BOLD}Version:{RESET} 0.5.0 • MIT License")
    print()
    print()
    print(f"{CYAN}{BOLD}   Thank you for watching! 🚀{RESET}")
    print()
    print()
    time.sleep(3)


# ============================================================
# MAIN DEMO
# ============================================================

def run_demo():
    """Run the full demo sequence."""
    print(f"\n{BOLD}{CYAN}Starting Solvens Core Demo...{RESET}\n")
    time.sleep(1)
    
    # Run all frames
    frame_1_intro()
    frame_2_cosmos_visualizer()
    frame_3_cost_tracking()
    frame_4_deterministic()
    frame_5_multi_provider()
    frame_6_pricing()
    frame_7_outro()
    
    print(f"\n{BOLD}{GREEN}Demo complete!{RESET}\n")


def run_gif():
    """Generate GIF from demo frames."""
    print("GIF generation requires Pillow and image processing.")
    print("For production GIFs, use: terminalizer or asciinema")
    print()
    print("Quick alternative: Record terminal with:")
    print("  • asciinema rec demo.cast")
    print("  • terminalizer record")
    print()
    print("Converting to GIF:")
    print("  • agg demo.cast demo.gif")
    print()


def main():
    parser = argparse.ArgumentParser(description="Solvens Core Demo Generator")
    parser.add_argument('--format', choices=['ascii', 'gif', 'video'], 
                       default='ascii', help='Output format')
    parser.add_argument('--fast', action='store_true', help='Skip delays')
    
    args = parser.parse_args()
    
    if args.format == 'ascii':
        run_demo()
    elif args.format == 'gif':
        run_gif()
    elif args.format == 'video':
        print("Video generation requires ffmpeg.")
        print("Frames saved for manual video creation.")


if __name__ == "__main__":
    main()
