import json
from cron.jobs import create_job, update_job, remove_job, get_job

job = create_job(prompt='repeat-fix-smoke', schedule='every 1m', name='repeat-fix-smoke', repeat=-1, deliver='local')
job_id = job['id']

j1 = get_job(job_id)

update_job(job_id, {'name': 'repeat-fix-smoke-updated'})
j2 = get_job(job_id)

update_job(job_id, {'repeat': -1})
j3 = get_job(job_id)

payload = {
    'job_id': job_id,
    'before': j1.get('repeat'),
    'after_name_update': j2.get('repeat'),
    'after_repeat_minus1': j3.get('repeat'),
}
print(json.dumps(payload, ensure_ascii=False))

remove_job(job_id)
