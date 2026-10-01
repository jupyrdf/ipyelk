# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Toolbar`` orders tool UIs by priority and omits tools without a UI."""

import ipywidgets as W

from ipyelk.tools import Selection, Toolbar, ToolButton


def test_toolbar_orders_uis_by_priority_and_skips_state_only_tools():
    late = ToolButton(description="late", priority=20)
    early = ToolButton(description="early", priority=1)
    toolbar = Toolbar(tools=[late, Selection(), early])
    assert toolbar.order() == {1: [early.ui], 20: [late.ui]}
    assert toolbar.tool_order() == [early.ui, late.ui]
    assert all(isinstance(ui, W.DOMWidget) for ui in toolbar.tool_order())
    assert list(toolbar.children)[1:] == [
        early.ui,
        late.ui,
        toolbar.close_btn,
    ]  # [0]: css
