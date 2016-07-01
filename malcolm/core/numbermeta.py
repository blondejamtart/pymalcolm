from collections import OrderedDict

import numpy

from malcolm.core.scalarmeta import ScalarMeta
from malcolm.core.serializable import Serializable
from malcolm.compat import base_string


@Serializable.register("malcolm:core/NumberMeta:1.0")
class NumberMeta(ScalarMeta):
    """Meta object containing information for a numerical value"""

    def __init__(self, name, description, dtype):
        super(NumberMeta, self).__init__(name, description)
        self.dtype = dtype

    def validate(self, value):
        if value is None:
            return None
        cast = self.dtype(value)
        if not isinstance(value, base_string):
            assert cast == value, \
                "Lost information converting %s to %s" % (value, cast)
        return cast

    def to_dict(self):
        d = OrderedDict()
        d["typeid"] = self.typeid
        d["dtype"] = self.dtype().dtype.name

        d.update(super(NumberMeta, self).to_dict())
        return d

    @classmethod
    def from_dict(cls, name, d):
        dtype = numpy.dtype(d["dtype"]).type
        meta = cls(name, d["description"], dtype)
        meta.writeable = d["writeable"]
        meta.tags = d["tags"]
        meta.label = d["label"]
        return meta