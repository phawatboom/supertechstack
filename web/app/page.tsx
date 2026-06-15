"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";

type Workspace = {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL;

export default function HomePage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceName, setWorkspaceName] = useState("");
  const [workspaceDescription, setWorkspaceDescription] = useState("");

  const fetchWorkspaces = useCallback(async () => {
    const response = await fetch(`${apiUrl}/workspaces`);
    const data = await response.json();
    setWorkspaces(data);
  }, []);

  async function createWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    await fetch(`${apiUrl}/workspaces`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: workspaceName,
        description: workspaceDescription || null,
      }),
    });
    setWorkspaceName("");
    setWorkspaceDescription("");
    await fetchWorkspaces();
  }

  useEffect(() => {
    void fetchWorkspaces();
  }, [fetchWorkspaces]);

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-3xl font-bold">InsightOS</h1>
      <p className="mt-2 text-gray-600">
        Create research workspaces and turn sources into structured knowledge.
      </p>

      <form onSubmit={createWorkspace} className="mt-8 space-y-4 rounded-lg border p-4">
        <div>
          <label className="block text-sm font-medium">Workspace name</label>
          <input
            value={workspaceName}
            onChange={(event) => setWorkspaceName(event.target.value)}
            className="mt-1 w-full rounded border p-2"
            placeholder="AI full-stack job research"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium">Description</label>
          <textarea
            value={workspaceDescription}
            onChange={(event) => setWorkspaceDescription(event.target.value)}
            className="mt-1 w-full rounded border p-2"
            placeholder="Researching AI full-stack roles, skills, and project ideas."
          />
        </div>

        <button className="rounded bg-black px-4 py-2 text-white">
          Create workspace
        </button>
      </form>

      <section className="mt-8">
        <h2 className="text-xl font-semibold">Workspaces</h2>

        <div className="mt-4 space-y-3">
          {workspaces.map((workspace) => (
            <div key={workspace.id} className="rounded-lg border p-4">
              <h3 className="font-medium">{workspace.name}</h3>
              <p className="text-sm text-gray-600">
                {workspace.description || "No description"}
              </p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
