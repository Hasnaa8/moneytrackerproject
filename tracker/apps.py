from django.apps import AppConfig


class TrackerConfig(AppConfig):
    name = 'tracker'

    def ready(self):
        import tracker.signals  # Import signals to ensure they are registered
