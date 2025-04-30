import configSetting


from threading import Thread

# custom thread


class ThreadWithReturnValue(Thread):
    def __init__(self, *init_args, **init_kwargs):
        Thread.__init__(self, *init_args, **init_kwargs)
        self._return = None

    def run(self):
        self._return = self._target(*self._args, **self._kwargs)

    def join(self):
        Thread.join(self)
        return self._return


def generateThreadWorkers(taskNumbers: int) -> int:
    thread_workers = int(taskNumbers**0.5) * 5
    if thread_workers >= configSetting.multithread_high:
        thread_workers = configSetting.multithread_high
    elif thread_workers >= configSetting.multithread_median:
        thread_workers = configSetting.multithread_median

    return thread_workers
