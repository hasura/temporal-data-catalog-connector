from sqlalchemy.orm import Mapped

from .model_orderable_field_base import ModelOrderableField as BaseModelOrderableField
from ...mixins.temporal.temporal_relationship import TemporalRelationship
from ...model.model_base import Model


class ModelOrderableField(BaseModelOrderableField):
    __tablename__ = "model_orderable_field"

    model: Mapped["Model"] = TemporalRelationship(
        "Model",
        primaryjoin="and_(foreign(ModelOrderableField.model_name) == Model.name)",
        uselist=False)
