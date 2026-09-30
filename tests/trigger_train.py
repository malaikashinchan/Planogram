from backend.app.workers.celery_app import celery_app
celery_app.send_task("backend.app.workers.training_tasks.launch_training_task")
print("Task triggered!")
