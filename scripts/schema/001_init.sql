CREATE SCHEMA IF NOT EXISTS platform;
CREATE SCHEMA IF NOT EXISTS vendor;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS agno;

CREATE TABLE IF NOT EXISTS platform.agent_nodes (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    system_prompt TEXT NOT NULL DEFAULT '',
    model_id TEXT,
    model_provider TEXT,
    model_api_key TEXT,
    model_base_url TEXT,
    session_table TEXT,
    runtime_config_json TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    public_name TEXT,
    image_file_id BIGINT,
    priority INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    metadata_json TEXT,
    created_by BIGINT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS platform.agent_node_edges (
    id BIGSERIAL PRIMARY KEY,
    parent_node_id BIGINT NOT NULL,
    child_node_id BIGINT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    member_instructions_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS platform.tools (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    progress_label TEXT,
    progress_visual_type TEXT,
    progress_visual_value TEXT,
    tool_type TEXT NOT NULL,
    user_types TEXT NOT NULL DEFAULT '[]',
    parameters TEXT NOT NULL DEFAULT '[]',
    required_tool_ids TEXT NOT NULL DEFAULT '[]',
    show_result BOOLEAN NOT NULL DEFAULT FALSE,
    action_only_name TEXT,
    action_only_description TEXT,
    rule_method TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    public_name TEXT,
    agent_id BIGINT,
    api_url TEXT,
    api_method TEXT NOT NULL DEFAULT 'GET',
    api_headers TEXT,
    api_body_template TEXT,
    metadata_json TEXT,
    created_by BIGINT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS platform.tool_actions (
    id BIGSERIAL PRIMARY KEY,
    tool_id BIGINT,
    slug TEXT,
    name TEXT,
    description TEXT NOT NULL DEFAULT '',
    fa_name TEXT,
    fa_description TEXT,
    constructor_params TEXT NOT NULL DEFAULT '{}',
    response_title TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata_json TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS platform.tool_action_bindings (
    id BIGSERIAL PRIMARY KEY,
    tool_id BIGINT NOT NULL,
    action_id BIGINT NOT NULL,
    constructor_params TEXT NOT NULL DEFAULT '{}',
    response_title TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    metadata_json TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS platform.tool_knowledge_nodes (
    id BIGSERIAL PRIMARY KEY,
    tool_slug TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS platform.agent_node_tool_bindings (
    id BIGSERIAL PRIMARY KEY,
    node_id BIGINT NOT NULL,
    tool_id BIGINT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    binding_mode TEXT,
    metadata_json TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS platform.mcp_servers (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    transport TEXT NOT NULL,
    command TEXT,
    url TEXT,
    working_directory TEXT,
    env_json TEXT,
    headers_json TEXT,
    include_tools_json TEXT,
    exclude_tools_json TEXT,
    tool_name_prefix TEXT,
    timeout_seconds INTEGER NOT NULL DEFAULT 15,
    refresh_connection BOOLEAN NOT NULL DEFAULT FALSE,
    allow_partial_failure BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    public_name TEXT,
    metadata_json TEXT,
    created_by BIGINT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS platform.agent_node_mcp_bindings (
    id BIGSERIAL PRIMARY KEY,
    node_id BIGINT NOT NULL,
    mcp_server_id BIGINT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    binding_mode TEXT,
    header_template_json TEXT,
    metadata_json TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS platform.skill_packages (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    source_path TEXT NOT NULL,
    metadata_json TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    public_name TEXT,
    created_by BIGINT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS platform.agent_node_skill_bindings (
    id BIGSERIAL PRIMARY KEY,
    node_id BIGINT NOT NULL,
    skill_package_id BIGINT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata_json TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS platform.agent_api_keys (
    id BIGSERIAL PRIMARY KEY,
    node_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS platform.agent_channels (
    id BIGSERIAL PRIMARY KEY,
    node_id BIGINT NOT NULL,
    channel_type TEXT NOT NULL,
    name TEXT NOT NULL,
    bot_token_encrypted TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    token_hint TEXT NOT NULL,
    api_base_url TEXT NOT NULL,
    webhook_secret_encrypted TEXT NOT NULL,
    webhook_secret_hash TEXT NOT NULL,
    webhook_url TEXT,
    bot_id TEXT,
    bot_username TEXT,
    bot_display_name TEXT,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    metadata_json TEXT,
    last_verified_at TIMESTAMPTZ,
    last_webhook_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS platform.agent_channel_updates (
    id BIGSERIAL PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    provider_update_id BIGINT NOT NULL,
    status TEXT NOT NULL DEFAULT 'processing',
    error_message TEXT,
    received_at TIMESTAMPTZ DEFAULT now(),
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS vendor.llm_request_logs (
    id BIGSERIAL PRIMARY KEY,
    scope TEXT NOT NULL DEFAULT '',
    model TEXT,
    messages TEXT,
    response TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS vendor.message_feedbacks (
    id BIGSERIAL PRIMARY KEY,
    vendor_id BIGINT NOT NULL,
    user_id BIGINT,
    session_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    is_positive BOOLEAN NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    x_ref TEXT
);

CREATE TABLE IF NOT EXISTS agno.agno_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    workflow_id TEXT,
    team_id TEXT,
    agent_id TEXT,
    session_type TEXT NOT NULL DEFAULT '',
    session_data JSONB,
    agent_data JSONB,
    summary JSONB,
    runs JSONB,
    metadata JSONB,
    workflow_data JSONB,
    team_data JSONB,
    created_at BIGINT,
    updated_at BIGINT,
    x_ref TEXT
);

CREATE INDEX IF NOT EXISTS agent_nodes_slug_idx
    ON platform.agent_nodes (slug, is_active);
CREATE INDEX IF NOT EXISTS agent_nodes_active_idx
    ON platform.agent_nodes (is_active, priority);

CREATE INDEX IF NOT EXISTS agent_node_edges_parent_idx
    ON platform.agent_node_edges (parent_node_id, is_active, priority);
CREATE INDEX IF NOT EXISTS agent_node_edges_child_idx
    ON platform.agent_node_edges (child_node_id, is_active);

CREATE INDEX IF NOT EXISTS tools_slug_idx
    ON platform.tools (slug, is_active) WHERE slug IS NOT NULL;
CREATE INDEX IF NOT EXISTS tools_active_idx
    ON platform.tools (is_active, name);
CREATE INDEX IF NOT EXISTS tools_agent_idx
    ON platform.tools (agent_id, is_active);

CREATE INDEX IF NOT EXISTS tool_actions_slug_idx
    ON platform.tool_actions (slug, is_active) WHERE slug IS NOT NULL;
CREATE INDEX IF NOT EXISTS tool_actions_tool_idx
    ON platform.tool_actions (tool_id, is_active, priority);

CREATE INDEX IF NOT EXISTS tool_action_bindings_tool_idx
    ON platform.tool_action_bindings (tool_id, is_enabled, priority);

CREATE INDEX IF NOT EXISTS tool_knowledge_nodes_slug_idx
    ON platform.tool_knowledge_nodes (tool_slug, is_active, priority, id);

CREATE INDEX IF NOT EXISTS agent_node_tool_bindings_node_idx
    ON platform.agent_node_tool_bindings (node_id, is_enabled, priority);

CREATE INDEX IF NOT EXISTS mcp_servers_slug_idx
    ON platform.mcp_servers (slug, is_active);
CREATE INDEX IF NOT EXISTS mcp_servers_active_idx
    ON platform.mcp_servers (is_active, name);

CREATE INDEX IF NOT EXISTS agent_node_mcp_bindings_node_idx
    ON platform.agent_node_mcp_bindings (node_id, is_enabled, priority);

CREATE INDEX IF NOT EXISTS skill_packages_slug_idx
    ON platform.skill_packages (slug, is_active);
CREATE INDEX IF NOT EXISTS skill_packages_active_idx
    ON platform.skill_packages (is_active, name);

CREATE INDEX IF NOT EXISTS agent_node_skill_bindings_node_idx
    ON platform.agent_node_skill_bindings (node_id, is_enabled, priority);

CREATE UNIQUE INDEX IF NOT EXISTS agent_api_keys_hash_uq
    ON platform.agent_api_keys (key_hash);
CREATE INDEX IF NOT EXISTS agent_api_keys_node_idx
    ON platform.agent_api_keys (node_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS agent_channels_node_type_uq
    ON platform.agent_channels (node_id, channel_type);
CREATE UNIQUE INDEX IF NOT EXISTS agent_channels_token_hash_uq
    ON platform.agent_channels (token_hash);

CREATE UNIQUE INDEX IF NOT EXISTS agent_channel_updates_provider_uq
    ON platform.agent_channel_updates (channel_id, provider_update_id);

CREATE INDEX IF NOT EXISTS llm_request_logs_scope_created_idx
    ON vendor.llm_request_logs (scope, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS message_feedbacks_scope_uq
    ON vendor.message_feedbacks (vendor_id, session_id, message_id);
CREATE INDEX IF NOT EXISTS message_feedbacks_session_idx
    ON vendor.message_feedbacks (vendor_id, session_id);

CREATE INDEX IF NOT EXISTS agno_sessions_user_updated_idx
    ON agno.agno_sessions (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS agno_sessions_agent_updated_idx
    ON agno.agno_sessions (agent_id, updated_at DESC);
