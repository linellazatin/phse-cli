"""Market recap — summary of market activity."""

from __future__ import annotations

from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..config import get_settings

console = Console()


def market_recap() -> None:
    """Print a market recap with top gainers, losers, and volume leaders."""
    from ..data.frames_pse import FramesPseClient

    frames = FramesPseClient(get_settings())
    summary = frames.market_summary()

    gainers = summary["gainers"]
    losers = summary["losers"]
    volume_leaders = summary["volume_leaders"]
    most_active = summary["most_active"]
    total_count = summary["advancers"] + summary["decliners"] + summary["unchanged"]
    
    # Print recap
    console.print()
    console.print(Panel(
        f"[bold]Market Recap — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}[/bold]\n"
        f"[dim]Based on {total_count} companies from frames.pse.com.ph | "
        f"Total Volume: {summary['total_volume']:,} | "
        f"Total Value: ₱{summary['total_value']:,.0f}[/dim]",
        title="[bold]PSE Market Recap[/bold]",
        border_style="blue",
    ))
    
    def _change_color(pct) -> str:
        if isinstance(pct, dict):
            pct = pct.get("percent_change", 0)
        return "green" if pct > 0 else "red" if pct < 0 else "yellow"

    # Top gainers
    table = Table(title="[bold]Top Gainers[/]", show_header=True, header_style="bold")
    table.add_column("Symbol", style="cyan")
    table.add_column("Price", justify="right")
    table.add_column("% Change", justify="right")
    for g in gainers:
        c = _change_color(g["percent_change"])
        table.add_row(
            g["symbol"],
            f"{g['price']:.2f}" if g["price"] else "—",
            f"[{c}]{g['percent_change']:+.2f}%[/]" if g["percent_change"] else "—",
        )
    console.print(table)

    # Top losers
    table = Table(title="[bold]Top Losers[/]", show_header=True, header_style="bold")
    table.add_column("Symbol", style="cyan")
    table.add_column("Price", justify="right")
    table.add_column("% Change", justify="right")
    for l in losers:
        c = _change_color(l["percent_change"])
        table.add_row(
            l["symbol"],
            f"{l['price']:.2f}" if l["price"] else "—",
            f"[{c}]{l['percent_change']:+.2f}%[/]" if l["percent_change"] else "—",
        )
    console.print(table)

    # Volume leaders
    table = Table(title="[bold]Volume Leaders[/]", show_header=True, header_style="bold")
    table.add_column("Symbol", style="cyan")
    table.add_column("Volume", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("% Change", justify="right")
    for v in volume_leaders:
        vol = int(v.get("Volume", 0) or 0)
        price = float(v.get("Price", 0) or 0)
        pct = float(v.get("PercentChange", 0) or 0)
        c = _change_color(pct)
        table.add_row(
            v.get("StockSymbol", ""),
            f"{vol:,}" if vol else "—",
            f"{price:.2f}" if price else "—",
            f"[{c}]{pct:+.2f}%[/]" if pct else "—",
        )
    console.print(table)

    # Most active by value
    table = Table(title="[bold]Most Active by Value[/]", show_header=True, header_style="bold")
    table.add_column("Symbol", style="cyan")
    table.add_column("Price", justify="right")
    table.add_column("Volume", justify="right")
    table.add_column("Value", justify="right")
    table.add_column("% Change", justify="right")
    for m in most_active:
        price = float(m.get("Price", 0) or 0)
        vol = int(m.get("Volume", 0) or 0)
        raw_val = m.get("Value", "0")
        val = float(str(raw_val).replace(",", "")) if raw_val else 0
        pct = float(m.get("PercentChange", 0) or 0)
        c = _change_color(pct)
        table.add_row(
            m.get("StockSymbol", ""),
            f"{price:.2f}" if price else "—",
            f"{vol:,}" if vol else "—",
            f"₱{val:,.0f}" if val else "—",
            f"[{c}]{pct:+.2f}%[/]" if pct else "—",
        )
    console.print(table)
    console.print()
