from typing import List, Dict, Any, TYPE_CHECKING, Optional

from sqlalchemy.orm import Mapped, Session

from .relationship_base import Relationship as BaseRelationship
from .relationship_field_mapping import RelationshipFieldMapping
from .relationship_rdf_mixin import RelationshipRDFMixin
from ..mixins.temporal.temporal_relationship import TemporalRelationship

if TYPE_CHECKING:
    from .. import Subgraph, ObjectType, AggregateExpression

logger = __import__('logging').getLogger(__name__)


class Relationship(RelationshipRDFMixin, BaseRelationship):
    """Concrete implementation of Relationship with field mappings and aggregate support."""
    __tablename__ = "relationship"

    # Relationships
    field_mappings: Mapped[List[RelationshipFieldMapping]] = TemporalRelationship(
        "RelationshipFieldMapping",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Relationship.name)==RelationshipFieldMapping.relationship_name, 
            foreign(Relationship.subgraph_name)==RelationshipFieldMapping.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    # Subgraph relationship
    subgraph: Mapped["Subgraph"] = TemporalRelationship(
        "Subgraph",
        uselist=False,
        viewonly=True,
        primaryjoin="and_(foreign(Relationship.subgraph_name)==Subgraph.name)"
    )

    # Type relationships
    source_type: Mapped["ObjectType"] = TemporalRelationship(
        "ObjectType",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(foreign(Relationship.source_type_name)==ObjectType.name, 
                    foreign(Relationship.subgraph_name)==ObjectType.subgraph_name)"""
    )

    target_type: Mapped["ObjectType"] = TemporalRelationship(
        "ObjectType",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(foreign(Relationship.target_type_name)==ObjectType.name, 
                    foreign(Relationship.target_subgraph_name)==ObjectType.subgraph_name)"""
    )

    aggregate_expression_relationship: Mapped[Optional["AggregateExpression"]] = TemporalRelationship(
        "AggregateExpression",
        uselist=False,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Relationship.aggregate_expression)==AggregateExpression.name, 
            foreign(Relationship.target_subgraph_name)==AggregateExpression.subgraph_name
        )"""
    )

    def to_json(self) -> Dict[str, Any]:
        base_dict = {
            "kind": "Relationship",
            "version": "v1",
            "definition": {
                "name": self.name,
                "sourceType": self.source_type_name,
                "description": self.description,
                "deprecated": self.deprecated if self.deprecated else None,
                "graphql": {"aggregateFieldName": self.graphql_field_name} if self.graphql_field_name else None,
                "mapping": [
                    {
                        "source": {"fieldPath": [{"fieldName": fm.source_field}]},
                        "target": {"modelField": [{"fieldName": fm.target_field}]}
                    }
                    for fm in self.field_mappings
                ]
            }
        }

        # Handle target information
        target_info = {
            "model": {
                "name": self.target_type_name,
                "relationshipType": self.relationship_type,
                "subgraph": self.target_subgraph_name if self.target_subgraph_name != self.subgraph_name else None
            }
        }

        if self.is_aggregate:
            # Use correct key 'aggregateExpression' and include description
            aggregate_info = {
                "aggregateExpression": self.aggregate_expression,
                "description": None  # Since we don't store description in the Relationship class
            }
            target_info["model"]["aggregate"] = aggregate_info

        base_dict["definition"]["target"] = target_info

        return base_dict

    @classmethod
    def from_json(cls, data: Dict[str, Any], subgraph: "Subgraph", session: "Session") -> "Relationship":
        from .target_model import TargetModel
        from .relationship_aggregate import RelationshipAggregate

        definition = data.get("definition", data)

        # Extract target info
        target_data = definition.get("target", {})
        model_data = target_data.get("model", {})
        target_subgraph = model_data.get("subgraph") or subgraph.name

        # Handle graphql data
        graphql_data = definition.get("graphql")
        graphql_field_name = graphql_data.get("aggregateFieldName") if graphql_data is not None else None

        # Get aggregate info
        aggregate_data = model_data.get("aggregate", {})

        # Create and add the main relationship first
        relationship = cls(
            name=definition["name"],
            source_type_name=definition["sourceType"],
            target_type_name=model_data["name"],
            target_subgraph_name=target_subgraph,
            description=definition.get("description"),
            deprecated=definition.get("deprecated", False),
            relationship_type=model_data.get("relationshipType", "Object"),
            subgraph_name=subgraph.name,
            graphql_field_name=graphql_field_name,
            is_aggregate=bool(aggregate_data),
            aggregate_expression=aggregate_data.get("aggregateExpression")
        )
        session.add(relationship)
        session.flush()

        # Create target model in its own transaction
        target_model = TargetModel.from_dict(
            data=target_data,
            relationship_name=relationship.name,
            subgraph_name=subgraph.name,
            source_type_name=relationship.source_type_name
        )
        session.add(target_model)
        session.flush()

        # Create field mappings in batches
        mappings = []
        for mapping in definition.get("mapping", []):
            field_mapping = RelationshipFieldMapping.from_mapping_data(
                mapping_data=mapping,
                relationship_name=relationship.name,
                subgraph=subgraph,
                source_type_name=relationship.source_type_name,
                session=session
            )
            mappings.append(field_mapping)
            session.add(field_mapping)

            # Flush every 50 mappings to prevent transaction buildup
            if len(mappings) % 50 == 0:
                session.flush()
                session.expire_all()  # Release memory/connections

        # Final flush for any remaining mappings
        if mappings:
            session.flush()

        # Create relationship aggregate if needed
        if relationship.is_aggregate:
            aggregate = RelationshipAggregate(
                relationship_name=relationship.name,
                subgraph_name=subgraph.name,
                source_type_name=relationship.source_type_name,
                aggregate_expression=aggregate_data.get("aggregateExpression"),
                description=aggregate_data.get("description")
            )
            session.add(aggregate)
            session.flush()

        # Store field mappings on the relationship instance
        relationship.field_mappings = mappings

        # Final validation
        relationship.validate()

        return relationship

    def validate(self) -> None:
        """Validate relationship constraints"""
        if not self.field_mappings:
            raise ValueError("Relationship must have at least one field mapping")

        if self.is_aggregate and not self.aggregate_expression:
            raise ValueError("Aggregate relationships must specify an aggregate expression")

        if not self.source_type_name:
            raise ValueError("Relationship must specify a source type")

        if not self.target_type_name:
            raise ValueError("Relationship must specify a target type")
