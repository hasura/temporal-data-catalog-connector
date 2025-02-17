from ..base.core_base import CoreBase
from ..mixins.rdf import RDFGeneratorMixin, RDFNeo4jExport
from ..mixins.temporal import TemporalViewMixin, TemporalMixin


class Base(CoreBase, TemporalMixin, TemporalViewMixin, RDFGeneratorMixin, RDFNeo4jExport):
    __abstract__ = True
