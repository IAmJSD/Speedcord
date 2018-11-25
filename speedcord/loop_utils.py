def get_best_loop():
    """Gets the best possible loop."""
    try:
        import uvloop
        return uvloop.new_event_loop()
    except ImportError:
        import asyncio
        return asyncio.get_event_loop()
