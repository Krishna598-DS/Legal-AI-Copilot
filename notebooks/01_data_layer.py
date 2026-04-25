"""
Run this to verify the data layer works end to end.
  python notebooks/01_data_layer.py
"""
import sys
sys.path.insert(0, ".")

from dotenv import load_dotenv
import os

load_dotenv()

from src.ingestion.loaders import load_directory, load_web_page
from src.ingestion.chunkers import compare_strategies, get_chunk_stats
from rich.console import Console
from rich.panel import Panel

console = Console()

console.print(Panel.fit("[bold]Legal RAG — Data Layer Test[/bold]", border_style="cyan"))

# 1. Load documents from data/raw/
console.print("\n[bold]Step 1: Loading documents[/bold]")
docs = load_directory("data/raw/")

if not docs:
    console.print("[yellow]No local docs found — fetching sample legal text from web[/yellow]")
    docs = load_web_page("https://gdpr-info.eu/art-5-gdpr/")

console.print(f"\nLoaded [green]{len(docs)}[/green] document pages/sections")
console.print(f"Sample metadata: {docs[0].metadata}")
console.print(f"Sample text (first 300 chars):\n{docs[0].page_content[:300]}")

# 2. Run chunking strategies
console.print("\n[bold]Step 2: Comparing chunking strategies[/bold]")
openai_key = os.getenv("OPENAI_API_KEY")

results = compare_strategies(
    docs,
    openai_api_key=openai_key,
    run_semantic=bool(openai_key),
)

# 3. Show stats per strategy
console.print("\n[bold]Step 3: Chunk statistics[/bold]")
for strategy, chunks in results.items():
    stats = get_chunk_stats(chunks)
    console.print(f"  {strategy}: {stats}")

# 4. Inspect a sample chunk
console.print("\n[bold]Step 4: Sample chunk (recursive)[/bold]")
sample = results["recursive"][5]
console.print(f"Content: {sample.page_content[:200]}...")
console.print(f"Metadata: {sample.metadata}")

console.print("\n[bold green]Data layer working correctly[/bold green]")
