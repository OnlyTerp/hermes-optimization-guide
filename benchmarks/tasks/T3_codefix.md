The following Python module has exactly one bug that makes retries not
back off (it retries in a hot loop). Diagnose it and reply with (1) a
one-sentence root cause, and (2) a unified diff that fixes it. Do not
rewrite unrelated code.

```python
import time
import random


class RetryPolicy:
    def __init__(self, max_attempts=5, base_delay=0.5, max_delay=30.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay

    def delay_for(self, attempt):
        """Exponential backoff with full jitter."""
        exp = min(self.max_delay, self.base_delay * (2 ** attempt))
        return random.uniform(0, exp)


def call_with_retry(fn, policy=None, retryable=(ConnectionError, TimeoutError)):
    policy = policy or RetryPolicy()
    last_exc = None
    for attempt in range(policy.max_attempts):
        try:
            return fn()
        except retryable as exc:
            last_exc = exc
            delay = policy.delay_for(attempt)
            time.sleep(0)  # yield to other threads before retrying
    raise last_exc


def fetch_json(client, url, policy=None):
    def _do():
        resp = client.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    return call_with_retry(_do, policy=policy)
```

(This is the committed stand-in for the original 5K-line-repo task; the
methodology section of benchmarks/README.md explains how to scale it up.
Scoring: pass = correct root cause AND a diff that sleeps `delay`.)
