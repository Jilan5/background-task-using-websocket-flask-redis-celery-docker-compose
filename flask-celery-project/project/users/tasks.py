import random

import requests
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task
def divide(x, y):
    # from celery.contrib import rdb
    # rdb.set_trace()

    import time
    time.sleep(5)
    return x / y


@shared_task()
def sample_task(email):
    from project.users.views import api_call

    api_call(email)

@shared_task(bind=True)
def task_process_notification(self):
    try:
        if not random.choice([0, 1]):
            # mimic random error
            raise Exception()

        # this would block the I/O
        requests.post('https://httpbin.org/delay/5')
    except Exception as e:
        logger.error('exception raised, it would be retry after 5 seconds')
        raise self.retry(exc=e, countdown=5)
    

import os

from celery.result import AsyncResult
from flask_socketio import emit, join_room, SocketIO

from project import socketio


SOCKETIO_MESSAGE_QUEUE = os.environ.get(
    'SOCKETIO_MESSAGE_QUEUE',
    'redis://127.0.0.1:6379/0'
)

socketio_instance = SocketIO(message_queue=SOCKETIO_MESSAGE_QUEUE)


def get_task_info(task_id):
    """
    return task info according to the task_id
    """
    task = AsyncResult(task_id)
    state = task.state

    if state == 'FAILURE':
        error = str(task.result)
        response = {
            'state': state,
            'error': error,
        }
    else:
        response = {
            'state': state,
        }
    return response


def update_celery_task_status(task_id):
    """
    This function would be called in Celery worker
    https://flask-socketio.readthedocs.io/en/latest/deployment.html#emitting-from-an-external-process
    https://github.com/miguelgrinberg/Flask-SocketIO/issues/618#issuecomment-357753909
    """
    socketio_instance.emit('status', get_task_info(task_id), room=task_id, namespace='/task_status')


from celery.signals import task_postrun

@task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    """
    This function would be called after a Celery task is completed
    """
    from project.users.events import update_celery_task_status
    update_celery_task_status(task_id)
