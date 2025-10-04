/**
 * Query Controller
 * Proposal generation/refinement endpoints (initial + feedback paths).
 */
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const { getAssistantId } = require('../assistant');
const pool = require('../db');
const pdfParse = require('pdf-parse');
const OpenAI = require('openai');
const { summarizeJobForPrompt } = require('../platforms/upwork/utils');
const axios = require('axios'); // Added for raw HTTP call

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

/** Cosine similarity helper for embedding arrays */
function cosineSimilarity(a, b) {
  if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return 0;
  let dot = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < a.length; i++) {
    const x = a[i];
    const y = b[i];
    dot += x * y;
    normA += x * x;
    normB += y * y;
  }
  if (normA === 0 || normB === 0) return 0;
  return dot / (Math.sqrt(normA) * Math.sqrt(normB));
}

/**
 * Use Assistants API to generate a proposal, given text inputs.
 * Returns { proposal, threadId }.
 */
async function generateAssistantProposal({ profileContent, queryText, budgetMin, budgetMax, threadId, assistantId, feedback, profileName }) {
  const messageContent = [
    `Evaluate fit strictly. Use ONLY the Profile text and Job Summary below.`,
    `Return only the proposal text if it is a strong fit; otherwise return a very short explanation why not.`,
    `PROFILE_START`,
    String(profileContent || '').slice(0, 3000),
    `PROFILE_END`,
    `JOB_SUMMARY_START`,
    queryText,
    `Budget Range: $${budgetMin}-${budgetMax}`,
    feedback ? `Feedback: ${feedback}` : null,
    `JOB_SUMMARY_END`,
    `FORMAT_START`,
    `Hi,`,
    `One short sentence connecting my background to the role.`,
    `RELEVANT EXPERIENCE:`,
    `1. Point one (concise, to the point)`,
    `2. Point two`,
    `APPROACH:`,
    `1. Step one`,
    `2. Step two`,
    `ESTIMATE & NEXT STEPS:`,
    `- Timeline and suggestion to schedule a call`,
    `Best regards,`,
    String(profileName || 'Candidate'),
    `FORMAT_END`
  ].filter(Boolean).join('\n');

  let thread;
  if (threadId) {
    thread = await openai.beta.threads.retrieve(threadId);
  } else {
    thread = await openai.beta.threads.create();
  }
  console.log('Thread ID:', thread.id); // Debug log

  await openai.beta.threads.messages.create(thread.id, {
    role: 'user',
    content: messageContent
  });

  let run = await openai.beta.threads.runs.create(thread.id, {
    assistant_id: assistantId
  });
  console.log('Run ID:', run.id); // Debug log

  let pollCount = 0;
  while (run.status !== 'completed') {
    pollCount++;
    console.log(`Polling attempt ${pollCount}: Status = ${run.status}`);
    await new Promise(r => setTimeout(r, 800));

    // Validate IDs before API call
    if (!thread.id || !run.id) {
      throw new Error(`Invalid thread or run ID: thread_id=${thread.id}, run_id=${run.id}`);
    }

    // Raw Axios call to bypass SDK bug
    const apiUrl = `https://api.openai.com/v1/threads/${thread.id}/runs/${run.id}`;
    console.log('DEBUG: Axios URL being called:', apiUrl);
    try {
      const response = await axios.get(apiUrl, {
        headers: {
          Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
          'Content-Type': 'application/json',
          'OpenAI-Beta': 'assistants=v2' // Required for Assistants API v2
        },
        timeout: 10000
      });
      run = response.data; // Update run object
      console.log(`Retrieved run status: ${run.status}`);
    } catch (err) {
      if (err.response) {
        console.error('DEBUG: Axios error response:', err.response.data);
        throw new Error(`Axios API error: ${err.response.status} - ${JSON.stringify(err.response.data)}`);
      }
      throw err;
    }

    if (['failed', 'cancelled', 'expired'].includes(run.status)) {
      throw new Error(`Assistant run ${run.status}: ${run.last_error?.message || 'Unknown error'}`);
    }
    if (pollCount > 30) {
      throw new Error('Polling timeout - run not completing');
    }
  }

  const messages = await openai.beta.threads.messages.list(thread.id, {
    limit: 1,
    order: 'desc'
  });
  const responseMessage = messages.data[0];
  const proposal = responseMessage?.content?.[0]?.text?.value || '';
  return { proposal, threadId: thread.id };
}

