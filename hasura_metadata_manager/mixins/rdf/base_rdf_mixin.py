import datetime
from typing import Optional, Any, TYPE_CHECKING

from rdflib import Literal, XSD, URIRef

if TYPE_CHECKING:
    from ... import Supergraph
from . import NS_HASURA
from .rdf_cache_manager import RDFCacheManager

logger = __import__("logging").getLogger(__name__)


class BaseRDFMixin:
    """Base mixin class providing common RDF functionality and cache management."""

    _cache_manager: Optional[RDFCacheManager] = None

    @classmethod
    def configure_cache(
            cls,
            cache_dir: str = './.rdf_cache',
            model_maxsize: int = 128,
            instance_maxsize: int = 32,
            ttl: int = 3600,
            supergraph: Optional['Supergraph'] = None
    ) -> None:
        """Configure the RDF cache manager"""
        cls._cache_manager = RDFCacheManager(
            cache_dir=cache_dir,
            model_maxsize=model_maxsize,
            instance_maxsize=instance_maxsize,
            ttl=ttl,
            supergraph=supergraph
        )
        # logger.debug("Configured RDF cache manager")

    @classmethod
    def clear_caches(cls) -> None:
        """Clear all cached hasura_metadata_manager"""
        if cls._cache_manager:
            cls._cache_manager.clear_all()

    @classmethod
    def _ensure_cache_configured(cls):
        """Ensure cache is configured, called before any cache-dependent method"""
        if not cls._cache_manager:
            cls.configure_cache()

    @staticmethod
    def _format_literal(value: Any) -> Literal:
        """Convert Python values into RDF Literals with appropriate datatypes"""
        logger.debug(f"Formatting literal value of type {type(value).__name__}")
        if isinstance(value, bool):
            return Literal(value, datatype=XSD.boolean)
        elif isinstance(value, int):
            return Literal(value, datatype=XSD.integer)
        elif isinstance(value, float):
            return Literal(value, datatype=XSD.float)
        elif isinstance(value, str):
            return Literal(value, datatype=XSD.string)
        elif isinstance(value, datetime.datetime):
            return Literal(value.isoformat(), datatype=XSD.dateTime)
        elif isinstance(value, datetime.date):
            return Literal(value.isoformat(), datatype=XSD.date)
        else:
            logger.debug(f"Unhandled value type, converting to string: {type(value).__name__}")
            return Literal(str(value), datatype=XSD.string)

    @classmethod
    def get_rdf_type(cls) -> URIRef:
        """Get the RDF type for this class"""
        rdf_type = URIRef(NS_HASURA[cls.__name__])
        logger.debug(f"Getting RDF type for class {cls.__name__}: {rdf_type}")
        return rdf_type
