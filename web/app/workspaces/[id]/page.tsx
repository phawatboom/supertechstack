"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

type Source = {
    id: number; 
    workspace_id: number;
    title: string;
    source_type: string;
    raw_text: string;
    created_at: string;
};

type Chunk = {
    id: number;
    source_id:number;
    workspace_id: number;
    chunk_index: number;
    content: string;
    created_at: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL

export default function WorkspaceDetailPage() {
    const params = useParams();
    const workspaceId = params.id as string 
    
    const [sources, setSources] = useState<Source[]>([]);
    const [chunks, setChunks] = useState<Chunk[]>([]);
    const [sourceTitle, setSourceTitle] = useState("");
    const [rawText, setRawText] = useState("");
    const [ isLoading, setIsLoading] = useState(false);

    const fetchWorkspaceData = useCallback(async () => {
        const [sourcesResponse, chunksResponse] = await Promise.all([
            fetch(`${apiUrl}/workspaces/${workspaceId}/sources`),
            fetch(`${apiUrl}/workspaces/${workspaceId}/chunks`),
        ]);
        const sourcesData: Source[] = await sourcesResponse.json();
        const chunksData: Chunk[] = await chunksResponse.json();

        return { sourcesData, chunksData };
    }, [workspaceId]);

    useEffect(() => {
        let cancelled = false;

        void fetchWorkspaceData().then(({ sourcesData, chunksData }) => {
            if (!cancelled) {
                setSources(sourcesData);
                setChunks(chunksData);
            }
        });

        return () => {
            cancelled = true;
        };
    }, [fetchWorkspaceData]);

    async function createSource(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();

        if (!sourceTitle.trim() || !rawText.trim()) {
            return; 
        }

        setIsLoading(true);

        await fetch(`${apiUrl}/workspaces/${workspaceId}/sources`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                title: sourceTitle,
                raw_text: rawText,
            }),
        });

        setSourceTitle("")
        setRawText("")

        const { sourcesData, chunksData } = await fetchWorkspaceData();
        setSources(sourcesData);
        setChunks(chunksData);
        setIsLoading(false);
    }
    
    return (
        <main>
            <h1> Workspace {workspaceId}</h1>
            <section style={{ marginTop: "2rem"}}>
                <h2>Add source</h2>
                <form onSubmit={createSource}>
                    <input
                        value={sourceTitle}
                        onChange={(event) => setSourceTitle(event.target.value)}
                        placeholder="Source title"
                        style={{ display: "block", width: "100%", marginBottom: "1rem"}}
                    />
                    <textarea
                        value={rawText}
                        onChange={(event) => setRawText(event.target.value)}
                        placeholder="Paste source text here"
                        rows={8}
                        style={{ display: "block", width: "100%", marginBottom: "1rem" }}
                    />

                    <button type="submit" disabled={isLoading}>
                        {isLoading ? "Saving..." : "Save source"}
                    </button>
                </form>
            </section>

            <section style={{ marginTop: "2rem" }}>
                <h2> Sources</h2>

                {sources.map((source) => (
                    <div key={source.id} style={{border: "1px solid #ddd", padding: "1rem", marginBottom: "1rem"}}>
                        <h3>{source.title}</h3>
                        <p>{source.source_type}</p>
                        <p>{source.raw_text.slice(0, 200)}...</p>
                    </div>
                ))}
            </section>
            <section style={{ marginTop: "2rem "}}>
                <h2> Chunks </h2> 
                {chunks.map((chunk) => (
                    <div key={chunk.id} style={{border: "1px solid #ddd", padding: "1rem", marginBottom:"1rem"}}>
                        <strong>
                            Source {chunk.source_id}, Chunk {chunk.chunk_index}
                        </strong>
                        <p>{chunk.content}</p>
                    </div>
                ))}
            </section>
        </main>
    )
}



