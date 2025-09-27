create_state = """
INSERT INTO user_states (tg_chat_id, tg_username)
VALUES (:tg_chat_id, :tg_username)
RETURNING id;
"""

state_by_id = """
SELECT * FROM user_states
WHERE tg_chat_id = :tg_chat_id;
"""

state_by_account_id = """
SELECT * FROM user_states
WHERE account_id = :account_id;
"""

delete_state_by_tg_chat_id = """
DELETE FROM user_states
WHERE tg_chat_id = :tg_chat_id;
"""