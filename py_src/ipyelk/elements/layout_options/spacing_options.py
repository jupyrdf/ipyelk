# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import List

import ipywidgets as W
import traitlets as T

from .selection_widgets import LayoutOptionWidget, SpacingOptionWidget


class SeparateConnectedComponents(LayoutOptionWidget):
    identifier = "org.eclipse.elk.separateConnectedComponents"
    metadata_provider = "core.options.CoreOptions"
    active = T.Bool(default_value=False)

    applies_to = ["parents"]

    def _ui(self) -> List[W.Widget]:
        cb = W.Checkbox(description="Separeate Connected Components")

        T.link((self, "active"), (cb, "value"))
        return [cb]

    @T.observe("active")
    def _update_value(self, change=None):
        self.value = "true" if self.active else "false"


class ComponentsSpacing(SpacingOptionWidget):
    """Spacing to be preserved between pairs of connected components. This
    option is only relevant if ‘separateConnectedComponents’ is activated.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-spacing-componentComponent.html
    """

    identifier = "org.eclipse.elk.spacing.componentComponent"
    metadata_provider = "core.options.CoreOptions"
    spacing = T.Float(default_value=20, min=0)
    _slider_description = "Component Spacing"

    dependencies = ("org.eclipse.elk.separateConnectedComponents", "true")
    applies_to = ["parents"]
    group = "spacing"


class CommentNodeSpacing(SpacingOptionWidget):
    """Spacing to be preserved between a node and its connected comment boxes.
    The space left between a node and the comments of another node is controlled
    by the node-node spacing.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-spacing-commentNode.html
    """

    identifier = "org.eclipse.elk.spacing.commentNode"
    metadata_provider = "core.options.CoreOptions"

    _slider_description = "Comment Node Spacing"

    applies_to = ["parents"]
    group = "spacing"


class CommentCommentSpacing(SpacingOptionWidget):
    """Spacing to be preserved between a comment box and other comment boxes
    connected to the same node. The space left between comment boxes of
    different nodes is controlled by the node-node spacing.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-spacing-commentComment.html
    """

    identifier = "org.eclipse.elk.spacing.commentComment"
    metadata_provider = "core.options.CoreOptions"

    applies_to = ["parents"]
    group = "spacing"


class NodeSpacing(SpacingOptionWidget):
    """The minimal distance to be preserved between each two nodes.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-spacing-nodeNode.html
    """

    identifier = "org.eclipse.elk.spacing.nodeNode"
    metadata_provider = "core.options.CoreOptions"
    applies_to = ["parents"]
    group = "spacing"

    spacing = T.Float(default_value=20, min=0)
    _slider_description = "Node Spacing"


class LabelNodeSpacing(SpacingOptionWidget):
    """Spacing to be preserved between labels and the border of node they are
    associated with. Note that the placement of a label is influenced by the
    ‘nodelabels.placement’ option.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-spacing-labelNode.html
    """

    identifier = "org.eclipse.elk.spacing.labelNode"
    metadata_provider = "core.options.CoreOptions"
    applies_to = ["parents"]
    group = "spacing"

    spacing = T.Float(default_value=5, min=0)
    _slider_description = "Label Node Spacing"


class LabelSpacing(SpacingOptionWidget):
    """Determines the amount of space to be left between two labels of the same
    graph element.

    https://www.eclipse.org/elk/reference/options/org-eclipse-elk-spacing-labelLabel.html
    """

    identifier = "org.eclipse.elk.spacing.labelLabel"
    metadata_provider = "core.options.CoreOptions"
    applies_to = ["parents"]
    group = "spacing"

    spacing = T.Float(default_value=0, min=0)
    _slider_description = "Label Spacing"
