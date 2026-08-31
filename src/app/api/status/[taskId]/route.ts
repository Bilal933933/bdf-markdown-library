import { NextRequest } from "next/server";
import { getTask } from "@/lib/tasks/task-store";
import { NotFoundError } from "@/lib/api/errors";
import { apiSuccess } from "@/lib/api/response";
import { withErrorHandling } from "@/lib/api/handler";

export const GET = withErrorHandling(
  async (_req: NextRequest, { params }: { params: { taskId: string } }) => {
    const task = await getTask(params.taskId);

    if (!task) {
      throw new NotFoundError("المهمة غير موجودة.");
    }

    return apiSuccess({
      status: task.status,
      progress: task.progress,
      result: task.result,
      error: task.error,
    });
  }
);
