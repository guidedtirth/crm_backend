const { v4: uuidv4 } = require('uuid');
const axios = require('axios');
const OpenAI = require('openai');
const db = require('../db');
const { getAssistantId, initializeAssistant } = require('../assistant');

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
let tablesReady = false;

async function ensureTables() {
  if (tablesReady) return;
  await db.query(`
    CREATE TABLE IF NOT EXISTS profile_chat_threads (
      id UUID PRIMARY KEY,
      profile_id UUID NOT NULL,
      thread_id TEXT NOT NULL,
      title TEXT,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
  `);
  await db.query(`
    CREATE INDEX IF NOT EXISTS idx_profile_chat_threads_profile ON profile_chat_threads(profile_id);
  `);
  await db.query(`
    CREATE UNIQUE INDEX IF NOT EXISTS uq_profile_chat_thread_latest ON profile_chat_threads(profile_id, thread_id);
  `);
  await db.query(`
    CREATE TABLE IF NOT EXISTS profile_chat_messages (
      id UUID PRIMARY KEY,
      profile_id UUID NOT NULL,
      thread_id TEXT NOT NULL,
      role TEXT NOT NULL CHECK (role IN ('user','assistant')),
      content TEXT,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
  `);
  await db.query(`
    CREATE INDEX IF NOT EXISTS idx_profile_chat_messages_thread ON profile_chat_messages(thread_id, created_at);
  `);
  // Add encrypted columns if missing and relax NOT NULL on content for encrypted-only writes
  try { await db.query("ALTER TABLE profile_chat_messages ADD COLUMN IF NOT EXISTS content_enc TEXT"); } catch (e) {}
  try { await db.query("ALTER TABLE profile_chat_messages ADD COLUMN IF NOT EXISTS content_nonce TEXT"); } catch (e) {}
  try { await db.query("ALTER TABLE profile_chat_messages ADD COLUMN IF NOT EXISTS content_salt TEXT"); } catch (e) {}
  try { await db.query("ALTER TABLE profile_chat_messages ALTER COLUMN content DROP NOT NULL"); } catch (e) {}
  tablesReady = true;
}

async function ensureAssistant() {
  if (getAssistantId()) return getAssistantId();
  const id = await initializeAssistant();
  return id;
}

async function pollRun(threadId, runId) {
  let run = { id: runId, status: 'queued' };
  let attempts = 0;
  while (run.status !== 'completed') {
    attempts += 1;
    await new Promise(r => setTimeout(r, 800));
    const url = `https://api.openai.com/v1/threads/${threadId}/runs/${runId}`;
    const resp = await axios.get(url, {
      headers: {
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
        'Content-Type': 'application/json',
        'OpenAI-Beta': 'assistants=v2'
      },
      timeout: 15000
    });
    run = resp.data;
    if (['failed','cancelled','expired'].includes(run.status)) {
      throw new Error(`Assistant run ${run.status}: ${run.last_error?.message || 'unknown'}`);
    }
    if (attempts > 40) throw new Error('Polling timeout');
  }
}

