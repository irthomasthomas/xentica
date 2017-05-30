from hecate.bridge.base import Bridge


class MoireBridge:

    key_actions = {
        "up": Bridge.scroll_up,
        "down": Bridge.scroll_down,
        "left": Bridge.scroll_left,
        "right": Bridge.scroll_right,
        "escape": Bridge.exit_app,
    }