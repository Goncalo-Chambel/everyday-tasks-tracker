const boardEl = document.getElementById("board");
const showCompletedCheckbox = document.getElementById("show-completed");
const modalOverlay = document.getElementById("task-modal");
const modalContent = document.getElementById("modal-content");
const modalCloseBtn = document.getElementById("modal-close");

const CATEGORY_COLORS = [
  "#6c8cff",
  "#5cc98c",
  "#e5677a",
  "#f0b429",
  "#a78bfa",
  "#4fd1c5",
  "#f472b6",
  "#fb923c",
];

let draggedCategoryId = null;

function animateReorder(mutate) {
  const columns = [...boardEl.querySelectorAll(".column[data-category-id]")];
  const firstRects = new Map(columns.map((el) => [el, el.getBoundingClientRect()]));

  mutate();

  for (const el of columns) {
    const first = firstRects.get(el);
    const last = el.getBoundingClientRect();
    const dx = first.left - last.left;
    if (!dx) continue;
    el.style.transition = "none";
    el.style.transform = `translateX(${dx}px)`;
    requestAnimationFrame(() => {
      el.style.transition = "transform 180ms ease";
      el.style.transform = "";
    });
  }
}

async function api(path, options) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${response.status}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

async function loadBoard() {
  const params = new URLSearchParams();
  if (!showCompletedCheckbox.checked) params.set("done", "false");

  const [categories, tasks] = await Promise.all([api("/api/categories"), api(`/api/tasks?${params.toString()}`)]);

  renderBoard(categories, tasks);
}

function renderBoard(categories, tasks) {
  boardEl.innerHTML = "";
  for (const category of categories) {
    const categoryTasks = tasks.filter((task) => task.category_id === category.id);
    boardEl.appendChild(buildColumn(category, categoryTasks));
  }
  boardEl.appendChild(buildAddColumnTile(categories));
}

function buildColumn(category, tasks) {
  const color = category.color;

  const column = document.createElement("div");
  column.className = "column";
  column.style.borderTopColor = color;
  column.dataset.categoryId = category.id;

  column.addEventListener("dragover", (event) => {
    if (draggedCategoryId === null || draggedCategoryId === category.id) return;
    event.preventDefault();
    const draggedEl = boardEl.querySelector(`.column[data-category-id="${draggedCategoryId}"]`);
    if (!draggedEl) return;
    const rect = column.getBoundingClientRect();
    const before = event.clientX < rect.left + rect.width / 2;
    const target = before ? column : column.nextSibling;
    if (draggedEl === target || draggedEl.nextSibling === target) return;
    animateReorder(() => boardEl.insertBefore(draggedEl, target));
  });

  const header = document.createElement("div");
  header.className = "column-header";
  header.draggable = true;
  header.addEventListener("dragstart", (event) => {
    draggedCategoryId = category.id;
    event.dataTransfer.effectAllowed = "move";
    column.classList.add("dragging");
  });
  header.addEventListener("dragend", () => {
    column.classList.remove("dragging");
    draggedCategoryId = null;
    persistColumnOrder();
  });

  const title = document.createElement("h2");
  const dot = document.createElement("span");
  dot.className = "category-dot";
  dot.style.background = color;
  title.appendChild(dot);
  title.appendChild(document.createTextNode(category.name + " "));
  const count = document.createElement("span");
  count.className = "column-count";
  count.textContent = `(${tasks.length})`;
  title.appendChild(count);

  const deleteBtn = document.createElement("button");
  deleteBtn.className = "icon-btn";
  deleteBtn.type = "button";
  deleteBtn.textContent = "✕";
  deleteBtn.title = "Delete category";
  deleteBtn.addEventListener("click", () => deleteCategory(category));

  header.append(title, deleteBtn);
  column.appendChild(header);

  const list = document.createElement("ul");
  list.className = "column-tasks";
  if (tasks.length === 0) {
    const empty = document.createElement("p");
    empty.className = "column-empty";
    empty.textContent = "No tasks";
    list.appendChild(empty);
  } else {
    for (const task of tasks) {
      list.appendChild(buildTaskItem(task));
    }
  }
  column.appendChild(list);

  column.appendChild(buildAddTaskSlot(category.id));

  return column;
}

function buildTaskItem(task) {
  const li = document.createElement("li");
  li.className = "task" + (task.done ? " done" : "");
  li.style.borderLeftColor = task.category_color;
  li.addEventListener("click", () => openTaskModal(task));

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = task.done;
  checkbox.addEventListener("click", (event) => event.stopPropagation());
  checkbox.addEventListener("change", () => toggleDone(task.id, checkbox.checked));

  const body = document.createElement("div");
  body.className = "task-body";

  const titleEl = document.createElement("div");
  titleEl.className = "task-title";
  titleEl.textContent = task.title;
  body.appendChild(titleEl);

  const deleteBtn = document.createElement("button");
  deleteBtn.className = "icon-btn";
  deleteBtn.type = "button";
  deleteBtn.textContent = "✕";
  deleteBtn.title = "Delete task";
  deleteBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    deleteTask(task.id);
  });

  li.append(checkbox, body, deleteBtn);
  return li;
}

function openTaskModal(task) {
  modalContent.innerHTML = "";

  const categoryRow = document.createElement("div");
  categoryRow.className = "modal-category";
  const dot = document.createElement("span");
  dot.className = "category-dot";
  dot.style.background = task.category_color;
  categoryRow.append(dot, document.createTextNode(task.category_name));

  const title = document.createElement("h3");
  title.className = "modal-title";
  title.textContent = task.title;

  modalContent.append(categoryRow, title);

  const description = document.createElement("p");
  description.className = "modal-description";
  description.textContent = task.description || "No description added.";
  modalContent.appendChild(description);

  const dates = document.createElement("div");
  dates.className = "modal-dates";
  const started = document.createElement("span");
  started.textContent = `Created on: ${task.start_date}`;
  dates.appendChild(started);
  if (task.end_date) {
    const ends = document.createElement("span");
    ends.textContent = `Completed on: ${task.end_date}`;
    dates.appendChild(ends);
  }
  modalContent.appendChild(dates);

  modalOverlay.hidden = false;
}

