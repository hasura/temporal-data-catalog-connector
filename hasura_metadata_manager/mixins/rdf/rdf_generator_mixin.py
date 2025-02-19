import logging
from typing import Optional, Union, overload, TYPE_CHECKING

from rdflib import Graph
from sqlalchemy.orm import Session

from .instance_rdf_mixin import InstanceRDFMixin
from .model_rdf_mixin import ModelRDFMixin
from .rdf_translator import RDFTranslator, T

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class RDFGeneratorMixin(ModelRDFMixin, InstanceRDFMixin):
    """
    Combined mixin class providing both model and instance RDF capabilities.
    Maintains backward compatibility with existing code.
    """

    @classmethod
    @overload
    def generate_rdf_graph(cls, session: Session, metadata_type: str = "instance") -> Graph:
        ...

    @classmethod
    @overload
    def generate_rdf_graph(cls, session: Session, metadata_type: str, translator: RDFTranslator[T]) -> T:
        ...

    @classmethod
    def generate_rdf_graph(
            cls,
            session: Session,
            metadata_type: str = "instance",
            translator: Optional[RDFTranslator[T]] = None
    ) -> Union[Graph, T]:
        """Generate an RDF graph for either model or instance hasura_metadata_manager with caching"""
        if metadata_type == "model":
            return cls.translate_to_model_metadata(session, translator)
        else:
            return cls.translate_to_instance_metadata(session, translator)
