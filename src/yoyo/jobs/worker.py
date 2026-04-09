from yoyo.jobs.tasks.guide_generation import run_guide_generation_job


class WorkerSettings:
    functions = [run_guide_generation_job]
