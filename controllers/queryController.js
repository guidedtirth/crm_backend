const path = require("path");
const util = require("util");
const exec = util.promisify(require("child_process").exec);

exports.queryOpenAI = async (req, res) => {
  const { query } = req.body;
  if (!query) return res.status(400).json({ error: "Query is required" });

  try {
    const pythonPath = path.join(__dirname, "..", "venv", "Scripts", "python.exe");
    const scriptPath = path.join(__dirname, "..", "query_openai.py");
    const { stdout } = await exec(`"${pythonPath}" "${scriptPath}" "${query.replace(/"/g, '\\"')}"`);
    const lines = stdout.trim().split("\n");
    const result = lines.reverse().find(line => line.trim()) || "No response received";
    res.json({ result });
  } catch (err) {
    console.error("Query error:", err.message);
    res.status(500).json({ error: "Error executing query", details: err.message });
  }
};
