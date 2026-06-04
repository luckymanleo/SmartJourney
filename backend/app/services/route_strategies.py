"""
多路线生成策略 — 从 config.json 加载
"""

from app.config_loader import route_strategies as load_strategies

ROUTE_STRATEGIES = load_strategies()
