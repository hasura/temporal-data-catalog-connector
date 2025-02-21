from ..base.core_base import CoreBase
from ..mixins.rdf import RDFGeneratorMixin, RDFNeo4jExport
from ..mixins.temporal import TemporalViewMixin, TemporalMixin


class Base(CoreBase, RDFGeneratorMixin, RDFNeo4jExport, TemporalMixin, TemporalViewMixin):
    __abstract__ = True
