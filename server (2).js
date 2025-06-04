
const express = require('express');
const multer = require('multer');
const { exec } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');
const OpenAI = require('openai');
const { Pool } = require('pg');
const pdfParse = require('pdf-parse');
const util = require('util');
require('dotenv').config();

const app = express();
const upload = multer({ dest: 'Uploads/' });
app.use(cors());
app.use(express.json());

if (!process.env.OPENAI_API_KEY) {
  console.error('Error: OPENAI_API_KEY is not set in .env file');
  process.exit(1);
}

const DB_CONFIG = {
  database: process.env.DB_NAME || 'profiledb',
  user: process.env.DB_USER || 'profile',
  password: process.env.DB_PASSWORD || 'profileUYh$13#',
  host: process.env.DB_HOST || '122.176.158.168',
  port: process.env.DB_PORT || '5432',
  ssl: { rejectUnauthorized: false }
};

const pool = new Pool(DB_CONFIG);

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const configPath = path.join(__dirname, 'assistant_config.json');
const PYTHON_EXECUTABLE = path.join(__dirname, 'venv', 'Scripts', 'python.exe');

fs.access(PYTHON_EXECUTABLE)
  .catch(() => {
    console.error(`Error: Python executable not found at ${PYTHON_EXECUTABLE}`);
    process.exit(1);
  });

async function initializeAssistant() {
  try {
    let config = {};
    try {
      const configData = await fs.readFile(configPath, 'utf-8');
      config = JSON.parse(configData);
    } catch (err) {
      console.log('No assistant config found, creating new Assistant');
    }

    if (!config.assistantId) {
      const assistant = await openai.beta.assistants.create({
        name: `ProfileMatchingAssistant_${uuidv4()}`,
        instructions: "You are an expert in generating professional job proposals for technical roles, including full stack development, AI, automation, and project management. Given a job description, a candidate's profile, and optional feedback, create a tailored job proposal in plain text format . Do not use any markdown symbols (e.g., #, *, **, -, >) in any part of the proposal, including headings, subheadings, lists, or emphasis. The proposal should include: (1) an introductory greeting addressing the hiring manager, (2) a section highlighting the candidate's relevant skills and experiences that align with the job requirements, (3) a proposed approach to deliver the job's key deliverables, addressing specific roles or tasks mentioned (e.g., full stack, AI, n8n), and (4) a closing statement expressing enthusiasm, availability, and a proposed rate within the job’s budget range. Use a professional yet engaging tone, and keep the proposal concise (500-600 words). Incorporate all feedback provided in the conversation history to improve the proposal, ensuring all suggestions are addressed. Format as: Job Proposal for [Job Title]\n\nDear Hiring Manager,\n\n Why I’m a Strong Fit\n...\n My Approach to Your Project\n...\nLet’s Connect\n...",
        model: "gpt-4o-mini",
        tools: []
      });
      config.assistantId = assistant.id;
      await fs.writeFile(configPath, JSON.stringify(config, null, 2));
      console.log(`Created Assistant with ID: ${assistant.id}`);
    } else {
      await openai.beta.assistants.retrieve(config.assistantId);
      console.log(`Using existing Assistant ID: ${config.assistantId}`);
    }
    return config.assistantId;
  } catch (err) {
    console.error('Assistant initialization error:', err);
    throw new Error('Failed to initialize Assistant');
  }
}

let assistantId = null;

initializeAssistant()
  .then(id => {
    assistantId = id;
  })
  .catch(err => {
    console.error('Server startup failed:', err);
    process.exit(1);
  });

app.get('/api/profiles', async (req, res) => {
  console.log('Handling GET /api/profiles');
  try {
    const result = await pool.query('SELECT id, name FROM profiles ORDER BY name');
    console.log(`Fetched ${result.rows.length} profiles`);
    res.json(result.rows);
  } catch (err) {
    console.error('Profile fetch error:', err);
    res.status(500).json({ error: 'Failed to fetch profiles', details: err.message });
  }
});

app.post('/api/profiles', async (req, res) => {
  try {
    const { name } = req.body;
    const id = uuidv4();
    await pool.query('INSERT INTO profiles (id, name) VALUES ($1, $2)', [id, name]);
    res.json({ id, name });
  } catch (error) {
    console.error('Profile add error:', error);
    res.status(500).json({ error: 'Failed to add profile', details: error.message });
  }
});

