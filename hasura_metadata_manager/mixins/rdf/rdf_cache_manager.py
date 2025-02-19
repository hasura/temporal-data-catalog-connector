import datetime
import hashlib
import logging
import os
from typing import Optional, Any, TYPE_CHECKING

import diskcache as dc
from rdflib import Graph
from sqlalchemy import inspect
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from ... import Supergraph

logger = logging.getLogger(__name__)


class RDFCacheManager:
    """
    Manages caching for RDF hasura_metadata_manager graphs, supporting both model-level and instance-level caching.
    """

    def __init__(
            self,
            cache_dir: str = './.rdf_cache',
            model_maxsize: int = 128,  # MB for model hasura_metadata_manager
            instance_maxsize: int = 32,  # MB for instance hasura_metadata_manager
            ttl: int = 3600,  # Cache TTL in seconds
            supergraph: Optional['Supergraph'] = None
    ):
        """
        Initialize the RDF cache manager.

        Args:
            cache_dir: Directory to store cache files
            model_maxsize: Maximum size in MB for model hasura_metadata_manager cache
            instance_maxsize: Maximum size in MB for instance hasura_metadata_manager cache
            ttl: Cache time-to-live in seconds
            supergraph: Optional supergraph instance for freshness checks
        """
        self.cache_dir = cache_dir
        self.ttl = ttl
        self.supergraph = supergraph
        self.last_refresh = datetime.datetime.now(datetime.timezone.utc)

        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)

        # Initialize caches
        self.model_cache = dc.Cache(
            os.path.join(cache_dir, 'model_metadata_cache'),
            size_limit=model_maxsize * 1024 * 1024,
            expires=ttl
        )

        self.instance_cache = dc.Cache(
            os.path.join(cache_dir, 'instance_metadata_cache'),
            size_limit=instance_maxsize * 1024 * 1024,
            expires=ttl
        )

        # logger.debug(f"Initialized RDF cache manager in {cache_dir}")

    def clear_all(self) -> None:
        """Clear all cached hasura_metadata_manager"""
        self.model_cache.clear()
        self.instance_cache.clear()
        self.last_refresh = datetime.datetime.now(datetime.timezone.utc)
        logger.debug("Cleared all RDF caches")

    def is_fresh(self) -> bool:
        """
        Check if cache needs refresh based on Supergraph updates.
        Returns True if cache is fresh, False if cache needs refresh.
        """
        if self.supergraph is None:
            return True

        try:
            supergraph_updated = self.supergraph.t_updated_at
            if supergraph_updated > self.last_refresh:
                logger.info(
                    f"Cache is stale. Supergraph updated at {supergraph_updated}, "
                    f"last cache refresh at {self.last_refresh}"
                )
                return False
            return True
        except Exception as e:
            logger.warning(f"Error checking cache freshness: {e}")
            return True

    def get_model_metadata(
            self,
            cls: type,
            session: Session,
            generator_func: callable
    ) -> Graph:
        """
        Get model hasura_metadata_manager from cache or generate if not present.

        Args:
            cls: The model class
            session: The session
            generator_func: Function to generate model hasura_metadata_manager if not cached
        """
        cache_key = self._generate_model_key(cls)

        try:
            return self.model_cache[cache_key]
        except KeyError:
            graph = generator_func(session=session)
            self.model_cache[cache_key] = graph
            return graph

    def get_instance_metadata(
            self,
            instance: Any,
            session: Session,
            generator_func: callable
    ) -> Graph:
        """
        Get instance hasura_metadata_manager from cache or generate if not present.

        Args:
            instance: Model instance
            session: Session
            generator_func: Function to generate instance hasura_metadata_manager if not cached
        """
        cache_key = self._generate_instance_key(instance)

        try:
            return self.instance_cache[cache_key]
        except KeyError:
            graph = generator_func(session=session)
            self.instance_cache[cache_key] = graph
            return graph

    def get_bulk_instance_metadata(
            self,
            cls: type,
            session: Session,
            generator_func: callable
    ) -> Graph:
        """
        Get bulk instance hasura_metadata_manager from cache or generate if not present.

        Args:
            cls: The model class
            session: SQLAlchemy session
            generator_func: Function to generate bulk instance hasura_metadata_manager if not cached
        """
        cache_key = self._generate_bulk_instance_key(cls, session)

        try:
            return self.instance_cache[cache_key]
        except KeyError:
            graph = generator_func(session)
            self.instance_cache[cache_key] = graph
            return graph

    @staticmethod
    def _generate_model_key(cls: type) -> str:
        """Generate a cache key for model-level hasura_metadata_manager"""
        mro_names = [c.__name__ for c in cls.__mro__ if hasattr(c, '__table__')]
        key = hashlib.sha256(f"{':'.join(mro_names)}:model_metadata".encode()).hexdigest()
        logger.debug(f"Generated model hasura_metadata_manager cache key: {key}")
        return key

    @staticmethod
    def _generate_instance_key(instance: Any) -> str:
        """Generate a cache key for a specific instance"""
        pk_values = "_".join(
            str(getattr(instance, key.name))
            for key in inspect(instance.__class__).primary_key
        )

        modified_time = getattr(instance, 'updated_at', None) or getattr(instance, 'modified_at', None)
        if modified_time:
            pk_values += f"_{modified_time.isoformat()}"

        key = hashlib.sha256(
            f"{instance.__class__.__name__}:instance:{pk_values}".encode()
        ).hexdigest()
        logger.debug(f"Generated instance key: {key}")
        return key

    @staticmethod
    def _generate_bulk_instance_key(cls: type, session: Session) -> str:
        """Generate a cache key for bulk instance hasura_metadata_manager"""
        latest_modified = None
        for instance in session.query(cls).all():
            modified_time = getattr(instance, 'updated_at', None) or getattr(instance, 'modified_at', None)
            if modified_time and (not latest_modified or modified_time > latest_modified):
                latest_modified = modified_time

        key = hashlib.sha256(
            f"{cls.__name__}:instance_metadata_{latest_modified.isoformat() if latest_modified else ''}".encode()
        ).hexdigest()
        # logger.debug(f"Generated bulk instance hasura_metadata_manager cache key: {key}")
        return key
