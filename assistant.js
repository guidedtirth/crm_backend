const { v4: uuidv4 } = require('uuid');
const path = require('path');
const fs = require('fs').promises;
const OpenAI = require('openai');
require('dotenv').config();

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const configPath = path.join(__dirname, 'assistant_config.json');
const PYTHON_EXECUTABLE = process.platform === 'win32'
  ? path.join(__dirname, '.venv', 'Scripts', 'python.exe') // Windows
  : path.join(__dirname, '.venv', 'bin', 'python3');

let assistantId = null;

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
        instructions: "You are an expert in generating professional job proposals...", // Your existing instructions
        model: "gpt-4-turbo",
        tools: []
      });
      config.assistantId = assistant.id;
      await fs.writeFile(configPath, JSON.stringify(config, null, 2));
      console.log(`Created Assistant with ID: ${assistant.id}`);
    } else {
      await openai.beta.assistants.retrieve(config.assistantId);
      console.log(`Using existing Assistant ID: ${config.assistantId}`);
    }
    assistantId = config.assistantId;
    return assistantId;
  } catch (err) {
    console.error('Assistant initialization error:', err);
    throw err;
  }
}

function getAssistantId() {
  return assistantId;
}

// Verify Python executable exists
fs.access(PYTHON_EXECUTABLE).catch(() => {
  console.error(`Python executable not found at ${PYTHON_EXECUTABLE}`);
  process.exit(1);
});

module.exports = {
  initializeAssistant,
  getAssistantId,
  PYTHON_EXECUTABLE
};
