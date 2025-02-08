from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from rdflib import Graph

T = TypeVar('T')


class RDFTranslator(Generic[T], ABC):
    """Abstract base class for translating RDF graphs to other formats"""

    @abstractmethod
    def translate(self, graph: Graph) -> T:
        """Translate an RDF graph to target format"""
        raise NotImplementedError
