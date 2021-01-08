"""Widget to configure ElkNode layout properties
"""
# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import ipywidgets as W
import traitlets as T


class NodeLabelPlacement(W.HBox):
    horizontal = T.Enum(values=["left", "center", "right"], default_value="left")
    h_priority = T.Bool(allow_none=True)
    vertical = T.Enum(values=["top", "center", "bottom"], default_value="top")
    inside = T.Enum(values=["inside", "outside"], default_value="inside")
    value = T.Unicode(allow_none=True)

    def __init__(self, *args, **kwargs):
        """Simple widget to help format the ELK Node Label Placement.

        Hints for where node labels are to be placed; if empty, the node
        label’s position is not modified.
        """
        super().__init__(*args, **kwargs)

        self.horizontal_options = W.RadioButtons(
            description="Horizontal",
            options=(
                ("Left", "left"),
                ("Center", "center"),
                ("Right", "right"),
            ),
        )
        self.vertical_options = W.RadioButtons(
            description="Vertical",
            options=(
                ("Top", "top"),
                ("Center", "center"),
                ("Bottom", "bottom"),
            ),
        )
        self.inside_options = W.Checkbox(description="Inside")
        self.horizontal_priority_options = W.Checkbox(description="Horizontal Priority")

        T.link((self, "horizontal"), (self.horizontal_options, "value"))
        T.link((self, "vertical"), (self.vertical_options, "value"))
        T.link((self, "h_priority"), (self.horizontal_priority_options, "value"))

        def _handle_inside_change(change):
            self.inside = "inside" if self.inside_options.value is True else "outside"

        self.inside_options.observe(_handle_inside_change, "value")

        self.children = [
            self.horizontal_options,
            self.vertical_options,
            W.VBox([self.inside_options, self.horizontal_priority_options]),
        ]

        self._update_value()

    @T.observe("horizontal", "vertical", "inside", "h_priority")
    def _update_value(self, change=None):
        self.inside_options.value = self.inside == "inside"
        self.horizontal_priority_options.value = self.h_priority
        options = []
        if self.horizontal:
            options.append(f"H_{self.horizontal.upper()}")
        if self.vertical:
            options.append(f"V_{self.vertical.upper()}")
        if self.inside:
            options.append(self.inside.upper())
        if self.h_priority:
            options.append("H_PRIORITY")
        if options:
            self.value = f"[{' '.join(options)}]"
        else:
            self.value = None
