"""Console UI: menu loop, rich rendering, and input handling.

This module is the only place in the codebase allowed to call print()/input()
(directly or via rich.Console). It never re-implements domain decisions such
as stock availability, production quantity, or completion judgement -- every
such decision is delegated to the injected service instances (SampleService/
OrderService/ProductionLine/MonitoringService).
"""

from rich.console import Console
from rich.table import Table

from sample_order.domain import Sample
from sample_order.monitoring import STATE_AMPLE, STATE_DEPLETED, STATE_SHORTAGE
from sample_order.production import (
    NoJobInProgressError,
    ProductionNotYetCompleteError,
)
from sample_order.services import (
    DuplicateSampleError,
    InsufficientStockError,
    InvalidOrderStateError,
    UnknownSampleError,
)

_console = Console()

_STATUS_COLORS = {
    "RESERVED": "yellow",
    "CONFIRMED": "cyan",
    "PRODUCING": "magenta",
    "RELEASE": "green",
    "REJECTED": "red",
}

_INVENTORY_COLORS = {
    STATE_AMPLE: "green",
    STATE_SHORTAGE: "yellow",
    STATE_DEPLETED: "red",
}

_PAGE_SIZE = 10

_MAIN_MENU_TEXT = """\
==============================================
 반도체 시료 생산주문관리 시스템
----------------------------------------------
[1] 시료 관리   [2] 시료 주문   [3] 주문 승인/거절
[4] 모니터링    [5] 생산 라인 조회   [6] 출고 처리
[0] 종료
=============================================="""


# ---------------------------------------------------------------------------
# Rendering helpers (pure output, no service calls)
# ---------------------------------------------------------------------------


def _badge(status):
    """Return a rich color markup string for an order status.

    The raw status text is always included so the meaning survives even on
    terminals that do not render ANSI colors (SPEC.md 11).
    """
    color = _STATUS_COLORS.get(status)
    if color is None:
        return status
    return f"[{color}]{status}[/{color}]"


def _inventory_badge(state):
    color = _INVENTORY_COLORS.get(state)
    if color is None:
        return state
    return f"[{color}]{state}[/{color}]"


def _paginate(items, page, page_size=_PAGE_SIZE):
    """Slice items for the given 1-indexed page.

    Returns (page_items, has_more, remaining_count) where has_more is True
    only when there are additional items beyond this page, and
    remaining_count is how many items are left after this page.
    """
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]
    remaining = max(0, len(items) - end)
    has_more = remaining > 0
    return page_items, has_more, remaining


def _render_main_menu():
    _console.print(_MAIN_MENU_TEXT)


def _render_message(message):
    _console.print(message)


def _render_error(exc):
    _console.print(f"[red]오류: {exc}[/red]")


def _render_sample_table(samples):
    table = Table(title=f"등록 시료 목록 (총 {len(samples)}종)")
    table.add_column("ID")
    table.add_column("이름")
    table.add_column("평균생산시간(min/ea)")
    table.add_column("수율")
    table.add_column("재고")
    for sample in samples:
        table.add_row(
            sample.sample_id,
            sample.name,
            str(sample.average_production_time),
            str(sample.yield_rate),
            str(sample.stock),
        )
    _console.print(table)


def _render_order_table(orders, title):
    table = Table(title=title)
    table.add_column("주문 ID")
    table.add_column("고객명")
    table.add_column("시료 ID")
    table.add_column("수량")
    table.add_column("상태")
    for order in orders:
        table.add_row(
            order.order_id,
            order.customer_name,
            order.sample_id,
            str(order.quantity),
            _badge(order.status),
        )
    _console.print(table)


def _render_status_counts(counts, rejected_count):
    table = Table(title="상태별 주문 수")
    table.add_column("상태")
    table.add_column("건수")
    for status, count in counts.items():
        table.add_row(_badge(status), str(count))
    table.add_row(_badge("REJECTED"), f"{rejected_count} (참고, 정상 합계 제외)")
    _console.print(table)


