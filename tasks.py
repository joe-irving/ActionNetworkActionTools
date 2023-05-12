from celery import Celery
# from celery.schedules import crontab
from action_network_rolling_emails import RollingEmailer as RollingEmailerProcess
# import time
# from app import db, app, RollingEmailer

celery = Celery("tasks", broker="redis://localhost:6379")

@celery.task()
def process_emailer(rolling_emailer):
    print("Process Emailer Starting")
    process_tool = RollingEmailerProcess(
        rolling_emailer["trigger_tag_id"],
        rolling_emailer["target_view"],
        rolling_emailer["message_view"],
        rolling_emailer["prefix"],
        rolling_emailer["end_tag_id"]
    )
    return process_tool.process()

# @celery.task()
# def trigger_start():
#     print("trigger start")
#     print(celery.conf.beat_schedule)
    # with app.app_context():
    #     emailers = RollingEmailer.query.all()
    #     for emailer in emailers:
    #         process_emailer(emailer.to_dict())

# @celery.on_after_configure.connect
# def setup_periodic_tasks(sender, **kwargs):
#     sender.add_periodic_task(60.0, trigger_start.s(), name='Goes through tags every min')

# @celery.task()
# def setup_schedule(rolling_emailer):
#     celery.add_periodic_task(float(rolling_emailer['schedule']), process_emailer.s(rolling_emailer), name=f"rolling-emailer-{rolling_emailer['id']}")
#     print(celery.conf.beat_schedule)
#     return celery.conf.beat_schedule
    

celery.autodiscover_tasks()
