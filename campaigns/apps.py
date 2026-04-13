import os
from django.apps import AppConfig


class CampaignsConfig(AppConfig):
    name = 'campaigns'

    def ready(self):
        # Only start scheduler in the main server process, not during migrations or shell
        if os.environ.get('RUN_MAIN') != 'true':
            return
        from campaigns.scheduler import start_scheduler
        start_scheduler()
