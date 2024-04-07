def generate_temp_password(length):
    if not isinstance(length, int) or length < 8:
        raise ValueError("temp password must have positive length")

    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%^&*()"
    from os import urandom
    # Python 3 (urandom returns bytes)
    return "".join(chars[c % len(chars)] for c in urandom(length))


def generate_commit_sha(length):
    if not isinstance(length, int) or length < 8:
        raise ValueError("sha must have positive length")

    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    from os import urandom
    # Python 3 (urandom returns bytes)
    return "".join(chars[c % len(chars)] for c in urandom(length))


def delete_job_task(self):
    if self and self.id:
        job_q_env = self.env['queue.job']
        jobs = job_q_env.search([
            "|", "|", "|", ("state", "=", "pending"), (
                "state", "=", "enqueued"), ("state", "=", "started"), ("state", "=", "failed"),
            ('func_string', '=', "kk_odoo_saas.app({0},).post_init_tasks()".format(self.id))])
        for job in jobs:
            job.button_done()
