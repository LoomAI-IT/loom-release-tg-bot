create_release = """
INSERT INTO releases (
    service_name, 
    release_version, 
    status, 
    initiated_by, 
    github_run_id, 
    github_action_link, 
    github_ref
)
VALUES (
    :service_name, 
    :release_version, 
    :status, 
    :initiated_by, 
    :github_run_id, 
    :github_action_link, 
    :github_ref
)
RETURNING id;
"""

get_active_releases = """
SELECT * FROM releases
WHERE status NOT IN (
    'deployed',
    'failed',
    'rollback',
    'cancelled'
)
ORDER BY created_at DESC;
"""

get_successful_releases = """
SELECT * FROM releases
WHERE status = 'deployed'
ORDER BY completed_at DESC;
"""

get_failed_releases = """
SELECT * FROM releases
WHERE status IN (
    'failed',
    'manual_test_failed',
    'rollback',
    'cancelled'
)
ORDER BY completed_at DESC, created_at DESC;
"""