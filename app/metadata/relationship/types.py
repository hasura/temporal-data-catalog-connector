from typing import TypedDict, List, Optional, Literal


class FieldPath(TypedDict):
    """Single field path entry containing field name and optional subgraph"""
    fieldName: str
    subgraph: Optional[str]


class SourceField(TypedDict):
    """Source field specification with field path"""
    fieldPath: List[FieldPath]


class ModelField(TypedDict):
    """Target model field specification"""
    fieldName: str
    subgraph: Optional[str]


class TargetField(TypedDict):
    """Target field specification with model field"""
    modelField: List[ModelField]


class MappingEntry(TypedDict):
    """Single mapping between source and target fields"""
    source: SourceField
    target: TargetField


class AggregateDict(TypedDict):
    """Aggregate expression specification"""
    expression: str
    description: Optional[str]


class GraphQLConfig(TypedDict, total=False):
    """GraphQL-specific configuration"""
    aggregateFieldName: str


class ModelConfig(TypedDict, total=False):
    """Model configuration including optional aggregate"""
    name: str
    relationshipType: str
    subgraph: Optional[str]
    aggregate: Optional[AggregateDict]


class TargetDict(TypedDict):
    """Target specification - either model or command"""
    model: Optional[ModelConfig]
    command: Optional[ModelConfig]


class RelationshipDefinition(TypedDict, total=False):
    """Complete relationship definition"""
    name: str
    sourceType: str
    description: Optional[str]
    deprecated: Optional[bool]
    mapping: List[MappingEntry]
    target: TargetDict
    graphql: Optional[GraphQLConfig]


class RelationshipDict(TypedDict):
    """Top-level relationship structure"""
    kind: Literal["Relationship"]
    version: Literal["v1"]
    definition: RelationshipDefinition
