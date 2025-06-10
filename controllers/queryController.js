const { exec } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const { getAssistantId, PYTHON_EXECUTABLE } = require('../assistant');
const pool = require('../db');
const pdfParse = require('pdf-parse');
const util = require('util');

const execPromise = util.promisify(exec);

module.exports = {
  processQuery: async (req, res) => {
    try {
      const assistantId = getAssistantId();
      if (!assistantId) {
        throw new Error('Assistant not initialized');
      }

      const queryData = req.body.query;
      queryData.assistantId = assistantId;

      const queryFile = path.join(__dirname, `../temp/query_${uuidv4()}.json`);
      await fs.writeFile(queryFile, JSON.stringify(queryData));

      const command = `"${PYTHON_EXECUTABLE}" query_assistant.py "${queryFile}"`;

      exec(command, async (error, stdout, stderr) => {
        try {
          if (error) {
            throw new Error(stderr || error.message);
          }

          const result = JSON.parse(stdout);
          // await fs.unlink(queryFile);
          res.json({ result });
        } catch (err) {
          console.error('Query processing error:', err);
          res.status(500).json({ error: err.message });
        }
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
      const pdfFile = req.file;

      // Validate profileId
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      if (!uuidRegex.test(profileId)) {
        return res.status(400).json({ error: 'Invalid profileId format' });
      }

      if (!pdfFile) {
        return res.status(400).json({ error: 'PDF file required' });
      }

      // Process PDF
      const filePath = path.join(__dirname, '../Uploads', `${profileId}_${pdfFile.originalname}`);
      await fs.rename(pdfFile.path, filePath);

      const dataBuffer = await fs.readFile(filePath);
      const pdfData = await pdfParse(dataBuffer);
      const content = pdfData.text;

      // Save to temp file
      const tempDir = path.join(__dirname, '../temp');
      await fs.mkdir(tempDir, { recursive: true });
      const tempContentFile = path.join(tempDir, `${uuidv4()}.txt`);
      await fs.writeFile(tempContentFile, content);

      const result = await pool.query('SELECT training_file FROM profiles WHERE id = $1', [profileId]);
      let trainingFileData = [];
      if (result.rows.length > 0 && result.rows[0].training_file) {
        trainingFileData = result.rows[0].training_file;
      }
      trainingFileData.push({
        name: pdfFile.originalname,
        path: filePath,
        size: pdfFile.size,
        type: pdfFile.mimetype,
        processed: true
      });


      await pool.query(
        'UPDATE profiles SET training_file = $1::jsonb WHERE id = $2',
        [JSON.stringify(trainingFileData), profileId]
      );

      // Execute training
      const command = `"${PYTHON_EXECUTABLE}" train_profile.py "${profileId}" "${tempContentFile}" "${pdfFile.originalname}" "${assistantId}"`;

      const { stdout, stderr } = await execPromise(command, { maxBuffer: 1024 * 1024 });

      if (stderr && (stderr.includes('Error:') || stderr.includes('Exception'))) {
        throw new Error(`Training script failed: ${stderr}`);
      }

      await fs.unlink(tempContentFile).catch(console.warn);

      res.json({ message: 'Profile trained successfully' });
    } catch (err) {
      console.error('Training error:', err);
      res.status(500).json({ error: 'Training failed', details: err.message });
    }
  }
};