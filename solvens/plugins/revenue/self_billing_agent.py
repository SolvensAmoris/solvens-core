"""
solvens/plugins/revenue/self_billing_agent.py
============================================

SELF-BILLING AGENT v0.2
=======================

Plugin que hace que agentes generen revenue automáticamente.

Features:
- Treasury management (SQLite)
- Job billing via payment links
- API cost tracking
- P&L reporting
- Auto-recharge alerts

Autor: Luis Alberto Burciaga Miker
Version: 0.2.0
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path
import json

logger = logging.getLogger("solvens.billing")


# ============================================================
# DATABASE
# ============================================================

class BillingDatabase:
    """SQLite database para billing."""
    
    def __init__(self, db_path: str = ".solvens/billing.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Inicializa schema."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS treasury (
                id TEXT PRIMARY KEY,
                balance REAL DEFAULT 0,
                currency TEXT DEFAULT 'USD',
                updated_at TEXT
            )
        """)
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                type TEXT,
                amount REAL,
                currency TEXT,
                description TEXT,
                provider TEXT,
                tokens INTEGER,
                created_at TEXT
            )
        """)
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT,
                amount REAL,
                paid INTEGER DEFAULT 0,
                payment_link TEXT,
                created_at TEXT,
                completed_at TEXT
            )
        """)
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS api_costs (
                id TEXT PRIMARY KEY,
                provider TEXT,
                model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                cost REAL,
                created_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_treasury(self) -> Dict[str, Any]:
        """Obtiene estado de treasury."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT balance, currency FROM treasury WHERE id = 'main'")
        row = c.fetchone()
        conn.close()
        
        if row:
            return {"balance": row[0], "currency": row[1]}
        return {"balance": 0, "currency": "USD"}
    
    def update_treasury(self, amount: float, currency: str = "USD"):
        """Actualiza balance."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT OR REPLACE INTO treasury (id, balance, currency, updated_at)
            VALUES ('main', ?, ?, ?)
        """, (amount, currency, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def add_transaction(self, tx_type: str, amount: float, description: str, provider: str = None):
        """Agrega transacción."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO transactions (id, type, amount, currency, description, provider, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4())[:8], tx_type, amount, "USD", description, provider, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def record_job(self, amount: float) -> str:
        """Registra job y genera payment link."""
        job_id = str(uuid.uuid4())[:8]
        payment_link = f"https://pay.solvens.amoris/jobs/{job_id}"
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO jobs (id, status, amount, payment_link, created_at)
            VALUES (?, 'pending', ?, ?, ?)
        """, (job_id, amount, payment_link, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return payment_link
    
    def record_api_cost(self, provider: str, model: str, input_tokens: int, output_tokens: int, cost: float):
        """Registra costo de API."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO api_costs (id, provider, model, input_tokens, output_tokens, cost, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4())[:8], provider, model, input_tokens, output_tokens, cost, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_pnl(self, days: int = 30) -> Dict[str, Any]:
        """Calcula P&L para periodo."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Revenue
        c.execute("""
            SELECT SUM(amount) FROM transactions
            WHERE type = 'job_revenue' AND created_at >= ?
        """, (since,))
        revenue = c.fetchone()[0] or 0
        
        # Costs
        c.execute("""
            SELECT SUM(cost) FROM api_costs
            WHERE created_at >= ?
        """, (since,))
        costs = c.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "period_days": days,
            "revenue": revenue,
            "costs": costs,
            "profit": revenue - costs,
            "margin": ((revenue - costs) / revenue * 100) if revenue > 0 else 0
        }


# ============================================================
# SELF BILLING AGENT
# ============================================================

@dataclass
class AgentConfig:
    """Configuración del agente."""
    name: str
    base_price: float = 10.0
    currency: str = "USD"
    min_balance: float = 10.0  # Alert threshold
    auto_recharge: bool = True
    auto_recharge_amount: float = 50.0


@dataclass
class Job:
    """Job del agente."""
    id: str
    prompt: str
    status: str = "pending"
    result: Any = None
    price: float = 0
    cost: float = 0
    profit: float = 0
    payment_link: Optional[str] = None


class SelfBillingAgent:
    """
    Agente que se auto-factura.
    
    Workflow:
    1. Receive job request
    2. Generate payment link
    3. Execute after payment confirmed (or trust mode)
    4. Track API costs
    5. Report P&L
    """
    
    def __init__(
        self,
        config: AgentConfig,
        db_path: str = ".solvens/billing.db"
    ):
        self.config = config
        self.db = BillingDatabase(db_path)
        
        # Initialize treasury if empty
        treasury = self.db.get_treasury()
        if treasury["balance"] == 0:
            self.db.update_treasury(0)
        
        logger.info(f"SelfBillingAgent initialized: {config.name}")
    
    async def create_job(self, prompt: str, trust_mode: bool = False) -> Job:
        """
        Crea un nuevo job.
        
        Args:
            prompt: Request del cliente
            trust_mode: Si True, ejecuta sin esperar pago
        
        Returns:
            Job con payment link
        """
        job_id = str(uuid.uuid4())[:8]
        
        # Calculate price (could be dynamic based on prompt complexity)
        price = self.config.base_price
        
        # Generate payment link
        payment_link = self.db.record_job(price) if not trust_mode else None
        
        job = Job(
            id=job_id,
            prompt=prompt,
            status="awaiting_payment" if not trust_mode else "pending",
            price=price,
            payment_link=payment_link
        )
        
        logger.info(f"Job created: {job_id}, price: ${price}")
        
        return job
    
    async def execute_job(
        self,
        job: Job,
        execute_fn: callable,
        *args,
        **kwargs
    ) -> Job:
        """
        Ejecuta un job con tracking de costos.
        
        Args:
            job: Job a ejecutar
            execute_fn: Función que ejecuta el trabajo
            *args, **kwargs: Args para execute_fn
        """
        # Check balance
        treasury = self.db.get_treasury()
        if treasury["balance"] < self.config.min_balance:
            logger.warning(f"Low balance: ${treasury['balance']:.2f}")
        
        # Record start time
        start_time = datetime.now()
        
        try:
            job.status = "running"
            
            # Execute
            result = await execute_fn(*args, **kwargs)
            job.result = result
            
            # Calculate cost (simulated - real implementation would track actual API usage)
            cost = 0.5  # Placeholder
            job.cost = cost
            job.profit = job.price - cost
            
            # Update database
            self.db.record_api_cost("grok", "grok-2", 1000, 500, cost)
            self.db.add_transaction("api_cost", -cost, f"Job {job.id}", "grok")
            
            # Revenue (in real implementation, this comes after payment)
            self.db.add_transaction("job_revenue", job.price, f"Job {job.id}")
            
            # Update treasury
            new_balance = treasury["balance"] + job.price - cost
            self.db.update_treasury(new_balance)
            
            job.status = "completed"
            
            logger.info(f"Job {job.id} completed: ${job.price} - ${cost} = ${job.profit}")
            
        except Exception as e:
            job.status = "failed"
            job.result = str(e)
            logger.error(f"Job {job.id} failed: {e}")
        
        return job
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene status completo del agente."""
        treasury = self.db.get_treasury()
        pnl = self.db.get_pnl()
        
        return {
            "agent": self.config.name,
            "treasury": treasury,
            "pnl_30d": pnl,
            "alerts": self._check_alerts(treasury)
        }
    
    def _check_alerts(self, treasury: Dict) -> List[str]:
        """Check for alerts."""
        alerts = []
        
        if treasury["balance"] < self.config.min_balance:
            alerts.append(f"LOW_BALANCE: ${treasury['balance']:.2f}")
        
        return alerts
    
    def generate_report(self) -> str:
        """Genera reporte de P&L."""
        status = self.get_status()
        
        report = f"""
╔══════════════════════════════════════════════════════════════════╗
║              SELF-BILLING AGENT REPORT                           ║
╠══════════════════════════════════════════════════════════════════╣
║  Agent: {status['agent']:<54}║
╠══════════════════════════════════════════════════════════════════╣
║  TREASURY                                                        ║
║  Balance: ${status['treasury']['balance']:.2f} {status['treasury']['currency']:<42}║
╠══════════════════════════════════════════════════════════════════╣
║  P&L (Last {status['pnl_30d']['period_days']} days)                                         ║
║  Revenue:    ${status['pnl_30d']['revenue']:.2f}                                       ║
║  Costs:     -${status['pnl_30d']['costs']:.2f}                                       ║
║  Profit:     ${status['pnl_30d']['profit']:.2f}                                       ║
║  Margin:     {status['pnl_30d']['margin']:.1f}%                                           ║
╠══════════════════════════════════════════════════════════════════╣
║  ALERTS                                                         ║"""
        
        if status['alerts']:
            for alert in status['alerts']:
                report += f"\n║  ⚠️  {alert:<57}║"
        else:
            report += f"\n║  ✓ No alerts                                                   ║"
        
        report += """
╚══════════════════════════════════════════════════════════════════╝
"""
        
        return report


# ============================================================
# DEMO
# ============================================================

async def demo():
    """Demo del SelfBillingAgent."""
    print("=" * 60)
    print("SELF-BILLING AGENT v0.2 DEMO")
    print("=" * 60)
    
    # Create agent
    config = AgentConfig(
        name="RevenueAgent",
        base_price=25.0,
        min_balance=10.0
    )
    agent = SelfBillingAgent(config)
    
    # Create job
    print("\n[Creating job...]")
    job = await agent.create_job(
        "Generate a legal memorandum about AI liability",
        trust_mode=True
    )
    print(f"  Job ID: {job.id}")
    print(f"  Price: ${job.price}")
    print(f"  Payment: {job.payment_link or 'TRUST_MODE'}")
    
    # Simulate execution
    async def mock_execute():
        await asyncio.sleep(0.5)
        return "Legal memorandum generated successfully."
    
    print("\n[Executing job...]")
    job = await agent.execute_job(job, mock_execute)
    print(f"  Status: {job.status}")
    print(f"  Result: {job.result[:50]}...")
    print(f"  Cost: ${job.cost}")
    print(f"  Profit: ${job.profit}")
    
    # Report
    print("\n" + agent.generate_report())
    
    print("=" * 60)
    print("Agent ready for monetization!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
