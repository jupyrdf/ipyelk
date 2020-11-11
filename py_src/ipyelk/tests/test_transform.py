# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import pytest

from ipyelk.nx.transformer import XELK


@pytest.mark.asyncio
async def test_transform():
    x = XELK(text_sizer=None)
    assert isinstance(x, XELK)
