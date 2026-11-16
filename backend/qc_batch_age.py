"""Exercise 7.1: a deterministic QC rule. Reject a component when its batch is
older than 30 days. No random numbers are involved."""
from dataclasses import dataclass
from datetime import date
from typing import List

import ballpen_production_line as bp


@dataclass
class BatchComponent(bp.Component):
    batch_date: date = date(2026, 11, 1)   # when the batch was produced


class BatchAgeQC(bp.QualityControl):
    MAX_AGE_DAYS = 30

    def __init__(self, name: str, today: date):
        super().__init__(name=name)
        self.today = today

    def process(self, item: BatchComponent) -> List[BatchComponent]:
        self.processed += 1
        age = (self.today - item.batch_date).days
        if age > self.MAX_AGE_DAYS:
            self.rejected += 1
            self.log(f"REJECT {item.name}#{item.serial} (batch is {age} days old)")
            return []
        self.log(f"pass   {item.name}#{item.serial} (batch is {age} days old)")
        return [item]


if __name__ == "__main__":
    today = date(2026, 11, 16)
    qc = BatchAgeQC("QC barrel", today)
    for serial, produced in enumerate([date(2026, 11, 6), date(2026, 10, 17), date(2026, 10, 16), date(2026, 9, 1)], 1):
        qc.process(BatchComponent("barrel", serial, batch_date=produced))
    print(f"processed={qc.processed} rejected={qc.rejected}")
