import { ImageResponse } from "next/og";

export const alt = "SuperTechStack grounded research workspace";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          width: "100%",
          height: "100%",
          padding: 72,
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#f6f7fb",
          color: "#111827",
          fontFamily: "Arial, sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <div
            style={{
              display: "flex",
              width: 64,
              height: 64,
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 18,
              background: "#4f46e5",
              color: "white",
              fontSize: 32,
              fontWeight: 800,
            }}
          >
            S
          </div>
          <span style={{ fontSize: 30, fontWeight: 800 }}>SuperTechStack</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          <div style={{ maxWidth: 980, fontSize: 68, fontWeight: 800 }}>
            Grounded research from your own sources.
          </div>
          <div style={{ color: "#64748b", fontSize: 30 }}>
            Semantic retrieval, cited answers, and traceable evidence.
          </div>
        </div>
      </div>
    ),
    size,
  );
}
