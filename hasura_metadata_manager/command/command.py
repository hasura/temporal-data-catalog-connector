from typing import List, Dict, Any, Type

from sqlalchemy.orm import Mapped, Session

from .command_argument import CommandArgument
from .command_base import Command as BaseCommand
from .command_source_mapping import CommandSourceMapping
from ..mixins.temporal.temporal_relationship import TemporalRelationship


class Command(BaseCommand):
    """Main Command class representing the command definition."""
    __tablename__ = "command"

    # Relationships
    arguments: Mapped[List["CommandArgument"]] = TemporalRelationship(
        "CommandArgument",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Command.name) == CommandArgument.command_name,
            foreign(Command.subgraph_name) == CommandArgument.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    source_mappings: Mapped[List["CommandSourceMapping"]] = TemporalRelationship(
        "CommandSourceMapping",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(Command.name) == CommandSourceMapping.command_name,
            foreign(Command.subgraph_name) == CommandSourceMapping.subgraph_name
        )""",
        info={'skip_constraint': True}
    )

    @classmethod
    def from_json(cls: Type["Command"], json_data: Dict[str, Any], subgraph_name: str,
                  session: Session) -> "Command":
        """Create a Command from JSON data."""
        if json_data.get("kind") != "Command":
            raise ValueError(f"Expected Command, got {json_data.get('kind')}")

        def_data = json_data.get("definition", {})
        graphql_data = def_data.get("graphql", {})
        source_data = def_data.get("source", {})

        command = cls(
            subgraph_name=subgraph_name,
            name=def_data.get("name"),
            version=json_data.get("version"),
            description=def_data.get("description"),
            output_type=def_data.get("outputType"),
            connector_name=source_data.get("dataConnectorName"),
            graphql_deprecated=graphql_data.get("deprecated"),
            graphql_root_field_kind=graphql_data.get("rootFieldKind"),
            graphql_root_field_name=graphql_data.get("rootFieldName")
        )
        session.add(command)
        session.flush()

        # Create arguments
        if "arguments" in def_data:
            for arg_data in def_data["arguments"]:
                CommandArgument.from_json(arg_data, command, session)

        # Create source mappings from argumentMapping
        arg_mapping = source_data.get("argumentMapping", {})
        for source_key, target_value in arg_mapping.items():
            CommandSourceMapping.from_json(source_key, target_value, command, session)

        return command

    def to_json(self) -> dict:
        """Convert Command to JSON representation."""
        source_mappings_dict = {}
        for mapping in self.source_mappings:
            source_mappings_dict[mapping.source_key] = mapping.target_value

        definition = {
            "name": self.name,
            "description": self.description,
            "arguments": [arg.to_json() for arg in self.arguments],
            "graphql": {
                "deprecated": self.graphql_deprecated,
                "rootFieldKind": self.graphql_root_field_kind,
                "rootFieldName": self.graphql_root_field_name
            },
            "outputType": self.output_type,
            "source": {
                "argumentMapping": source_mappings_dict,
                "dataConnectorName": self.connector_name,
                "dataConnectorCommand": {
                    "function": None,  # Add if needed
                    "procedure": None  # Add if needed
                }
            }
        }

        return {
            "definition": definition,
            "kind": "Command",
            "version": self.version
        }
