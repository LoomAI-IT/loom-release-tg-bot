create_state_table = """
CREATE TABLE IF NOT EXISTS user_states (
    id SERIAL PRIMARY KEY,
    tg_chat_id BIGINT NOT NULL,
    tg_username TEXT DEFAULT '',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


drop_state_table = """
DROP TABLE IF EXISTS user_states;
"""


create_queries = [create_state_table]
drop_queries = [drop_state_table]
