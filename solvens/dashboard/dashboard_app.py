"""
solvens/dashboard/dashboard_app.py
==================================

Streamlit Dashboard MVP for Solvens Core.

Shows:
- Provider status
- Cost tracking
- Task queue
- Agent activity

Usage:
    streamlit run solvens/dashboard/dashboard_app.py
"""

import streamlit as st
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random

try:
    from solvens.providers.cost_tracker import CostTracker, format_cost, format_tokens, Provider
    from solvens.providers.cost_tracker import ProviderStats
    COST_TRACKER_AVAILABLE = True
except ImportError:
    COST_TRACKER_AVAILABLE = False


# ============================================================
# Mock Data for Demo
# ============================================================

def generate_mock_stats() -> Dict[str, ProviderStats]:
    """Generate mock provider stats for demo."""
    stats = {}
    providers = [
        ("openai", "GPT-4 Turbo"),
        ("anthropic", "Claude 3 Sonnet"),
        ("ollama", "Llama 3 (Local)"),
        ("google", "Gemini Pro"),
    ]
    
    for provider, model in providers:
        stats[provider] = ProviderStats(
            provider=Provider(provider),
            total_requests=random.randint(10, 100),
            total_input_tokens=random.randint(1000, 50000),
            total_output_tokens=random.randint(500, 25000),
            total_cost=round(random.uniform(0.1, 5.0), 4),
            latency_ms=random.uniform(100, 2000)
        )
    
    return stats


def generate_mock_tasks() -> List[Dict]:
    """Generate mock task queue."""
    tasks = []
    statuses = ["running", "completed", "pending", "failed"]
    agents = ["Researcher", "Coder", "Reviewer", "Summarizer"]
    
    for i in range(8):
        tasks.append({
            "id": f"task_{i+1:03d}",
            "agent": random.choice(agents),
            "status": random.choice(statuses),
            "tokens_in": random.randint(100, 5000),
            "tokens_out": random.randint(50, 2000),
            "cost": round(random.uniform(0.01, 0.5), 4),
            "started": datetime.now() - timedelta(minutes=random.randint(1, 60))
        })
    
    return sorted(tasks, key=lambda x: x["started"], reverse=True)


# ============================================================
# Dashboard Components
# ============================================================

def render_header():
    """Render dashboard header."""
    st.set_page_config(
        page_title="Solvens Core Dashboard",
        page_icon="🌌",
        layout="wide"
    )
    
    st.title("🌌 Solvens Core Dashboard")
    st.markdown("*AI Operating System Kernel*")
    st.divider()


def render_provider_status(stats: Dict[str, ProviderStats]):
    """Render provider status cards."""
    st.subheader("📊 Provider Status")
    
    cols = st.columns(len(stats))
    
    for i, (provider, stat) in enumerate(stats.items()):
        with cols[i]:
            status = "🟢 Online" if stat.total_requests > 0 else "⚪ Unknown"
            cost = format_cost(stat.total_cost)
            
            st.metric(
                label=provider.upper(),
                value=f"{stat.total_requests} req",
                delta=f"{cost}"
            )
            st.caption(f"{status} • {stat.latency_ms:.0f}ms avg")


def render_cost_tracking():
    """Render cost tracking section."""
    st.subheader("💰 Cost Tracking")
    
    # Mock budget data
    budget_limit = 100.0
    budget_spent = random.uniform(20, 80)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Total Spent",
            value=format_cost(budget_spent),
            delta=f"{(budget_spent/budget_limit*100):.1f}% of budget"
        )
    
    with col2:
        st.metric(
            label="This Week",
            value=format_cost(random.uniform(5, 30)),
            delta=f"{random.randint(-20, 20)}% vs last week"
        )
    
    with col3:
        st.metric(
            label="Predicted Monthly",
            value=format_cost(random.uniform(100, 500)),
            delta="Based on current usage"
        )
    
    # Progress bar
    progress = budget_spent / budget_limit
    st.progress(progress, text=f"Budget: {progress*100:.1f}% used")


