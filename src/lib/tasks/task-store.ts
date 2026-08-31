import { randomUUID } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import type { OcrTask, OcrTaskResult, TaskStatus } from "./types";

/**
 * تخزين مهام مبني على ملف JSON واحد على القرص، مع ذاكرة تخزين مؤقت
 * في العملية لتسريع القراءة المتكررة أثناء polling.
 *
 * لماذا هذا بدل `tasks = {}` القديم:
 * - يبقى بعد إعادة تشغيل السيرفر (المهام القديمة لا تُفقد).
 * - قابل للتبديل لاحقًا بـ SQLite/Postgres دون تغيير الواجهة الخارجية
 *   (createTask/getTask/updateTask) — فقط استبدل تنفيذ هذا الملف.
 *
 * ⚠️ حدود معروفة: لا يزال غير آمن عبر أكثر من عملية Node تعمل بالتوازي
 * (multi-instance) بسبب عدم وجود قفل حقيقي على الملف. كافٍ لسيرفر واحد،
 * ويكفي لحجم هذا المشروع. إن احتجت نشرًا موزّعًا، بدّل لـ SQLite (better-sqlite3)
 * أو Postgres خلف نفس الواجهة.
 */

const STORE_PATH = path.join(process.cwd(), ".data", "tasks.json");

let cache: Map<string, OcrTask> | null = null;
let writeQueue: Promise<void> = Promise.resolve();

async function loadFromDisk(): Promise<Map<string, OcrTask>> {
  if (cache) return cache;

  try {
    const raw = await readFile(STORE_PATH, "utf8");
    const parsed: OcrTask[] = JSON.parse(raw);
    cache = new Map(parsed.map((t) => [t.id, t]));
  } catch {
    cache = new Map();
  }

  return cache;
}

/** يكتب الحالة الحالية للقرص، بترتيب متسلسل لتفادي كتابات متزامنة متضاربة. */
function persist(): Promise<void> {
  writeQueue = writeQueue.then(async () => {
    if (!cache) return;
    await mkdir(path.dirname(STORE_PATH), { recursive: true });
    const data = JSON.stringify(Array.from(cache.values()), null, 2);
    await writeFile(STORE_PATH, data, "utf8");
  });
  return writeQueue;
}

export async function createTask(): Promise<OcrTask> {
  const tasks = await loadFromDisk();
  const now = Date.now();
  const task: OcrTask = {
    id: randomUUID(),
    status: "processing",
    progress: 0,
    createdAt: now,
    updatedAt: now,
    result: null,
    error: null,
  };
  tasks.set(task.id, task);
  await persist();
  return task;
}

export async function getTask(id: string): Promise<OcrTask | null> {
  const tasks = await loadFromDisk();
  return tasks.get(id) ?? null;
}

export async function updateTaskProgress(
  id: string,
  progress: number
): Promise<void> {
  const tasks = await loadFromDisk();
  const task = tasks.get(id);
  if (!task) return;
  task.progress = progress;
  task.updatedAt = Date.now();
  await persist();
}

export async function completeTask(
  id: string,
  result: OcrTaskResult
): Promise<void> {
  const tasks = await loadFromDisk();
  const task = tasks.get(id);
  if (!task) return;
  task.status = "completed";
  task.progress = 100;
  task.result = result;
  task.updatedAt = Date.now();
  await persist();
}

export async function failTask(id: string, error: string): Promise<void> {
  const tasks = await loadFromDisk();
  const task = tasks.get(id);
  if (!task) return;
  task.status = "failed";
  task.error = error;
  task.updatedAt = Date.now();
  await persist();
}

/** تنظيف اختياري للمهام القديمة (يُستدعى دوريًا أو عند الإقلاع). */
export async function pruneOldTasks(maxAgeMs = 24 * 60 * 60 * 1000): Promise<void> {
  const tasks = await loadFromDisk();
  const cutoff = Date.now() - maxAgeMs;
  for (const [id, task] of tasks) {
    if (task.updatedAt < cutoff) tasks.delete(id);
  }
  await persist();
}
