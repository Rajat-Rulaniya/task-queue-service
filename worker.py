#!/usr/bin/env python
"""
Celery worker script
Run with: celery -A worker worker --loglevel=info -c 4
"""

import sys
import os
import asyncio
from celery_app import celery_app
from tasks import parse_csv_task, send_email_task, process_data_task
from database import init_db
from celery.signals import worker_process_init


@worker_process_init.connect
def init_worker(**kwargs):
    """Initialize database connection for each worker process"""
    print("Initializing database for worker process...")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())


if __name__ == "__main__":
    # Register tasks
    celery_app.register_task(parse_csv_task)
    celery_app.register_task(send_email_task)
    celery_app.register_task(process_data_task)
    
    # Start worker
    celery_app.worker_main(
        argv=[
            "worker",
            "--loglevel=info",
            "-c", "4",  # 4 concurrent workers
            "-n", "worker@%h",
        ]
    )
