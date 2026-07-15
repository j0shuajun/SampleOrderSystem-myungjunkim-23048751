"""Entry point: assemble services, load persisted state, run the console UI.

Usage:
    python3 main.py [data-path.json]

If no path is given, "data.json" in the current directory is used. On exit
(menu item 0), the current state is saved back to the same path.
"""

import sys

from sample_order import cli
from sample_order.monitoring import MonitoringService
from sample_order.production import ProductionLine
from sample_order.repository import Repository
from sample_order.services import OrderService, SampleService


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "data.json"

    sample_service = SampleService()
    production_line = ProductionLine()
    order_service = OrderService(sample_service, production_line=production_line)
    monitoring_service = MonitoringService(sample_service, order_service)

    repository = Repository(path)
    repository.load_into(sample_service, order_service, production_line)

    cli.run(
        sample_service,
        order_service,
        production_line,
        monitoring_service,
        on_exit=lambda: repository.save(sample_service, order_service, production_line),
    )


if __name__ == "__main__":
    main()
