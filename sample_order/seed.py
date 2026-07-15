"""Seed/dummy data generator, reimplemented from the DummyDataGenerator PoC
(https://github.com/j0shuajun/DummyDataGenerator-myungjunkim-23048751) for this
repo's own JSON schema (SPEC.md section 13). No console input/output here --
loading seed data only happens via the explicit `python -m sample_order.seed`
command below, never automatically from main.py (CLAUDE.md section 4).
"""

import argparse
import math
import random
from datetime import datetime

from sample_order.storage import save

_SAMPLE_NAMES = [
    "실리콘 웨이퍼-8인치",
    "GaN 에피택셜-4인치",
    "SiC 파워기판-6인치",
    "포토레지스트-PR7",
    "산화막 웨이퍼-SiO2",
]

_CUSTOMERS = ["삼성전자 파운드리", "SK하이닉스", "LG이노텍", "DB하이텍", "Fabless A"]

_ORDER_STATUSES = ("RESERVED", "REJECTED", "PRODUCING", "CONFIRMED", "RELEASE")


def _sample_id(index):
    return f"S-{index:03d}"


def _order_id(date_str, index):
    return f"ORD-{date_str}-{index:04d}"


def _job_id(index):
    return f"JOB-{index:04d}"


def _generate_samples(count, rng):
    samples = []
    for i in range(1, count + 1):
        samples.append(
            {
                "sample_id": _sample_id(i),
                "name": _SAMPLE_NAMES[(i - 1) % len(_SAMPLE_NAMES)],
                "average_production_time": round(rng.uniform(0.2, 1.0), 2),
                "yield_rate": round(rng.uniform(0.7, 0.98), 2),
                "stock": rng.randint(0, 500),
            }
        )
    return samples


def _generate_orders(count, samples, rng, date_str):
    orders = []
    for i in range(1, count + 1):
        sample = rng.choice(samples)
        orders.append(
            {
                "order_id": _order_id(date_str, i),
                "sample_id": sample["sample_id"],
                "customer_name": rng.choice(_CUSTOMERS),
                "quantity": rng.randint(1, 300),
                "status": rng.choice(_ORDER_STATUSES),
            }
        )
    return orders


def _generate_production_jobs(orders, samples, start_time_str):
    samples_by_id = {sample["sample_id"]: sample for sample in samples}
    jobs = []
    job_number = 1
    for order in orders:
        if order["status"] != "PRODUCING":
            continue
        sample = samples_by_id[order["sample_id"]]
        shortage = max(0, order["quantity"] - sample["stock"])
        planned_quantity = math.ceil(shortage / sample["yield_rate"]) if shortage else 0
        jobs.append(
            {
                "job_id": _job_id(job_number),
                "order_id": order["order_id"],
                "sample_id": order["sample_id"],
                "shortage": shortage,
                "planned_quantity": planned_quantity,
                "status": "QUEUED",
                "started_at": None,
            }
        )
        job_number += 1
    return jobs


def build_seed_data(sample_count, order_count, seed=None, now=datetime.now):
    rng = random.Random(seed)
    current = now()
    samples = _generate_samples(sample_count, rng)
    orders = _generate_orders(order_count, samples, rng, current.strftime("%Y%m%d"))
    production_jobs = _generate_production_jobs(
        orders, samples, current.isoformat(timespec="seconds")
    )
    return {"samples": samples, "orders": orders, "production_jobs": production_jobs}


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Generate seed/dummy data for SampleOrderSystem."
    )
    parser.add_argument("path", help="더미 데이터를 저장할 JSON 파일 경로")
    parser.add_argument("--samples", type=int, default=5, help="생성할 시료 수")
    parser.add_argument("--orders", type=int, default=20, help="생성할 주문 수")
    parser.add_argument("--seed", type=int, default=None, help="재현 가능한 랜덤 시드")
    return parser.parse_args()


def main():
    args = _parse_args()
    data = build_seed_data(
        sample_count=args.samples, order_count=args.orders, seed=args.seed
    )
    save(args.path, data)
    print(
        f"더미 데이터 생성 완료: 시료 {len(data['samples'])}종, "
        f"주문 {len(data['orders'])}건, 생산작업 {len(data['production_jobs'])}건 "
        f"-> {args.path}"
    )


if __name__ == "__main__":
    main()
