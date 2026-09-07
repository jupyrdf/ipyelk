# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import pytest

from ipyelk.pipes import Pipeline


def test_empty_pipeline_check_does_not_raise():
    pipeline = Pipeline(pipes=[])
    assert pipeline.check() is True


def test_empty_pipeline_progress_is_complete():
    pipeline = Pipeline(pipes=[])
    assert pipeline.get_progress_value() == pytest.approx(1.0)
