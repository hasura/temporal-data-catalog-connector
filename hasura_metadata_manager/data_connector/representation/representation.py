from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session, Mapped

from ..representation.enum_value import EnumValue
from ..representation.representation_base import Representation as BaseRepresentation
from ...mixins.temporal.temporal_relationship import TemporalRelationship


class Representation(BaseRepresentation):
    """Base class for scalar type representations"""
    __tablename__ = "representation"

    # For enum types, relationship to possible values
    enum_values: Mapped[List["EnumValue"]] = TemporalRelationship(
        "EnumValue",
        uselist=True,
        primaryjoin="""and_(
            foreign(Representation.subgraph_name) == EnumValue.subgraph_name, 
            foreign(Representation.connector_name) == EnumValue.connector_name,  
            foreign(Representation.name) == EnumValue.rep_name
        )""",
        info={'skip_constraint': True}
    )

    def to_json(self) -> Dict[str, Any]:
        """Convert representation to JSON format"""
        if self.type == "enum":
            return {
                "type": "enum",
                "one_of": [value.to_json() for value in self.enum_values]
            }
        else:
            return {
                "type": self.type
            }

    @classmethod
    def from_json(cls, json_data: Dict[str, Any], subgraph_name: Optional[str],
                  connector_name: str, name: str, session: Session) -> "Representation":
        """
        Create a Representation instance from JSON data

        Args:
            json_data: Dictionary containing representation data
            subgraph_name: Optional subgraph name
            connector_name: Connector id
            name: Type name
            session: SQLAlchemy session
        """
        rep_type = json_data.get("type")
        if not rep_type:
            raise ValueError("Representation must have a type")

        if rep_type == "enum":
            one_of = json_data.get("one_of", [])
            if not isinstance(one_of, list):
                raise ValueError("Enum representation must have one_of list")

            rep = cls(
                subgraph_name=subgraph_name,
                connector_name=connector_name,
                name=name,
                type=rep_type
            )
            for value in one_of:
                ev = EnumValue.from_json(value, subgraph_name, connector_name, name)
                session.add(ev)

                session.flush()
        else:
            rep = cls(
                subgraph_name=subgraph_name,
                connector_name=connector_name,
                name=name,
                type=rep_type
            )

        return rep