def render_task_queue(tasks: List[Dict]):
    """Render task queue."""
    st.subheader("📋 Task Queue")
    
    # Filter options
    col1, col2 = st.columns([3, 1])
    with col1:
        filter_status = st.multiselect(
            "Filter by status",
            ["running", "completed", "pending", "failed"],
            default=["running", "completed", "pending", "failed"]
        )
    with col2:
        refresh = st.button("🔄 Refresh")
        if refresh:
            st.rerun()
    
    # Filter tasks
    filtered_tasks = [t for t in tasks if t["status"] in filter_status]
    
    # Display as table
    if filtered_tasks:
        df_data = []
        for task in filtered_tasks[:10]:
            df_data.append({
                "ID": task["id"],
                "Agent": task["agent"],
                "Status": task["status"],
                "Tokens In": format_tokens(task["tokens_in"]),
                "Tokens Out": format_tokens(task["tokens_out"]),
                "Cost": format_cost(task["cost"]),
                "Started": task["started"].strftime("%H:%M")
            })
        
        st.dataframe(
            df_data,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No tasks matching filter")


def render_cosmos_visualization():
    """Render Cosmos DAG visualization preview."""
    st.subheader("🌌 Cosmos DAG Preview")
    
    # Example DAG visualization
    st.markdown('''
    ```mermaid
    graph LR
        A[📥 Input] --> B[🔀 Router]
        B --> C[📝 Claude]
        B --> D[💻 GPT-4]
        B --> E[🔍 Gemini]
        C --> F[📤 Output]
        D --> F
        E --> F
    ```
    ''')
    
    # Show example SVG
    st.markdown("""
    <div style="background: #1F2937; padding: 1rem; border-radius: 8px; text-align: center;">
        <svg width="600" height="200" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="#1F2937" rx="8"/>
            
            <!-- Input -->
            <circle cx="50" cy="100" r="25" fill="#06B6D4"/>
            <text x="50" y="105" text-anchor="middle" fill="white" font-size="20">📥</text>
            <text x="50" y="140" text-anchor="middle" fill="#9CA3AF" font-size="12">Input</text>
            
            <!-- Router -->
            <circle cx="150" cy="100" r="25" fill="#3B82F6"/>
            <text x="150" y="105" text-anchor="middle" fill="white" font-size="20">🔀</text>
            <text x="150" y="140" text-anchor="middle" fill="#9CA3AF" font-size="12">Router</text>
            <line x1="75" y1="100" x2="125" y2="100" stroke="#6B7280" stroke-width="2" marker-end="url(#arrow)"/>
            
            <!-- Claude -->
            <circle cx="280" cy="60" r="25" fill="#EC4899"/>
            <text x="280" y="65" text-anchor="middle" fill="white" font-size="20">📝</text>
            <text x="280" y="100" text-anchor="middle" fill="#9CA3AF" font-size="12">Claude</text>
            <line x1="175" y1="85" x2="255" y2="65" stroke="#6B7280" stroke-width="2"/>
            
            <!-- GPT -->
            <circle cx="280" cy="140" r="25" fill="#10B981"/>
            <text x="280" y="145" text-anchor="middle" fill="white" font-size="20">💻</text>
            <text x="280" y="180" text-anchor="middle" fill="#9CA3AF" font-size="12">GPT-4</text>
            <line x1="175" y1="115" x2="255" y2="135" stroke="#6B7280" stroke-width="2"/>
            
            <!-- Output -->
            <circle cx="400" cy="100" r="25" fill="#84CC16"/>
            <text x="400" y="105" text-anchor="middle" fill="white" font-size="20">📤</text>
            <text x="400" y="140" text-anchor="middle" fill="#9CA3AF" font-size="12">Output</text>
            <line x1="305" y1="75" x2="375" y2="95" stroke="#6B7280" stroke-width="2"/>
            <line x1="305" y1="125" x2="375" y2="105" stroke="#6B7280" stroke-width="2"/>
            
            <!-- Arrow marker -->
            <defs>
                <marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="#6B7280"/>
                </marker>
            </defs>
        </svg>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚀 Open Full Visualizer"):
        st.info("Run `python -m solvens.cosmos.visualizer.web_preview` to open the interactive visualizer")


def render_activity_log():
    """Render activity log."""
    st.subheader("📜 Activity Log")
    
    log_entries = [
        ("12:45:23", "info", "Task task_003 completed by Coder"),
        ("12:44:18", "warning", "High latency detected on GPT-4: 2.3s"),
        ("12:43:55", "success", "Provider Claude 3 Sonnet: OK"),
        ("12:42:31", "info", "New task queued: ResearchAgent"),
        ("12:41:02", "error", "Provider DeepSeek: Rate limit exceeded"),
        ("12:40:15", "info", "Budget alert: 75% used"),
    ]
    
    for time, level, message in log_entries:
        icon = {"info": "ℹ️", "warning": "⚠️", "success": "✅", "error": "❌"}.get(level, "•")
        color = {"info": "white", "warning": "#F59E0B", "success": "#10B981", "error": "#EF4444"}.get(level, "white")
        
        st.markdown(f"""
        <div style="padding: 0.5rem; border-left: 3px solid {color}; margin-bottom: 0.5rem;">
            <span style="color: #6B7280; font-size: 0.8rem;">{time}</span>
            <span style="margin-left: 0.5rem;">{icon} {message}</span>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# Main Dashboard
# ============================================================

def main():
    """Main dashboard entry point."""
    render_header()
    
    # Sidebar
    with st.sidebar:
        st.header("Settings")
        
        st.subheader("Providers")
        provider_enabled = {}
        for provider in ["OpenAI", "Anthropic", "Ollama", "Google"]:
            provider_enabled[provider] = st.toggle(provider, value=True)
        
        st.subheader("Budget")
        budget_limit = st.number_input("Monthly Budget ($)", value=100.0, step=10.0)
        
        st.subheader("Refresh")
        auto_refresh = st.checkbox("Auto-refresh", value=False)
        refresh_interval = st.slider("Interval (seconds)", 5, 60, 10) if auto_refresh else 0
        
        st.divider()
        st.caption("Solvens Core v0.5.0")
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Get stats
        stats = generate_mock_stats()
        tasks = generate_mock_tasks()
        
        render_provider_status(stats)
        render_cost_tracking()
        render_task_queue(tasks)
    
    with col2:
        render_cosmos_visualization()
        render_activity_log()
    
    # Auto-refresh
    if auto_refresh and refresh_interval > 0:
        time.sleep(refresh_interval)
        st.rerun()


if __name__ == "__main__":
    main()