app.delete('/api/profiles/:id', async (req, res) => {
  try {
    const { id } = req.params;
    await pool.query('DELETE FROM profiles WHERE id = $1', [id]);
    res.status(200).send();
  } catch (error) {
    console.error('Profile delete error:', error);
    res.status(500).json({ error: 'Failed to delete profile', details: error.message });
  }
});

app.post('/query', async (req, res) => {
  try {
    if (!assistantId) {
      throw new Error('Assistant not initialized');
    }
    const queryData = req.body.query;
    queryData.assistantId = assistantId;
    const queryFile = path.join(__dirname, `query_${uuidv4()}.json`);
    await fs.writeFile(queryFile, JSON.stringify(queryData));

    const command = `"${PYTHON_EXECUTABLE}" query_assistant.py "${queryFile}"`;
    console.log(`Executing command: ${command}`);
    exec(command, async (error, stdout, stderr) => {
      try {
        if (error) {
          console.error('Python error:', stderr);
          throw new Error(stderr || error.message);
        }
        console.log('Python stdout:', stdout);
        console.log('Python stderr:', stderr);
        const result = JSON.parse(stdout);
        await fs.unlink(queryFile);
        res.json({ result });
      } catch (err) {
        console.error('Query processing error:', err);
        res.status(500).json({ error: err.message });
      }
    });
  } catch (error) {
    console.error('Query error:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/train/:profileId', upload.single('pdf'), async (req, res) => {
  console.log('Handling POST /train/:profileId:', req.params.profileId);
  try {
    const { profileId } = req.params;
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(profileId)) {
      console.warn(`Invalid profileId format: ${profileId}`);
      return res.status(400).json({ error: 'Invalid profileId format' });
    }

    const pdfFile = req.file;
    if (!pdfFile) {
      console.warn('PDF file missing in request');
      return res.status(400).json({ error: 'PDF file required' });
    }

    const filePath = path.join(__dirname, 'Uploads', `${profileId}_${pdfFile.originalname}`);
    await fs.rename(pdfFile.path, filePath);
    console.log(`Saved PDF to: ${filePath}`);

    const dataBuffer = await fs.readFile(filePath);
    const pdfData = await pdfParse(dataBuffer);
    const content = pdfData.text;
    console.log(`Extracted PDF content length: ${content.length} characters`);

    const tempContentFile = path.join(__dirname, 'temp', `${uuidv4()}.txt`);
    await fs.mkdir(path.dirname(tempContentFile), { recursive: true });
    await fs.writeFile(tempContentFile, content);
    console.log(`Saved content to temp file: ${tempContentFile}`);

    const trainingFileData = [{
      name: pdfFile.originalname,
      path: filePath,
      size: pdfFile.size,
      type: pdfFile.mimetype,
      processed: true
    }];
    await pool.query(
      'UPDATE profiles SET training_file = $1::jsonb WHERE id = $2',
      [JSON.stringify(trainingFileData), profileId]
    );
    console.log(`Updated profiles.training_file for profileId: ${profileId}`);

    const execPromise = util.promisify(exec);
    const command = `"${PYTHON_EXECUTABLE}" train_profile.py "${profileId}" "${tempContentFile}" "${pdfFile.originalname}"`;
    console.log(`Executing training command: ${command}`);
    const { stdout, stderr } = await execPromise(command, { maxBuffer: 1024 * 1024 });
    console.log(`Training stdout: ${stdout}`);
    if (stderr && (stderr.includes('Error:') || stderr.includes('Exception'))) {
      console.error('Training script failed:', stderr);
      throw new Error(`Training script failed: ${stderr}`);
    }

    await fs.unlink(tempContentFile).catch(err => console.warn(`Failed to delete temp file: ${tempContentFile}, ${err}`));
    console.log('Profile trained successfully');
    res.json({ message: 'Profile trained successfully' });
  } catch (err) {
    console.error('Training error:', err);
    res.status(500).json({ error: 'Training failed', details: err.message });
  }
});

app.listen(5000, () => console.log('Server running on port 5000'));

process.on('SIGTERM', async () => {
  console.log('Shutting down server');
  await pool.end();
  process.exit(0);
});