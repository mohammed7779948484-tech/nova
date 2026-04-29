"""LangGraph Studio entry point.

This file is referenced by langgraph.json so that LangGraph Studio
(and `langgraph dev`) can auto-discover and load the graph.

NOTE: No checkpointer here — Studio manages its own persistence.
      For CLI usage, see main.py which adds InMemorySaver.
"""

from src.graphs.sales_graph import build_sales_graph

# Studio wants an uncompiled or compiled-without-checkpointer graph
graph = build_sales_graph().compile()
