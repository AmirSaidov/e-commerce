from django.conf import settings
from rest_framework.throttling import ScopedRateThrottle


class AuthRateThrottle(ScopedRateThrottle):
    """ScopedRateThrottle, но ставки берутся из settings.AUTH_THROTTLE_RATES на каждом запросе.

    У DRF ставки читаются один раз при импорте класса, поэтому их нельзя поменять ни через .env
    без перезапуска, ни через override_settings в тестах.
    """

    def get_rate(self):
        return settings.AUTH_THROTTLE_RATES.get(self.scope) or None
