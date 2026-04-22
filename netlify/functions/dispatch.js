// netlify/functions/dispatch.js
// Triggers the GitHub Actions "Refresh PCR Dashboard" workflow.
// Requires GITHUB_PAT env var set in Netlify (Site config → Env variables).

const https = require('https');

exports.handler = async () => {
  const token = process.env.GITHUB_PAT;
  if (!token) {
    return { statusCode: 500, body: 'GITHUB_PAT not configured' };
  }

  const payload = JSON.stringify({ ref: 'main' });
  const options = {
    hostname: 'api.github.com',
    path: '/repos/omartarabichi/pcr-dashboard/actions/workflows/refresh.yml/dispatches',
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'PCR-Dashboard-Netlify-Function',
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload),
    },
  };

  return new Promise((resolve) => {
    const req = https.request(options, (res) => {
      resolve({
        statusCode: 204,
        headers: { 'Access-Control-Allow-Origin': '*' },
        body: '',
      });
    });
    req.on('error', (e) => {
      resolve({ statusCode: 500, body: `Request failed: ${e.message}` });
    });
    req.write(payload);
    req.end();
  });
};
