from typing import List, Type, Dict, Any

from sqlalchemy.orm import Mapped, Session

from .filter.filter_condition import FilterCondition
from .model_argument_preset import ModelArgumentPreset
from .model_permission_base import ModelPermission as BaseModelPermission
from ..mixins.temporal.temporal_relationship import TemporalRelationship
from ..model.model_base import Model
from ..role import Role
from ..subgraph.subgraph_base import Subgraph

logger = __import__('logging').getLogger(__name__)


class ModelPermission(BaseModelPermission):
    __tablename__ = "model_permission"

    model: Mapped["Model"] = TemporalRelationship(
        "Model",
        uselist=False,
        viewonly=True,
        primaryjoin="and_(foreign(ModelPermission.model_name)==Model.name)"
    )
    role: Mapped["Role"] = TemporalRelationship(
        "Role",
        uselist=False,
        viewonly=True,
        primaryjoin="and_(foreign(ModelPermission.role_name)==Role.name)"
    )
    argument_presets: Mapped[List["ModelArgumentPreset"]] = TemporalRelationship(
        "ModelArgumentPreset",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ModelPermission.role_name) == ModelArgumentPreset.role_name, 
            foreign(ModelPermission.subgraph_name) == ModelArgumentPreset.subgraph_name, 
            foreign(ModelPermission.model_name) == ModelArgumentPreset.model_name
        )""",
        info={'skip_constraint': True}
    )
    filter_conditions: Mapped[List["FilterCondition"]] = TemporalRelationship(
        "FilterCondition",
        uselist=True,
        viewonly=True,
        primaryjoin="""and_(
            foreign(ModelPermission.role_name) == FilterCondition.role_name, 
            foreign(ModelPermission.subgraph_name) == FilterCondition.subgraph_name, 
            foreign(ModelPermission.model_name) == FilterCondition.model_name
        )""",
        info={'skip_constraint': True},
    )

    @classmethod
    def from_json(cls: Type["ModelPermission"], json_data: Dict[str, Any], subgraph: "Subgraph",
                  session: Session) -> List["ModelPermission"]:
        """
        Create ModelPermission instances from JSON data.

        Args:
            json_data: Dictionary containing model permissions configuration
            subgraph: the Subgraph
            session: SQLAlchemy session

        Returns:
            List of created ModelPermission instances

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if json_data.get("kind") != "ModelPermissions":
            raise ValueError(f"Expected ModelPermissions, got {json_data.get('kind')}")

        def_data = json_data.get("definition", {})
        model_name = def_data.get("modelName")
        if not model_name:
            raise ValueError("modelName is required")

        permissions = []
        for perm_data in def_data.get("permissions", []):
            role_name = perm_data.get("role")
            if not role_name:
                logger.warning(f"Skipping permission without role for model {model_name}")
                continue

            select_data = perm_data.get("select", {})

            # Create the base permission
            permission = cls(
                subgraph_name=subgraph.name,
                model_name=model_name,
                role_name=role_name,
                allow_subscriptions=select_data.get("allowSubscriptions", False)
            )
            session.add(permission)
            session.flush()
            

            # Process argument presets if present
            for preset in select_data.get("argumentPresets", []):
                ModelArgumentPreset.from_json(preset, permission, session)

            # Process filter conditions if present
            filter_data = select_data.get("filter")
            if filter_data:
                FilterCondition.from_json(filter_data, permission, session)

            permissions.append(permission)

        session.flush()
        return permissions

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the model permission to a JSON-compatible dictionary.

        Returns:
            A dictionary matching the expected JSON structure for ModelPermission.
        """
        definition = {
            "modelName": self.model_name,
            "permissions": [
                {
                    "role": self.role_name,
                    "select": {
                        "allowSubscriptions": self.allow_subscriptions,
                        "argumentPresets": [
                            preset.to_json() for preset in self.argument_presets
                        ],
                        "filter": next((
                            condition.to_json() for condition in self.filter_conditions
                        ), None)
                    }
                }
            ]
        }

        return {
            "definition": definition,
            "kind": "ModelPermissions",
            "version": "v1"
        }