module.exports = {
  startChat: async (req, res) => {
    try {
      await ensureTables();
      const assistantId = await ensureAssistant();
      const { profileId } = req.params;
      const title = req.body?.title || null;

      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      if (!uuidRegex.test(profileId)) return res.status(400).json({ error: 'Invalid profileId' });

      // Reuse existing thread if any
      const existing = await db.query('SELECT thread_id FROM profile_chat_threads WHERE profile_id = $1 ORDER BY created_at DESC LIMIT 1', [profileId]);
      if (existing.rows.length > 0) {
        return res.json({ thread_id: existing.rows[0].thread_id });
      }

      const thread = await openai.beta.threads.create();
      const id = uuidv4();
      await db.query(
        'INSERT INTO profile_chat_threads (id, profile_id, thread_id, title) VALUES ($1, $2, $3, $4)',
        [id, profileId, thread.id, title]
      );
      return res.json({ thread_id: thread.id });
    } catch (err) {
      console.error('startChat error:', err);
      return res.status(500).json({ error: err.message });
    }
  },

  getHistory: async (req, res) => {
    try {
      await ensureTables();
      const { profileId } = req.params;
      const rows = await db.query('SELECT thread_id FROM profile_chat_threads WHERE profile_id = $1 ORDER BY created_at DESC LIMIT 1', [profileId]);
      if (rows.rows.length === 0) return res.json({ thread_id: null, messages: [] });
      const threadId = rows.rows[0].thread_id;
      const msgs = await db.query('SELECT id, role, content, content_enc, content_nonce, content_salt, created_at FROM profile_chat_messages WHERE profile_id = $1 AND thread_id = $2 ORDER BY created_at ASC', [profileId, threadId]);
      return res.json({ thread_id: threadId, messages: msgs.rows });
    } catch (err) {
      console.error('getHistory error:', err);
      return res.status(500).json({ error: err.message });
    }
  },

  postMessage: async (req, res) => {
    try {
      await ensureTables();
      const assistantId = await ensureAssistant();
      const { threadId } = req.params;
      const { profileId, content } = req.body || {};
      if (!threadId || !profileId || !content) return res.status(400).json({ error: 'threadId, profileId and content are required' });

      // Ensure thread exists record for profile
      const thr = await db.query('SELECT 1 FROM profile_chat_threads WHERE profile_id = $1 AND thread_id = $2 LIMIT 1', [profileId, threadId]);
      if (thr.rows.length === 0) {
        const id = uuidv4();
        await db.query('INSERT INTO profile_chat_threads (id, profile_id, thread_id) VALUES ($1, $2, $3)', [id, profileId, threadId]);
      }

      // Append user message to assistant thread
      await openai.beta.threads.messages.create(threadId, { role: 'user', content });
      const run = await openai.beta.threads.runs.create(threadId, { assistant_id: assistantId });
      await pollRun(threadId, run.id);

      // Retrieve latest assistant message
      const messages = await openai.beta.threads.messages.list(threadId, { limit: 2, order: 'desc' });
      const latest = messages.data[0];
      const assistantText = latest?.content?.[0]?.text?.value || '';

      const userMsgId = uuidv4();
      const asstMsgId = uuidv4();
      // Do not persist plaintext: store NULL; client saves encrypted copy via /encrypted
      await db.query('INSERT INTO profile_chat_messages (id, profile_id, thread_id, role, content) VALUES ($1, $2, $3, $4, NULL)', [userMsgId, profileId, threadId, 'user']);
      await db.query('INSERT INTO profile_chat_messages (id, profile_id, thread_id, role, content) VALUES ($1, $2, $3, $4, NULL)', [asstMsgId, profileId, threadId, 'assistant']);
      await db.query('UPDATE profile_chat_threads SET updated_at = NOW() WHERE thread_id = $1', [threadId]);

      return res.json({ thread_id: threadId, messages: [
        { id: userMsgId, role: 'user', content, created_at: new Date().toISOString() },
        { id: asstMsgId, role: 'assistant', content: assistantText, created_at: new Date().toISOString() }
      ]});
    } catch (err) {
      console.error('postMessage error:', err);
      return res.status(500).json({ error: err.message });
    }
  }
};