def _render_inventory_status(statuses):
    table = Table(title="시료별 재고 상태")
    table.add_column("ID")
    table.add_column("이름")
    table.add_column("재고")
    table.add_column("미출고 수량")
    table.add_column("상태")
    for status in statuses:
        table.add_row(
            status.sample_id,
            status.name,
            str(status.stock),
            str(status.unshipped_quantity),
            _inventory_badge(status.state),
        )
    _console.print(table)


def _render_production_overview(jobs):
    in_progress = [job for job in jobs if job.status == "IN_PROGRESS"]
    queued = [job for job in jobs if job.status == "QUEUED"]

    if in_progress:
        current = in_progress[0]
        _console.print(
            f"현재 진행 중: {current.job_id} ({current.sample_id}, "
            f"계획 {current.planned_quantity}개, 시작 {current.started_at})"
        )
    else:
        _console.print("현재 진행 중: 없음")

    if queued:
        table = Table(title="대기 큐 (FIFO)")
        table.add_column("작업 ID")
        table.add_column("시료 ID")
        table.add_column("부족분")
        table.add_column("계획 수량")
        for job in queued:
            table.add_row(
                job.job_id, job.sample_id, str(job.shortage), str(job.planned_quantity)
            )
        _console.print(table)
    else:
        _console.print("대기 큐: 비어 있음")


def _paginated_prompt_and_render(items, render_fn):
    """Render items page by page; render_fn(page_items) draws one page.

    Returns after the user stops requesting more pages (either no more items
    remain, or the user enters anything other than 'N').
    """
    page_number = 1
    while True:
        page_items, has_more, remaining = _paginate(items, page_number)
        render_fn(page_items)
        if not has_more:
            return
        _console.print(f"...외 {remaining}종 [N] 다음페이지")
        choice = _prompt("선택 > ")
        if choice.strip().upper() != "N":
            return
        page_number += 1


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------


def _prompt(label):
    return input(label)


def _prompt_int(label):
    return int(_prompt(label))


def _prompt_float(label):
    return float(_prompt(label))


# ---------------------------------------------------------------------------
# Menu handlers
# ---------------------------------------------------------------------------


def _menu_sample(sample_service):
    while True:
        _render_message("\n[1] 시료 등록  [2] 시료 목록  [3] 시료 검색  [0] 이전 메뉴")
        choice = _prompt("선택 > ").strip()
        if choice == "0":
            return
        if choice == "1":
            _handle_sample_register(sample_service)
        elif choice == "2":
            _paginated_prompt_and_render(
                sample_service.list_all(), _render_sample_table
            )
        elif choice == "3":
            keyword = _prompt("검색어 > ")
            _paginated_prompt_and_render(
                sample_service.search(keyword), _render_sample_table
            )
        else:
            _render_message("알 수 없는 선택입니다.")


def _handle_sample_register(sample_service):
    try:
        sample_id = _prompt("시료 ID > ")
        name = _prompt("이름 > ")
        average_production_time = _prompt_float("평균 생산시간(min/ea) > ")
        yield_rate = _prompt_float("수율(0~1) > ")
        stock = _prompt_int("재고 > ")
    except ValueError as exc:
        _render_error(exc)
        return

    try:
        sample = sample_service.register(
            Sample(
                sample_id=sample_id,
                name=name,
                average_production_time=average_production_time,
                yield_rate=yield_rate,
                stock=stock,
            )
        )
    except DuplicateSampleError as exc:
        _render_error(exc)
        return
    _render_message(f"등록 완료: {sample.sample_id} ({sample.name})")


def _menu_order_place(order_service):
    try:
        sample_id = _prompt("시료 ID > ")
        customer_name = _prompt("고객명 > ")
        quantity = _prompt_int("수량 > ")
    except ValueError as exc:
        _render_error(exc)
        return

    try:
        order = order_service.place_order(sample_id, customer_name, quantity)
    except UnknownSampleError as exc:
        _render_error(exc)
        return
    _render_message(f"접수 완료: {order.order_id} {_badge(order.status)}")