function closeTaskModal() {
  modalOverlay.hidden = true;
}

function buildAddTaskSlot(categoryId) {
  const slot = document.createElement("div");
  slot.className = "add-task-slot";

  const openBtn = document.createElement("button");
  openBtn.type = "button";
  openBtn.className = "add-task-btn";
  openBtn.textContent = "+ Add task";
  openBtn.addEventListener("click", () => {
    slot.innerHTML = "";
    slot.appendChild(buildAddTaskForm(categoryId, slot, openBtn));
  });

  slot.appendChild(openBtn);
  return slot;
}

function buildAddTaskForm(categoryId, slot, openBtn) {
  const form = document.createElement("form");
  form.className = "add-task-form";

  const titleInput = document.createElement("input");
  titleInput.type = "text";
  titleInput.placeholder = "Title";
  titleInput.required = true;
  titleInput.maxLength = 200;

  const descriptionInput = document.createElement("textarea");
  descriptionInput.placeholder = "Description (optional)";

  const endDateInput = document.createElement("input");
  endDateInput.type = "date";

  const actions = document.createElement("div");
  actions.className = "form-actions";

  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.textContent = "Cancel";
  cancelBtn.addEventListener("click", () => {
    slot.innerHTML = "";
    slot.appendChild(openBtn);
  });

  const submitBtn = document.createElement("button");
  submitBtn.type = "submit";
  submitBtn.className = "primary";
  submitBtn.textContent = "Add";

  actions.append(cancelBtn, submitBtn);
  form.append(titleInput, descriptionInput, endDateInput, actions);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await api("/api/tasks", {
      method: "POST",
      body: JSON.stringify({
        title: titleInput.value.trim(),
        description: descriptionInput.value.trim() || null,
        category_id: categoryId,
        end_date: endDateInput.value || null,
      }),
    });
    loadBoard();
  });

  titleInput.focus();
  return form;
}

function buildAddColumnTile(categories) {
  const tile = document.createElement("div");
  tile.className = "column add-column";

  const openBtn = document.createElement("button");
  openBtn.type = "button";
  openBtn.className = "add-category-btn";
  openBtn.textContent = "+ Add category";
  openBtn.addEventListener("click", () => {
    tile.innerHTML = "";
    tile.appendChild(buildAddColumnForm(tile, openBtn, categories));
  });

  tile.appendChild(openBtn);
  return tile;
}

function buildAddColumnForm(tile, openBtn, categories) {
  const form = document.createElement("form");
  form.className = "add-category-form";

  const nameInput = document.createElement("input");
  nameInput.type = "text";
  nameInput.placeholder = "Category name";
  nameInput.required = true;
  nameInput.maxLength = 50;

  let selectedColor = CATEGORY_COLORS[categories.length % CATEGORY_COLORS.length];

  const colorRow = document.createElement("div");
  colorRow.className = "color-swatches";

  const swatchButtons = CATEGORY_COLORS.map((color) => {
    const swatch = document.createElement("button");
    swatch.type = "button";
    swatch.className = "color-swatch" + (color === selectedColor ? " selected" : "");
    swatch.style.background = color;
    swatch.title = color;
    swatch.addEventListener("click", () => {
      selectedColor = color;
      for (const btn of swatchButtons) btn.classList.toggle("selected", btn === swatch);
    });
    colorRow.appendChild(swatch);
    return swatch;
  });

  const actions = document.createElement("div");
  actions.className = "form-actions";

  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.textContent = "Cancel";
  cancelBtn.addEventListener("click", () => {
    tile.innerHTML = "";
    tile.appendChild(openBtn);
  });

  const submitBtn = document.createElement("button");
  submitBtn.type = "submit";
  submitBtn.className = "primary";
  submitBtn.textContent = "Add";

  actions.append(cancelBtn, submitBtn);
  form.append(nameInput, colorRow, actions);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api("/api/categories", {
        method: "POST",
        body: JSON.stringify({ name: nameInput.value.trim(), color: selectedColor }),
      });
      loadBoard();
    } catch (error) {
      alert(error.message);
    }
  });

  nameInput.focus();
  return form;
}

async function toggleDone(taskId, done) {
  await api(`/api/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify({ done }),
  });
  loadBoard();
}

async function deleteTask(taskId) {
  await api(`/api/tasks/${taskId}`, { method: "DELETE" });
  loadBoard();
}

async function persistColumnOrder() {
  const ids = [...boardEl.querySelectorAll(".column[data-category-id]")].map((el) => Number(el.dataset.categoryId));
  try {
    await api("/api/categories/reorder", {
      method: "PUT",
      body: JSON.stringify({ category_ids: ids }),
    });
  } catch (error) {
    alert(error.message);
    loadBoard();
  }
}

async function deleteCategory(category) {
  if (!confirm(`Delete category "${category.name}"?`)) return;
  try {
    await api(`/api/categories/${category.id}`, { method: "DELETE" });
    loadBoard();
  } catch (error) {
    alert(error.message);
  }
}

showCompletedCheckbox.addEventListener("change", loadBoard);

modalCloseBtn.addEventListener("click", closeTaskModal);
modalOverlay.addEventListener("click", (event) => {
  if (event.target === modalOverlay) closeTaskModal();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeTaskModal();
});

loadBoard();
