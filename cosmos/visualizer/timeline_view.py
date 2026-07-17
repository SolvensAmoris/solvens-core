"""
timeline_view.py - Timeline Visualization for Temporal Constraints
================================================================

Muestra restricciones temporales como timelines interactivas.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta


@dataclass
class TemporalConstraint:
    """Restricción temporal en Cosmos."""
    id: str
    name: str
    start: Optional[datetime]
    end: Optional[datetime]
    restricted_until: Optional[datetime]
    duration: Optional[timedelta]
    node_ids: List[str] = field(default_factory=list)


@dataclass
class TimelineEvent:
    """Evento en el timeline."""
    id: str
    name: str
    start: datetime
    end: datetime
    category: str
    color: str


class TimelineView:
    """
    Genera visualización de timeline para restricciones temporales.
    
    Usage:
        view = TimelineView()
        svg = view.render_svg(constraints)
        html = view.render_html(constraints)
    """
    
    def __init__(
        self,
        width: int = 1000,
        height: int = 400,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ):
        self.width = width
        self.height = height
        self.start_date = start_date or datetime.now()
        self.end_date = end_date or (self.start_date + timedelta(days=365))
    
    def render_svg(
        self,
        constraints: List[TemporalConstraint],
        events: List[TimelineEvent] = None
    ) -> str:
        """Genera SVG del timeline."""
        svg_lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}" width="{self.width}">',
            '<style>',
            '.timeline-bg { fill: #1F2937; }',
            '.timeline-line { stroke: #374151; stroke-width: 2; }',
            '.timeline-label { font-family: system-ui; font-size: 11px; fill: #9CA3AF; }',
            '.event-label { font-family: system-ui; font-size: 12px; fill: white; }',
            '.constraint-label { font-family: system-ui; font-size: 10px; fill: #D1D5DB; }',
            '.restricted { fill: #EF4444; opacity: 0.2; }',
            '.active { fill: #10B981; opacity: 0.3; }',
            '.title { font-family: system-ui; font-size: 16px; fill: #F9FAFB; font-weight: bold; }',
            '.subtitle { font-family: system-ui; font-size: 12px; fill: #9CA3AF; }',
            '</style>',
            '<defs>',
            '  <pattern id="grid" width="50" height="20" patternUnits="userSpaceOnUse">',
            '    <line x1="0" y1="0" x2="50" y2="0" stroke="#374151" stroke-width="0.5" stroke-dasharray="2,2"/>',
            '  </pattern>',
            '</defs>',
            f'<rect width="100%" height="100%" class="timeline-bg" rx="8"/>',
            f'<text x="20" y="30" class="title">⏰ Cosmos Temporal Constraints</text>',
            f'<text x="20" y="50" class="subtitle">{self.start_date.strftime("%Y-%m-%d")} to {self.end_date.strftime("%Y-%m-%d")}</text>',
        ]
        
        # Línea base del timeline
        base_y = 100
        svg_lines.append(f'<line x1="50" y1="{base_y}" x2="{self.width-20}" y2="{base_y}" class="timeline-line"/>')
        
        # Escala temporal
        days_total = (self.end_date - self.start_date).days
        px_per_day = (self.width - 70) / max(days_total, 1)
        
        # Dibujar marcadores de mes
        current = self.start_date
        while current <= self.end_date:
            x = 50 + (current - self.start_date).days * px_per_day
            svg_lines.append(f'<line x1="{x}" y1="{base_y-5}" x2="{x}" y2="{base_y+5}" stroke="#6B7280" stroke-width="1"/>')
            svg_lines.append(f'<text x="{x}" y="{base_y+20}" class="timeline-label" text-anchor="middle">{current.strftime("%b")}</text>')
            current += timedelta(days=30)
        
        # Restricciones
        y_offset = base_y + 40
        for i, constraint in enumerate(constraints):
            y = y_offset + i * 50
            
            # Barra de restricción
            if constraint.restricted_until:
                x_start = 50
                x_end = 50 + (constraint.restricted_until - self.start_date).days * px_per_day
                x_end = min(x_end, self.width - 20)
                
                svg_lines.append(
                    f'<rect x="{x_start}" y="{y}" width="{x_end - x_start}" height="20" rx="4" class="restricted"/>'
                )
                svg_lines.append(
                    f'<text x="{x_start + 5}" y="{y + 14}" class="constraint-label">🔒 {constraint.name}</text>'
                )
            
            # Período activo
            if constraint.start and constraint.end:
                x_start = 50 + (constraint.start - self.start_date).days * px_per_day
                x_end = 50 + (constraint.end - self.start_date).days * px_per_day
                x_end = min(x_end, self.width - 20)
                
                svg_lines.append(
                    f'<rect x="{x_start}" y="{y}" width="{max(x_end - x_start, 20)}" height="20" rx="4" class="active"/>'
                )
                svg_lines.append(
                    f'<text x="{x_start + 5}" y="{y + 14}" class="constraint-label">✓ {constraint.name}</text>'
                )
        
        svg_lines.append('</svg>')
        return '\n'.join(svg_lines)
    
    def render_html(
        self,
        constraints: List[TemporalConstraint],
        events: List[TimelineEvent] = None
    ) -> str:
        """Genera HTML interactivo del timeline."""
        svg = self.render_svg(constraints, events)
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cosmos Temporal Constraints</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            background: #0F172A;
            color: #F9FAFB;
            padding: 2rem;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }}
        .subtitle {{
            color: #9CA3AF;
            margin-bottom: 1.5rem;
        }}
        .card {{
            background: #1E293B;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }}
        .constraints-list {{
            margin-top: 1rem;
        }}
        .constraint-item {{
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.75rem;
            background: #334155;
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }}
        .constraint-icon {{
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .restricted-icon {{ background: #EF4444; }}
        .active-icon {{ background: #10B981; }}
        .constraint-info {{
            flex: 1;
        }}
        .constraint-name {{
            font-weight: 600;
        }}
        .constraint-dates {{
            font-size: 0.875rem;
            color: #9CA3AF;
        }}
        .graph-container {{
            background: #1F2937;
            border-radius: 12px;
            overflow: hidden;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⏰ Temporal Constraints</h1>
        <p class="subtitle">{len(constraints)} constraints defined</p>
        
        <div class="card">
            <h2>Timeline</h2>
            <div class="graph-container">
                {svg}
            </div>
        </div>
        
        <div class="card">
            <h2>Constraints</h2>
            <div class="constraints-list">
                {''.join(self._constraint_item(c) for c in constraints)}
            </div>
        </div>
    </div>
</body>
</html>'''
    
    def _constraint_item(self, constraint: TemporalConstraint) -> str:
        icon_class = "restricted-icon" if constraint.restricted_until else "active-icon"
        icon = "🔒" if constraint.restricted_until else "✓"
        
        dates = ""
        if constraint.start and constraint.end:
            dates = f"{constraint.start.strftime('%Y-%m-%d')} → {constraint.end.strftime('%Y-%m-%d')}"
        elif constraint.restricted_until:
            dates = f"Restricted until {constraint.restricted_until.strftime('%Y-%m-%d')}"
        
        return f'''
        <div class="constraint-item">
            <div class="constraint-icon {icon_class}">{icon}</div>
            <div class="constraint-info">
                <div class="constraint-name">{constraint.name}</div>
                <div class="constraint-dates">{dates}</div>
            </div>
        </div>'''
    
    def save(
        self,
        constraints: List[TemporalConstraint],
        path: str,
        format: str = "html"
    ) -> str:
        """Guarda el timeline en archivo."""
        from pathlib import Path
        
        path = Path(path)
        
        if format == "svg":
            content = self.render_svg(constraints)
            path = path.with_suffix(".svg")
        else:
            content = self.render_html(constraints)
            path = path.with_suffix(".html")
        
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        
        return str(path)


# ============================================================
# Demo
# ============================================================

def demo():
    """Demo del timeline view."""
    print("=" * 60)
    print("COSMOS TIMELINE VIEW DEMO")
    print("=" * 60)
    
    now = datetime.now()
    
    constraints = [
        TemporalConstraint(
            id="c1",
            name="Primary License",
            start=now,
            end=now + timedelta(days=365),
            restricted_until=None
        ),
        TemporalConstraint(
            id="c2",
            name="Beta Feature",
            start=now + timedelta(days=30),
            end=now + timedelta(days=180),
            restricted_until=now + timedelta(days=30)
        ),
        TemporalConstraint(
            id="c3",
            name="Trial Period",
            start=now,
            end=now + timedelta(days=30),
            restricted_until=None
        ),
    ]
    
    view = TimelineView()
    html_path = view.save(constraints, "cosmos_timeline_demo", format="html")
    print(f"\nTimeline saved to: {html_path}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo()
