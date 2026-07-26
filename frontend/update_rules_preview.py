with open("../frontend/app/rules/page.tsx", "r") as f:
    content = f.read()

# Replace proposal preview UI
old_proposal = '''          {proposal && (
            <div
              style={{
                border: "1px solid #c7d2fe",
                background: "#eef2ff",
                borderRadius: 8,
                padding: 12,
                marginTop: 10,
                fontSize: 13,
              }}
            >
              <strong>Rule terdeteksi:</strong>
              <div style={{ marginTop: 6 }}>
                Kolom: <em>{proposal.column_name}</em>
                <br />
                Jenis: {proposal.rule_label}
                <br />
                {Object.keys(proposal.params || {}).length > 0 && (
                  <>
                    Params: <code>{JSON.stringify(proposal.params)}</code>
                    <br />
                  </>
                )}
                Deskripsi: {proposal.description}
              </div>
              <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
                <button className="btn" type="button" onClick={editProposal}>
                  Edit
                </button>
                <button className="btn primary" type="button" onClick={activateProposal}>
                  Aktifkan Rule
                </button>
              </div>
            </div>
          )}'''

new_proposal = '''          {proposal && (
            <div
              style={{
                border: "1px solid #c7d2fe",
                background: "#f8fafc",
                borderRadius: "var(--radius)",
                padding: 16,
                marginTop: 16,
                boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px", borderBottom: "1px solid var(--border)", paddingBottom: "8px" }}>
                <span style={{ fontSize: "1.2rem" }}>🤖</span>
                <strong style={{ fontSize: "1.05rem" }}>Saran Rule AI</strong>
              </div>
              <div style={{ fontSize: "0.95rem", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div>
                  <span style={{ color: "var(--text-secondary)", width: "80px", display: "inline-block" }}>Kolom:</span>
                  <strong style={{ background: "#e2e8f0", padding: "2px 8px", borderRadius: "12px", fontSize: "0.85rem" }}>{proposal.column_name}</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-secondary)", width: "80px", display: "inline-block" }}>Jenis:</span>
                  <span style={{ fontWeight: 500 }}>{proposal.rule_label}</span>
                </div>
                {Object.keys(proposal.params || {}).length > 0 && (
                  <div style={{ display: "flex" }}>
                    <span style={{ color: "var(--text-secondary)", width: "80px", display: "inline-block" }}>Params:</span>
                    <code style={{ background: "#f1f5f9", padding: "2px 6px", borderRadius: "4px", fontSize: "0.85rem", color: "var(--primary)" }}>
                      {JSON.stringify(proposal.params)}
                    </code>
                  </div>
                )}
                <div style={{ marginTop: "4px", padding: "8px", background: "#f1f5f9", borderRadius: "6px", fontStyle: "italic", color: "var(--text-secondary)" }}>
                  "{proposal.description}"
                </div>
              </div>
              <div style={{ marginTop: 16, display: "flex", gap: 12, justifyContent: "flex-end" }}>
                <button className="btn" style={{ borderColor: "#fecaca", color: "var(--danger)" }} type="button" onClick={() => setProposal(null)}>
                  Tolak
                </button>
                <button className="btn" type="button" onClick={editProposal}>
                  Edit Manual
                </button>
                <button className="btn primary" type="button" onClick={activateProposal}>
                  ✓ Aktifkan Rule
                </button>
              </div>
            </div>
          )}'''

content = content.replace(old_proposal, new_proposal)

with open("../frontend/app/rules/page.tsx", "w") as f:
    f.write(content)
