
const http = require('http');
const { spawn } = require('child_process');
const path = require('path');

const ROOT = __dirname;
const PORT = 3000;
const TOKEN = process.env.RUNNER_TOKEN;

if (!TOKEN) {
  console.error('Missing RUNNER_TOKEN environment variable.');
  process.exit(1);
}

let busy = false;

function run(command, args, timeoutMs = 600000) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: ROOT,
      windowsHide: true,
      shell: false,
      env: process.env,
    });

    let output = '';
    let finished = false;

    function collect(chunk) {
      output += chunk.toString();
      if (output.length > 200000) {
        output = output.slice(-200000);
      }
    }

    child.stdout.on('data', collect);
    child.stderr.on('data', collect);

    const timer = setTimeout(() => {
      child.kill();
      if (!finished) {
        finished = true;
        reject(new Error(
          `Timed out: ${command} ${args.join(' ')}\n${output}`
        ));
      }
    }, timeoutMs);

    child.on('error', (err) => {
      clearTimeout(timer);
      if (!finished) {
        finished = true;
        reject(new Error(`${err.message}\n${output}`));
      }
    });

    child.on('close', (code) => {
      clearTimeout(timer);
      if (finished) return;
      finished = true;

      if (code !== 0) {
        reject(new Error(
          `Process exited with code ${code}\n${output}`
        ));
      } else {
        resolve(output);
      }
    });
  });
}

const server = http.createServer(async (req, res) => {
  res.setHeader('Content-Type', 'application/json; charset=utf-8');

  if (req.method !== 'POST' || req.url !== '/run') {
    res.writeHead(404);
    return res.end(JSON.stringify({ error: 'Not found' }));
  }

  if (req.headers.authorization !== `Bearer ${TOKEN}`) {
    res.writeHead(401);
    return res.end(JSON.stringify({ error: 'Unauthorized' }));
  }

  if (busy) {
    res.writeHead(409);
    return res.end(JSON.stringify({ error: 'A run is already in progress' }));
  }

  busy = true;
  console.log('NPRA workflow started:', new Date().toISOString());

  try {
    const downloadLog = await run(
      process.execPath,
      [path.join(ROOT, 'src', 'scrape.js')]
    );

    const python = path.join(
      ROOT, '.venv', 'Scripts', 'python.exe'
    );

    const parseLog = await run(
      python,
      [path.join(ROOT, 'src', 'parse.py')]
    );

    res.writeHead(200);
    res.end(JSON.stringify({
      success: true,
      downloadLog,
      parseLog,
    }));
    console.log('NPRA workflow completed.');
  } catch (err) {
    console.error(err.message);
    res.writeHead(500);
    res.end(JSON.stringify({
      success: false,
      error: err.message,
    }));
  } finally {
    busy = false;
  }
});

// Listen on the host interfaces so Docker can reach this service.
// Protect the endpoint with the token and Windows Firewall.
server.listen(PORT, '0.0.0.0', () => {
  console.log(`NPRA runner listening on port ${PORT}`);
});
