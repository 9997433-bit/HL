import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../src/app.js';

let server;
let baseUrl;

before(async () => {
  const app = createApp();
  await new Promise((resolve) => {
    server = app.listen(0, () => {
      const { port } = server.address();
      baseUrl = `http://127.0.0.1:${port}`;
      resolve();
    });
  });
});

after(() => {
  server?.close();
});

test('health endpoint returns ok', async () => {
  const res = await fetch(`${baseUrl}/health`);
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { status: 'ok' });
});

test('lists seeded tasks', async () => {
  const res = await fetch(`${baseUrl}/api/tasks`);
  assert.equal(res.status, 200);
  const tasks = await res.json();
  assert.ok(Array.isArray(tasks));
  assert.equal(tasks.length, 2);
});

test('creates a task', async () => {
  const res = await fetch(`${baseUrl}/api/tasks`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ title: 'Write tests' }),
  });
  assert.equal(res.status, 201);
  const task = await res.json();
  assert.equal(task.title, 'Write tests');
  assert.equal(task.done, false);
});

test('rejects an empty task title', async () => {
  const res = await fetch(`${baseUrl}/api/tasks`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ title: '   ' }),
  });
  assert.equal(res.status, 400);
});

test('updates and deletes a task', async () => {
  const created = await (
    await fetch(`${baseUrl}/api/tasks`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ title: 'Temp task' }),
    })
  ).json();

  const patched = await fetch(`${baseUrl}/api/tasks/${created.id}`, {
    method: 'PATCH',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ done: true }),
  });
  assert.equal(patched.status, 200);
  assert.equal((await patched.json()).done, true);

  const del = await fetch(`${baseUrl}/api/tasks/${created.id}`, { method: 'DELETE' });
  assert.equal(del.status, 204);

  const missing = await fetch(`${baseUrl}/api/tasks/${created.id}`, { method: 'DELETE' });
  assert.equal(missing.status, 404);
});