// Edit a user message: truncate following messages, rebuild a fresh thread, replay user messages up to edited one, and regenerate assistant reply
module.exports.editMessage = async (req, res) => {
  try {
    await ensureTables();
    const assistantId = await ensureAssistant();
    const { messageId } = req.params;
    const { profileId, content } = req.body || {};
    if (!messageId || !profileId || !content) return res.status(400).json({ error: 'messageId, profileId and content are required' });

    // Reject optimistic temporary IDs like tmp_...
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(String(messageId))) {
      return res.status(400).json({ error: 'Invalid messageId format' });
    }

    // Load the message
    const msgRes = await db.query('SELECT id, profile_id, thread_id, role, content, created_at FROM profile_chat_messages WHERE id = $1 AND profile_id = $2', [messageId, profileId]);
    if (msgRes.rows.length === 0) return res.status(404).json({ error: 'Message not found' });
    const target = msgRes.rows[0];
    if (target.role !== 'user') return res.status(400).json({ error: 'Only user messages can be edited' });

    // Delete all following messages in this thread
    await db.query('DELETE FROM profile_chat_messages WHERE profile_id = $1 AND thread_id = $2 AND created_at > $3', [profileId, target.thread_id, target.created_at]);
    // Do not keep plaintext for the edited message
    await db.query('UPDATE profile_chat_messages SET content = NULL WHERE id = $1', [messageId]);

    // Fetch remaining messages up to and including edited one (chronological)
    const hist = await db.query('SELECT id, role, content, created_at FROM profile_chat_messages WHERE profile_id = $1 AND thread_id = $2 ORDER BY created_at ASC', [profileId, target.thread_id]);

    // Create a fresh OpenAI thread and remap this profile to it
    const thread = await openai.beta.threads.create();
    const oldThreadId = target.thread_id;
    await db.query('UPDATE profile_chat_threads SET thread_id = $1, updated_at = NOW() WHERE profile_id = $2', [thread.id, profileId]);

    // Migrate kept messages in DB to the new thread id so UI history stays continuous
    await db.query('UPDATE profile_chat_messages SET thread_id = $1 WHERE profile_id = $2 AND thread_id = $3', [thread.id, profileId, oldThreadId]);

    // Safety: ensure the edited user message exists under the new thread id
    await db.query(
      'INSERT INTO profile_chat_messages (id, profile_id, thread_id, role, content) VALUES ($1, $2, $3, $4, NULL) ON CONFLICT (id) DO NOTHING',
      [messageId, profileId, thread.id, 'user']
    );

    // Replay only user messages into the new OpenAI thread so the assistant has context
    for (const m of hist.rows) {
      if (m.role === 'user') {
        await openai.beta.threads.messages.create(thread.id, { role: 'user', content: m.content });
      }
    }

    // After editing, regenerate assistant reply for the last user message
    const run = await openai.beta.threads.runs.create(thread.id, { assistant_id: assistantId });
    await pollRun(thread.id, run.id);
    const messages = await openai.beta.threads.messages.list(thread.id, { limit: 1, order: 'desc' });
    const assistantText = messages.data[0]?.content?.[0]?.text?.value || '';

    // Persist the assistant reply under the new thread id
    const asstMsgId = uuidv4();
    await db.query('INSERT INTO profile_chat_messages (id, profile_id, thread_id, role, content) VALUES ($1, $2, $3, $4, NULL)', [asstMsgId, profileId, thread.id, 'assistant']);

    // Return updated thread id and full message history (now migrated)
    const newHist = await db.query('SELECT id, role, content, created_at FROM profile_chat_messages WHERE profile_id = $1 AND thread_id = $2 ORDER BY created_at ASC', [profileId, thread.id]);
    return res.json({ thread_id: thread.id, messages: newHist.rows });
  } catch (err) {
    console.error('editMessage error:', err);
    return res.status(500).json({ error: err.message });
  }
};

// Save or update encrypted message copies (client-side encrypted)
module.exports.saveEncrypted = async (req, res) => {
  try {
    await ensureTables();
    const { items } = req.body || {};
    if (!Array.isArray(items) || items.length === 0) return res.status(400).json({ error: 'items array required' });

    for (const it of items) {
      const { id, profile_id, thread_id, role, content_enc, content_nonce, content_salt, created_at } = it || {};
      if (!id || !profile_id || !thread_id || !role || !content_enc || !content_nonce) continue;
      // Try update existing row by id
      const upd = await db.query(
        'UPDATE profile_chat_messages SET content = NULL, content_enc = $1, content_nonce = $2, content_salt = $3 WHERE id = $4 AND profile_id = $5 RETURNING id',
        [content_enc, content_nonce, content_salt || null, id, profile_id]
      );
      if (upd.rowCount === 0) {
        await db.query(
          'INSERT INTO profile_chat_messages (id, profile_id, thread_id, role, content, content_enc, content_nonce, content_salt, created_at) VALUES ($1, $2, $3, $4, NULL, $5, $6, $7, COALESCE($8, NOW()))',
          [id, profile_id, thread_id, role, content_enc, content_nonce, content_salt || null, created_at || null]
        );
      }
    }

    return res.json({ ok: true });
  } catch (err) {
    console.error('saveEncrypted error:', err);
    return res.status(500).json({ error: err.message });
  }
};


