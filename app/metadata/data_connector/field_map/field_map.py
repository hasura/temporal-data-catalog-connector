from sqlalchemy.orm import Mapped

from ..field_map.field_map_base import FieldMap as BaseFieldMap
from ..schema.collection.field.collection_field_base import CollectionField
from ...mixins.temporal.temporal_relationship import TemporalRelationship
from ...object_type.field.object_field import ObjectField


class FieldMap(BaseFieldMap):
    """Implementation class for FieldMap that includes relationships and methods."""
    __tablename__ = "field_map"

    collection_field: Mapped["CollectionField"] = TemporalRelationship(
        "CollectionField",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(FieldMap.physical_field_name) == CollectionField.physical_field_name,
            foreign(FieldMap.subgraph_name) == CollectionField.subgraph_name,
            foreign(FieldMap.connector_name) == CollectionField.connector_name,
            foreign(FieldMap.collection_name) == CollectionField.collection_name
        )"""
    )
    object_field: Mapped["ObjectField"] = TemporalRelationship(
        "ObjectField",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(FieldMap.logical_field_name) == ObjectField.logical_field_name,
            foreign(FieldMap.subgraph_name) == ObjectField.subgraph_name,
            foreign(FieldMap.object_type_name) == ObjectField.object_type_name
        )"""
    )
