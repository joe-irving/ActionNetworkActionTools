from celery import Celery
from action_network_rolling_emails import RollingEmailer as RollingEmailerProcess

celery = Celery("tasks", broker="redis://redis:6379")


@celery.task()
def process_emailer(rolling_emailer):
    print("Process Emailer Starting")
    process_tool = RollingEmailerProcess(
        rolling_emailer["trigger_tag_id"],
        rolling_emailer["target_view"],
        rolling_emailer["message_view"],
        rolling_emailer["prefix"],
        rolling_emailer["end_tag_id"],
        an_key=rolling_emailer["action_network_api_key"],
        targets_each=rolling_emailer["targets_each"],
        delay_mins=rolling_emailer["delay_mins"]
    )
    return process_tool.process()

# celery.autodiscover_tasks()
