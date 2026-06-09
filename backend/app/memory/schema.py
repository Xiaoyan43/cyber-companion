SCHEMA_VERSION = 2

MEMORY_TYPES = (
    "stable_profile",
    "recent_event",
    "emotion_state",
    "project",
    "job_progress",
    "reminder",
    "relationship_state",
    "behavior_preference",
    "conversation_summary",
)

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'chat',
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS conversation_summaries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  range_start_message_id INTEGER NOT NULL,
  range_end_message_id INTEGER NOT NULL,
  summary TEXT NOT NULL,
  keywords_json TEXT NOT NULL DEFAULT '[]',
  FOREIGN KEY (range_start_message_id) REFERENCES messages(id),
  FOREIGN KEY (range_end_message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  type TEXT NOT NULL,
  content TEXT NOT NULL,
  tags_json TEXT NOT NULL DEFAULT '[]',
  importance REAL NOT NULL DEFAULT 0.5,
  confidence REAL NOT NULL DEFAULT 0.5,
  expires_at TEXT,
  source_message_id INTEGER,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (source_message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS mood_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  mood TEXT NOT NULL DEFAULT 'idle',
  energy REAL NOT NULL DEFAULT 0.5,
  annoyance REAL NOT NULL DEFAULT 0.2,
  boredom REAL NOT NULL DEFAULT 0.2,
  worry REAL NOT NULL DEFAULT 0.2,
  trust REAL NOT NULL DEFAULT 0.5,
  loneliness REAL NOT NULL DEFAULT 0.3,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS relationship_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  trust REAL NOT NULL DEFAULT 0.5,
  closeness REAL NOT NULL DEFAULT 0.2,
  familiarity REAL NOT NULL DEFAULT 0.0,
  tension REAL NOT NULL DEFAULT 0.0,
  last_meaningful_interaction_at TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS reminders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  due_at TEXT,
  title TEXT NOT NULL,
  details TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending',
  source_message_id INTEGER,
  FOREIGN KEY (source_message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS file_access_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  operation TEXT NOT NULL,
  requested_path TEXT NOT NULL,
  resolved_path TEXT NOT NULL,
  allowed INTEGER NOT NULL,
  reason TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories(updated_at);
CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status);
"""