module.exports = {
  processQuery: async (req, res) => {
    try {
      const assistantId = getAssistantId();
      if (!assistantId) {
        throw new Error('Assistant not initialized');
      }

      const companyId = req.user?.company_id;
      if (!companyId) return res.status(401).json({ error: 'Missing company scope' });

      const queryData = req.body.query || {};
      const title = queryData.title || '';
      const description = queryData.description || '';
      const skills = Array.isArray(queryData.skills) ? queryData.skills : [];
      const budgetMin = Number(queryData.budgetMin || 0);
      const budgetMax = Number(queryData.budgetMax || 1000);
      const feedback = queryData.feedback || null;
      const threadId = queryData.thread_id || null;
      const jobIdFromBody = queryData.job_id || null; // optional: upwork_jobs.id
      const profileIdFromBody = queryData.profile_id || null;

      const queryTextForEmbedding = `${typeof title === 'string' ? title : JSON.stringify(title)} ${description} ${skills.join(' ')}`.trim();
      // Also build a compact job summary string for prompting (if full job object is provided later we can swap to summarizeJobForPrompt)
      const jobSummaryString = JSON.stringify({ title, description: String(description).slice(0,700), skills: (skills || []).slice(0,8) });

      const nowIso = new Date().toISOString();

      if (feedback && threadId && profileIdFromBody) {
        // Refinement path using existing thread and selected profile
        const profileRes = await pool.query('SELECT name, content FROM profiles WHERE id = $1 AND company_id = $2', [profileIdFromBody, companyId]);
        if (profileRes.rows.length === 0) {
          return res.json({ result: [{ relevance: 'No', score: 0, proposal: 'Profile not found.', thread_id: threadId, created_at: nowIso }] });
        }
      const profileName = profileRes.rows[0].name;
        const profileContent = profileRes.rows[0].content || '';

        const { proposal, threadId: ensuredThreadId } = await generateAssistantProposal({
          profileContent,
          queryText: jobSummaryString,
          budgetMin,
          budgetMax,
          threadId,
          assistantId,
          feedback,
          profileName
        });

        // Preserve the original match score for this thread so lists don't jump to 100%
        let scoreToPersist = 100;
        try {
          const s = await pool.query('SELECT score FROM proposal_feedback WHERE thread_id = $1 ORDER BY created_at ASC LIMIT 1', [ensuredThreadId]);
          if (s.rows.length > 0 && Number.isFinite(Number(s.rows[0].score))) {
            scoreToPersist = Number(s.rows[0].score);
          }
        } catch (e) {
          // fall back to default 100 if anything goes wrong
        }

        const feedbackId = uuidv4();
        // Create a fresh thread for the saved proposal; fallback to refinement thread if creation fails
        let saveThreadId = null;
        try {
          const t = await openai.beta.threads.create();
          saveThreadId = t.id;
          await openai.beta.threads.messages.create(saveThreadId, { role: 'assistant', content: proposal });
        } catch (_) { saveThreadId = ensuredThreadId; }
        if (jobIdFromBody) {
          await pool.query(
            'INSERT INTO proposal_feedback (id, profile_id, job_id, query_text, feedback, proposal, thread_id, score, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())',
            [feedbackId, profileIdFromBody, jobIdFromBody, JSON.stringify({ id: jobIdFromBody, title }), feedback, proposal, saveThreadId, scoreToPersist]
          );
        } else {
          await pool.query(
            'INSERT INTO proposal_feedback (id, profile_id, job_id, query_text, feedback, proposal, thread_id, score, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())',
            [feedbackId, profileIdFromBody, null, JSON.stringify({ id: null, title }), feedback, proposal, saveThreadId, scoreToPersist]
          );
        }

        return res.json({
          result: [
            {
              relevance: 'Yes',
              score: scoreToPersist,
              proposal,
              profile_id: profileIdFromBody,
              profile_name: profileName,
              thread_id: ensuredThreadId,
              created_at: nowIso
            }
          ]
        });
      }

      // Initial proposal path: find best profile via embeddings
      const embeddingResp = await openai.embeddings.create({
        input: queryTextForEmbedding,
        model: 'text-embedding-3-small'
      });
      const queryEmbedding = embeddingResp.data[0].embedding;

      const embRes = await pool.query(`
        SELECT e.profile_id, e.chunk, e.embedding
        FROM embeddings e
        JOIN profiles p ON p.id = e.profile_id
        WHERE p.company_id = $1
      `, [companyId]);
      let highestScore = -1;
      let bestProfileId = null;
      const relevantChunks = [];

      for (const row of embRes.rows) {
        const profileId = row.profile_id;
        const chunk = row.chunk;
        const embeddingJson = row.embedding;
        const embedding = Array.isArray(embeddingJson) ? embeddingJson : JSON.parse(embeddingJson);
        const score = cosineSimilarity(queryEmbedding, embedding);
        if (score > highestScore) {
          highestScore = score;
          bestProfileId = profileId;
        }
        if (score > 0.7) {
          relevantChunks.push(chunk);
        }
      }

      // Enforce minimum relevance: skip proposal generation if score < 80%
      if (!bestProfileId || highestScore < 0.8) {
        return res.json({ result: [{ relevance: 'No', score: Math.max(0, Math.floor(highestScore * 100)), proposal: 'No sufficiently relevant profile (>=80) to generate a proposal.', thread_id: null, created_at: nowIso }] });
      }

      const profRes = await pool.query('SELECT name, content FROM profiles WHERE id = $1 AND company_id = $2', [bestProfileId, companyId]);
      if (profRes.rows.length === 0) {
        return res.json({ result: [{ relevance: 'No', score: 0, proposal: 'Profile not found.', thread_id: null, created_at: nowIso }] });
      }
        const profileName = profRes.rows[0].name;
      const profileContent = (profRes.rows[0].content || '') + (relevantChunks.length ? ('\n\n' + relevantChunks.join('\n')) : '');

      const { proposal, threadId: newThreadId } = await generateAssistantProposal({
        profileContent,
        queryText: jobSummaryString,
        budgetMin,
        budgetMax,
        threadId: null,
        assistantId,
        feedback: null,
        profileName
      });

      const feedbackId = uuidv4();
      // Create a fresh thread for the saved proposal; fallback to evaluation thread if creation fails
      let saveThreadId = null;
      try {
        const t = await openai.beta.threads.create();
        saveThreadId = t.id;
        await openai.beta.threads.messages.create(saveThreadId, { role: 'assistant', content: proposal });
      } catch (_) { saveThreadId = newThreadId; }
      if (jobIdFromBody) {
        await pool.query(
          'INSERT INTO proposal_feedback (id, profile_id, job_id, query_text, feedback, proposal, thread_id, score, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())',
          [feedbackId, bestProfileId, jobIdFromBody, JSON.stringify({ id: jobIdFromBody, title }), null, proposal, saveThreadId, Math.floor(highestScore * 100)]
        );
      } else {
        await pool.query(
          'INSERT INTO proposal_feedback (id, profile_id, job_id, query_text, feedback, proposal, thread_id, score, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())',
          [feedbackId, bestProfileId, null, JSON.stringify({ id: null, title }), null, proposal, saveThreadId, Math.floor(highestScore * 100)]
        );
      }

      return res.json({
        result: [
          {
            relevance: 'Yes',
            score: Math.floor(highestScore * 100),
            proposal,
            profile_id: bestProfileId,
            profile_name: profileName,
            thread_id: newThreadId,
            created_at: nowIso
          }
        ]
      });
    } catch (err) {
      console.error('Query error:', err);
      res.status(500).json({ error: err.message });
    }
  },

  trainProfile: async (req, res) => {
    try {
      const assistantId = getAssistantId();
      if (!assistantId) {
        throw new Error('Assistant not initialized');
      }

      const { profileId } = req.params;
      const file = (Array.isArray(req.files) && req.files.length > 0) ? req.files[0] : req.file;

      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      if (!uuidRegex.test(profileId)) {
        return res.status(400).json({ error: 'Invalid profileId format' });
      }
      if (!file) {
        return res.status(400).json({ error: 'File required' });
      }

      const filePath = path.join(__dirname, '../Uploads', `${profileId}_${file.originalname}`);
      await fs.rename(file.path, filePath);

      let newContent = '';
      const ext = path.extname(filePath).toLowerCase();
      try {
        if (ext === '.pdf') {
          const dataBuffer = await fs.readFile(filePath);
          const pdfData = await pdfParse(dataBuffer);
          newContent = (pdfData.text || '').trim();
        } else if (ext === '.docx') {
          const mammoth = require('mammoth');
          const result = await mammoth.extractRawText({ path: filePath });
          newContent = (result.value || '').trim();
        } else if (ext === '.txt') {
          newContent = (await fs.readFile(filePath, 'utf8')).trim();
        } else {
          return res.status(400).json({ error: 'Unsupported file type' });
        }
      } catch (parseErr) {
        return res.status(400).json({ error: 'Unable to extract text from file', details: parseErr.message });
      }

      // Update profiles table: append content, set assistant_id, update training_file metadata
      const profileRow = await pool.query('SELECT content, training_file FROM profiles WHERE id = $1', [profileId]);
      const existingContent = profileRow.rows[0]?.content || '';
      const updatedContent = existingContent ? `${existingContent}\n${newContent}` : newContent;

      let trainingFileData = Array.isArray(profileRow.rows[0]?.training_file) ? profileRow.rows[0].training_file : [];
      trainingFileData.push({
        name: file.originalname,
        path: filePath,
        size: file.size,
        type: file.mimetype,
        processed: true
      });

      await pool.query(
        'UPDATE profiles SET content = $1, assistant_id = $2, last_updated = CURRENT_TIMESTAMP, training_file = $3::jsonb WHERE id = $4',
        [updatedContent, assistantId, JSON.stringify(trainingFileData), profileId]
      );

      // Chunk new content and generate embeddings
      function chunkText(text, maxLength = 500) {
        const words = text.split(/\s+/);
        const chunks = [];
        let current = [];
        let length = 0;
        for (const w of words) {
          const wl = w.length + 1;
          if (length + wl > maxLength) {
            if (current.length) chunks.push(current.join(' '));
            current = [w];
            length = wl;
          } else {
            current.push(w);
            length += wl;
          }
        }
        if (current.length) chunks.push(current.join(' '));
        return chunks.filter(Boolean);
      }

      const textChunks = chunkText(newContent);
      for (const chunk of textChunks) {
        const embResp = await openai.embeddings.create({ input: chunk, model: 'text-embedding-3-small' });
        const embedding = embResp.data[0].embedding;
        await pool.query(
          'INSERT INTO embeddings (profile_id, chunk, embedding) VALUES ($1, $2, $3)',
          [profileId, chunk, JSON.stringify(embedding)]
        );
      }

      return res.json({ message: 'Profile trained successfully' });
    } catch (err) {
      console.error('Training error:', err);
      res.status(500).json({ error: 'Training failed', details: err.message });
    }
  }
};