from typing import TypeVar, Generic, Iterator, Type, Optional, Any, Union, overload

from sqlalchemy import and_, select
from sqlalchemy.orm import Query, RelationshipProperty
from sqlalchemy.orm.attributes import QueryableAttribute

T = TypeVar('T')


class TemporalRelationship(RelationshipProperty, Generic[T]):
    inherit_cache = True

    def __init__(self, argument: Union[Type[T], str], **kw):
        self.uselist = kw.get('uselist', True)  # Default to True for backwards compatibility
        kw['lazy'] = 'select'

        # Initialize the RelationshipProperty first
        super().__init__(argument, **kw)

    def _apply_temporal_criteria(self, query: Query) -> Query:
        parent = query._propagate_attrs['parent']
        parent_alias = query.with_parent(parent).correlate(None).column_descriptions[0]['expr']

        # Get the related model class dynamically
        related_model = self.argument
        if isinstance(related_model, str):
            related_model = query.session.execute(select(related_model)).scalar()

        if parent.t_current:
            return query.filter(related_model.t_current)
        else:
            return query.filter(
                and_(related_model.t_created_at <= parent_alias.t_created_at)
            )

    def create_loader(self, state: Any) -> Any:
        loader = super().create_loader(state)
        loader._apply_to_inner_query = self._apply_temporal_criteria
        return loader

    @overload
    def __get__(self, instance: None, owner: Any) -> QueryableAttribute[Union[Iterator[T], Optional[T]]]:
        ...

    @overload
    def __get__(self, instance: Any, owner: Any) -> Union[Iterator[T], Optional[T]]:
        ...

    def __get__(self, instance: Any, owner: Any) -> Union[
        QueryableAttribute[Union[Iterator[T], Optional[T]]],
        Union[Iterator[T], Optional[T]]
    ]:
        result = super().__get__(instance, owner)
        return result
