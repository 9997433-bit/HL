import express from 'express';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Build the HL Express application. The task store is kept in memory so the
 * factory can be instantiated independently per test run without shared state.
 */
export function createApp() {
  const app = express();
  app.use(express.json());

  let nextId = 1;
  const tasks = new Map();

  const seed = (title) => {
    const id = nextId++;
    tasks.set(id, { id, title, done: false });
  };
  seed('Read the HL README');
  seed('Try the REST API');

  const api = express.Router();

  api.get('/tasks', (req, res) => {
    res.json([...tasks.values()]);
  });

  api.post('/tasks', (req, res) => {
    const title = typeof req.body?.title === 'string' ? req.body.title.trim() : '';
    if (!title) {
      return res.status(400).json({ error: 'title is required' });
    }
    const id = nextId++;
    const task = { id, title, done: false };
    tasks.set(id, task);
    res.status(201).json(task);
  });

  api.patch('/tasks/:id', (req, res) => {
    const id = Number(req.params.id);
    const task = tasks.get(id);
    if (!task) {
      return res.status(404).json({ error: 'not found' });
    }
    if (typeof req.body?.done === 'boolean') {
      task.done = req.body.done;
    }
    if (typeof req.body?.title === 'string' && req.body.title.trim()) {
      task.title = req.body.title.trim();
    }
    res.json(task);
  });

  api.delete('/tasks/:id', (req, res) => {
    const id = Number(req.params.id);
    if (!tasks.has(id)) {
      return res.status(404).json({ error: 'not found' });
    }
    tasks.delete(id);
    res.status(204).end();
  });

  app.use('/api', api);

  app.get('/health', (req, res) => res.json({ status: 'ok' }));

  app.use(express.static(path.join(__dirname, '..', 'public')));

  return app;
}
