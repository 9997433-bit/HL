const listEl = document.getElementById('task-list');
const emptyEl = document.getElementById('empty');
const formEl = document.getElementById('new-task');
const inputEl = document.getElementById('task-title');

async function api(path, options) {
  const res = await fetch(`/api${path}`, options);
  if (!res.ok && res.status !== 204) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

function render(tasks) {
  listEl.innerHTML = '';
  emptyEl.hidden = tasks.length > 0;

  for (const task of tasks) {
    const li = document.createElement('li');
    li.className = `task${task.done ? ' task--done' : ''}`;

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'task__checkbox';
    checkbox.checked = task.done;
    checkbox.addEventListener('change', async () => {
      await api(`/tasks/${task.id}`, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ done: checkbox.checked }),
      });
      load();
    });

    const title = document.createElement('span');
    title.className = 'task__title';
    title.textContent = task.title;

    const del = document.createElement('button');
    del.className = 'task__delete';
    del.type = 'button';
    del.textContent = '\u00d7';
    del.setAttribute('aria-label', `Delete ${task.title}`);
    del.addEventListener('click', async () => {
      await api(`/tasks/${task.id}`, { method: 'DELETE' });
      load();
    });

    li.append(checkbox, title, del);
    listEl.append(li);
  }
}

async function load() {
  render(await api('/tasks'));
}

formEl.addEventListener('submit', async (event) => {
  event.preventDefault();
  const title = inputEl.value.trim();
  if (!title) {
    return;
  }
  await api('/tasks', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  inputEl.value = '';
  inputEl.focus();
  load();
});

load();
