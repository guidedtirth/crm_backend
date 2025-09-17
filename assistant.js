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

    const generalInstructions = [
      "You are a helpful, knowledgeable general AI assistant.",
      "Provide accurate, concise answers by default; expand with step-by-step detail when helpful.",
      "Ask clarifying questions when requirements are ambiguous; do not assume missing facts.",
      "For code requests, return clear, minimal examples and mention important caveats.",
      "Be professional and neutral; avoid unsafe or sensitive actions."
    ].join(' ');

    if (!config.assistantId) {
      const assistant = await openai.beta.assistants.create({
        name: `GeneralAssistant_${uuidv4()}`,
        instructions: generalInstructions,
        model: "gpt-4o-mini",
        tools: []
      });
      config.assistantId = assistant.id;
      await fs.writeFile(configPath, JSON.stringify(config, null, 2));
      console.log(`Created Assistant with ID: ${assistant.id}`);
    } else {
      // Update existing assistant to general-purpose
      await openai.beta.assistants.update(config.assistantId, {
        instructions: generalInstructions,
        model: "gpt-4o-mini"
      });
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
