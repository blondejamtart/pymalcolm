from annotypes import TYPE_CHECKING

from malcolm.core import PartRegistrar
from malcolm.modules.pandablocks.parts.pandabussespart import PandABussesPart
from malcolm.modules.pandablocks.util import PositionCapture
from malcolm.modules import scanning, ADCore
from ..util import DatasetBitsTable, DatasetPositionsTable

if TYPE_CHECKING:
    from typing import List


class PandADatasetBussesPart(PandABussesPart):
    bits_table_cls = DatasetBitsTable
    positions_table_cls = DatasetPositionsTable

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(PandADatasetBussesPart, self).setup(registrar)
        # Hooks
        self.register_hooked(scanning.hooks.ReportStatusHook,
                             self.report_status)

    def initial_bits_table(self, bit_names):
        # type: (List[str]) -> DatasetBitsTable
        ds_types = [ADCore.util.AttributeDatasetType.MONITOR] * len(bit_names)
        bits_table = DatasetBitsTable(
            name=bit_names,
            value=[False] * len(bit_names),
            capture=[False] * len(bit_names),
            datasetName=[""] * len(bit_names),
            datasetType=ds_types
        )
        return bits_table

    def initial_pos_table(self, pos_names):
        # type: (List[str]) -> DatasetPositionsTable
        ds_types = []
        for pos in pos_names:
            if pos.startswith("INENC"):
                ds_types.append(ADCore.util.AttributeDatasetType.POSITION)
            else:
                ds_types.append(ADCore.util.AttributeDatasetType.MONITOR)
        pos_table = DatasetPositionsTable(
            name=pos_names,
            value=[0.0] * len(pos_names),
            units=[""] * len(pos_names),
            scale=[1.0] * len(pos_names),
            offset=[0.0] * len(pos_names),
            capture=[PositionCapture.NO] * len(pos_names),
            datasetName=[""] * len(pos_names),
            datasetType=ds_types
        )
        return pos_table

    def report_status(self):
        # type: () -> scanning.hooks.UInfos
        ret = []
        bits_table = self.bits.value  # type: DatasetBitsTable
        for i, capture in enumerate(bits_table.capture):
            if capture:
                ret.append(ADCore.infos.NDAttributeDatasetInfo(
                    name=bits_table.datasetName[i],
                    type=bits_table.datasetType[i],
                    rank=2,
                    attr=bits_table.name[i]))
        pos_table = self.positions.value  # type: DatasetPositionsTable
        for i, capture in enumerate(pos_table.capture):
            ds_name = pos_table.datasetName[i]
            if ds_name and capture != PositionCapture.NO:
                # If we have Min Max Mean, just take Mean
                capture_suffix = capture.value.split(" ")[-1]
                ret.append(ADCore.infos.NDAttributeDatasetInfo(
                    name=ds_name,
                    type=pos_table.datasetType[i],
                    rank=2,
                    attr="%s.%s" % (pos_table.name[i], capture_suffix)))
        return ret