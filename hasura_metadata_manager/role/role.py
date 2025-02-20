from typing import List, Type, Dict, Any, Optional, TYPE_CHECKING

from sqlalchemy.orm import Mapped, Session

from .role_base import Role as BaseRole
from ..mixins.temporal.temporal_relationship import TemporalRelationship
from ..subgraph.subgraph_base import Subgraph
from ..supergraph.supergraph_base import Supergraph

if TYPE_CHECKING:
    from ..type_permission import TypePermission
    from .. import ModelPermission


class Role(BaseRole):
    __tablename__ = "role"

    supergraph: Mapped["Supergraph"] = TemporalRelationship(
        "Supergraph",
        uselist=False,
        viewonly=True,
        primaryjoin="and_(foreign(Role.supergraph_name)==Supergraph.name)"
    )
    type_permissions: Mapped[List["TypePermission"]] = TemporalRelationship(
        "TypePermission",
        uselist=True,
        viewonly=True,
        primaryjoin="and_(foreign(Role.name) == TypePermission.role_name)",
        info={'skip_constraint': True}
    )
    model_permissions: Mapped[List["ModelPermission"]] = TemporalRelationship(
        "ModelPermission",
        uselist=True,
        viewonly=True,
        primaryjoin="and_(foreign(Role.name) == ModelPermission.role_name)",
        info={'skip_constraint': True}
    )

    @classmethod
    def from_json(cls: Type["Role"], json_data: Dict[str, Any], subgraph: "Subgraph", supergraph: "Supergraph",
                  session: Session) -> Optional[
        "Role"]:
        """
        Create a Role from JSON data if it doesn't already exist.

        Args:
            json_data: The JSON data containing role information
            subgraph: The subgraph associated with this role
            supergraph: The supergraph associated with this role
            session: The SQLAlchemy session

        Returns:
            The created or existing Role object, or None if no role could be created
        """
        if not isinstance(json_data, dict):
            return None

        role_name = None
        if "permissions" in json_data["definition"]:
            for perm in json_data["definition"]["permissions"]:
                if "role" in perm:
                    role_name = perm["role"]
                    break

        if not role_name:
            return None

        supergraph_name = supergraph.name
        if not supergraph_name:
            raise ValueError("Supergraph name cannot be None")

        # Get the result and explicitly cast it to Optional[Role]
        existing_role: Optional[Role] = session.query(Role).filter_by(
            name=role_name,
            supergraph_name=supergraph_name
        ).first()

        if existing_role is not None:

            # Always add the existing role to the session to ensure it's tracked
            session.add(existing_role)
            session.flush()  # Added flush here

            from ..type_permission import TypePermission
            TypePermission.from_json(json_data, subgraph, session)
            return existing_role

        # Create new role
        new_role: Role = Role(
            name=role_name,
            supergraph_name=supergraph_name
        )
        session.add(new_role)
        session.flush()


        from ..type_permission import TypePermission
        TypePermission.from_json(json_data, subgraph, session)

        return new_role
