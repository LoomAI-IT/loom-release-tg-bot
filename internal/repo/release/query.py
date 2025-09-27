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