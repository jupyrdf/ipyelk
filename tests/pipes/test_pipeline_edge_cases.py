# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import pytest

from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget, Pipe, Pipeline


class _Copy(Pipe):
    """A stage whose output is a new tree, as a ``VisibilityPipe`` projection is."""

    async def run(self):
        self.outlet.value = self.inlet.value.model_copy()


def test_empty_pipeline_check_does_not_raise():
    pipeline = Pipeline(pipes=[])
    assert pipeline.check() is True


def test_empty_pipeline_progress_is_complete():
    pipeline = Pipeline(pipes=[])
    assert pipeline.get_progress_value() == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_a_clean_stage_keeps_its_output_until_its_input_changes():
    """A clean stage keeps what it made from an unchanged input, and passes a new
    input through (#231).
    """
    first, second = _Copy(observes=("a",)), _Copy(observes=("b",))
    source = MarkElementWidget(value=Node(id="root"))
    pipeline = Pipeline(inlet=source)
    pipeline.pipes = [first, second]
    pipeline.inlet.record("a", "b")
    await pipeline.run()
    made = pipeline.outlet.value
    assert made is not first.outlet.value

    await pipeline.run()  # nothing pending
    assert pipeline.outlet.value is made

    pipeline.inlet.record("a")
    await pipeline.run()
    assert pipeline.outlet.value is first.outlet.value, "a new input passes through"
    pipeline.close()
    source.close()
