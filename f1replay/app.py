"""Application entry — window setup and view routing."""


def run(event=None):
    """Open the window. With an event, go straight into that race; without
    one, open the session-select screen."""
    import arcade

    from f1replay.ui.text_cache import install as install_text_cache
    from f1replay.ui.window import RaceWindow

    # Replace arcade.draw_text with a cached Text renderer (the stock one
    # rebuilds a GL texture per call and warns about it at 60 fps).
    install_text_cache()
    RaceWindow(event)
    arcade.run()
    return 0
