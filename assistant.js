const { v4: uuidv4 } = require('uuid');
const path = require('path');
const fs = require('fs').promises;
const OpenAI = require('openai');
require('dotenv').config();

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const configPath = path.join(__dirname, 'assistant_config.json');

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
        instructions: "You are an expert in generating professional job proposals...",
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

module.exports = {
  initializeAssistant,
  getAssistantId
};
