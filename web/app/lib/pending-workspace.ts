export type PendingWorkspace = {
  name: string;
  description: string | null;
  requestId: string;
};

const STORAGE_KEY = "supertechstack.pending-workspace";
const MAX_AGE_MS = 24 * 60 * 60 * 1000;

type StoredPendingWorkspace = PendingWorkspace & {
  createdAt: number;
};

export function savePendingWorkspace(workspace: PendingWorkspace) {
  const storedWorkspace: StoredPendingWorkspace = {
    ...workspace,
    createdAt: Date.now(),
  };

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(storedWorkspace));
}

export function readPendingWorkspace(): PendingWorkspace | null {
  const value = window.localStorage.getItem(STORAGE_KEY);

  if (!value) {
    return null;
  }

  try {
    const workspace = JSON.parse(value) as Partial<StoredPendingWorkspace>;
    const requestId =
      typeof workspace.requestId === "string" && workspace.requestId
        ? workspace.requestId
        : crypto.randomUUID();

    if (
      typeof workspace.name !== "string" ||
      !workspace.name.trim() ||
      typeof workspace.createdAt !== "number" ||
      Date.now() - workspace.createdAt > MAX_AGE_MS
    ) {
      clearPendingWorkspace();
      return null;
    }

    return {
      name: workspace.name.trim(),
      description:
        typeof workspace.description === "string" && workspace.description.trim()
          ? workspace.description.trim()
          : null,
      requestId,
    };
  } catch {
    clearPendingWorkspace();
    return null;
  }
}

export function clearPendingWorkspace() {
  window.localStorage.removeItem(STORAGE_KEY);
}
