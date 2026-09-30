# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from ipyelk.elements import Label
from ipyelk.pipes.text_sizer import size_nested_label

LABEL_LABEL = "org.eclipse.elk.spacing.labelLabel"


def test_nested_label_width_includes_spacing_two_levels():
    """``labelLabel`` spacing is added to every sized sublabel, not only to
    sublabels without a width (``a or b + c`` parsed as ``a or (b + c)``).
    """
    inner = Label(text="inner", width=10, height=5, layoutOptions={LABEL_LABEL: 4})
    mid = Label(
        text="mid",
        width=20,
        height=7,
        labels=[inner],
        layoutOptions={LABEL_LABEL: 8},
    )
    outer = Label(text="outer", width=50, height=6, labels=[mid])

    size_nested_label(outer)

    assert mid.width == 34  # 20 + (10 + 4)
    assert outer.width == 92  # 50 + (34 + 8)
    assert mid.height == 7
    assert outer.height == 7
    assert inner.width == 10
    assert inner.height == 5
