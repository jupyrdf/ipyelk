# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
"""Could become an opinionated replacement for the models in elk_model

:return: [description]
:rtype: [type]
"""
# from dataclasses import dataclass, field
# from typing import ClassVar, List

# import networkx as nx

# from ..diagram import Symbol


# def add_to(self, g: nx.Graph) -> "Symbol":
#     if self.id is None:
#         self.id = str(uuid4())

#     g.add_node(self.id, **self.to_json())
#     return self


# @dataclass
# class Element:
#     shape: Symbol


# @dataclass
# class Node(Element):

#     _ports: Dict[Port] = field(default_factory=dict)

#     def __init__():

#         pass

#     def __setattr__(self, key, value):
#         if isinstance(value, Port):
#             self._ports[key] = value

#         else:
#             super().__setattr__(key, value)


# @dataclass
# class Port(Element):
#     pass