def _menu_order_review(order_service):
    reserved = [
        order for order in order_service.list_all() if order.status == "RESERVED"
    ]
    _render_order_table(reserved, "승인 대기 목록 (RESERVED)")
    if not reserved:
        return

    order_id = _prompt("주문 ID > ")
    action = _prompt("[1] 승인  [2] 거절 > ").strip()
    try:
        if action == "1":
            order = order_service.approve(order_id)
            if order.status == "CONFIRMED":
                _render_message(f"승인 완료: {order.order_id} {_badge(order.status)}")
            else:
                _render_message(
                    f"재고 부족으로 생산 큐에 등록되었습니다. -> "
                    f"{order.order_id} {_badge(order.status)}"
                )
        elif action == "2":
            order = order_service.reject(order_id)
            _render_message(f"거절 완료: {order.order_id} {_badge(order.status)}")
        else:
            _render_message("알 수 없는 선택입니다.")
    except InvalidOrderStateError as exc:
        _render_error(exc)


def _menu_monitoring(monitoring_service):
    counts = monitoring_service.order_status_counts()
    rejected_count = monitoring_service.rejected_count()
    _render_status_counts(counts, rejected_count)
    _render_inventory_status(monitoring_service.inventory_status())


def _menu_production(sample_service, order_service, production_line):
    while True:
        _render_production_overview(production_line.list_all())
        _render_message("[1] 다음 작업 시작  [2] 완료 처리  [0] 이전 메뉴")
        choice = _prompt("선택 > ").strip()
        if choice == "0":
            return
        if choice == "1":
            job = production_line.start_next()
            if job is None:
                _render_message("대기 중인 작업이 없습니다.")
            else:
                _render_message(f"{job.job_id} 작업을 시작했습니다.")
        elif choice == "2":
            try:
                job = production_line.complete_current(sample_service, order_service)
            except NoJobInProgressError as exc:
                _render_error(exc)
            except ProductionNotYetCompleteError as exc:
                _render_error(exc)
            else:
                sample = sample_service.find(job.sample_id)
                _render_message(
                    f"완료 처리 결과: {job.job_id} DONE, 재고 {sample.stock} "
                    f"(planned {job.planned_quantity})"
                )
                _render_message(
                    f"{job.order_id} 상태가 CONFIRMED로 바뀌었습니다."
                )
        else:
            _render_message("알 수 없는 선택입니다.")


def _menu_release(sample_service, order_service):
    confirmed = [
        order for order in order_service.list_all() if order.status == "CONFIRMED"
    ]
    _render_order_table(confirmed, "출고 대상 (CONFIRMED)")
    if not confirmed:
        return

    order_id = _prompt("주문 ID > ")
    try:
        order = order_service.release(order_id)
    except (InvalidOrderStateError, InsufficientStockError) as exc:
        _render_error(exc)
        return
    sample = sample_service.find(order.sample_id)
    _render_message(
        f"출고 완료: {order.order_id} {_badge(order.status)}, 재고 {sample.stock}"
    )


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run(
    sample_service,
    order_service,
    production_line,
    monitoring_service,
    on_exit=None,
):
    """Run the 6+1 main menu loop until the user chooses to exit."""
    while True:
        _render_main_menu()
        choice = _prompt("선택 > ").strip()
        if choice == "0":
            _render_message("저장 후 종료합니다.")
            if on_exit is not None:
                on_exit()
            return
        elif choice == "1":
            _menu_sample(sample_service)
        elif choice == "2":
            _menu_order_place(order_service)
        elif choice == "3":
            _menu_order_review(order_service)
        elif choice == "4":
            _menu_monitoring(monitoring_service)
        elif choice == "5":
            _menu_production(sample_service, order_service, production_line)
        elif choice == "6":
            _menu_release(sample_service, order_service)
        else:
            _render_message("알 수 없는 선택입니다.")
