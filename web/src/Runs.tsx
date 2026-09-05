import { useEffect, useState } from "react";
import {
  listRuns,
  getRun,
  type RunSummary,
  type RunDetail,
} from "./api";

// Percentages, attempts and money all line up in columns, so they get tabular figures.
function pct(value: number) {
  return `${value}%`;
}

function Detail({ run }: { run: RunDetail }) {
  return (
    <div className="run-detail">
      <h2>By kind of bug</h2>
      <p className="subtitle">
        The headline number hides its own bias — most cases are the easy kinds.
      </p>
      <table className="preview">
        <thead>
          <tr>
            <th>Break</th>
            <th>Cases</th>
            <th>pass@1</th>
            <th>pass@3</th>
          </tr>
        </thead>
        <tbody>
          {run.by_break_type.map((row) => (
            <tr key={row.break_type}>
              <td>{row.break_type.replace(/_/g, " ")}</td>
              <td>{row.cases}</td>
              <td>{pct(row.pass_at_1)}</td>
              <td>{pct(row.pass_at_3)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>What it got wrong</h2>
      {run.failures.length === 0 ? (
        <p>Nothing failed in this run.</p>
      ) : (
        run.failures.map((failure) => (
          <details className="attempt" key={failure.case_id}>
            <summary>
              {failure.case_id.replace(/_/g, " ")} — {failure.failure_reason}
            </summary>
            <pre className="sql">{failure.fixed_query ?? "No query produced."}</pre>
          </details>
        ))
      )}
    </div>
  );
}

export default function Runs() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [open, setOpen] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listRuns()
      .then(setRuns)
      .catch((e) => setError((e as Error).message));
  }, []);

  // Clicking a run loads its breakdown. Clicking the open one closes it.
  async function toggle(id: string) {
    if (open?.id === id) return setOpen(null);
    try {
      setOpen(await getRun(id));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (error) return <p>Couldn't load runs: {error}</p>;
  if (!runs) return <p>Loading…</p>;

  if (runs.length === 0) {
    return (
      <>
        <h1>Runs</h1>
        <div className="empty">
          <p>No eval runs yet.</p>
          <pre className="sql">uv run python -m app.evaluation.runner</pre>
        </div>
      </>
    );
  }

  return (
    <>
      <h1>Runs</h1>
      <p className="subtitle">
        How often the agent is right, on {runs[0].cases} broken queries with known answers.
      </p>

      <table className="preview runs">
        <thead>
          <tr>
            <th>Run</th>
            <th>Cases</th>
            <th>pass@1</th>
            <th>pass@3</th>
            <th>Attempts</th>
            <th>Latency</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr
              key={run.id}
              onClick={() => toggle(run.id)}
              className={open?.id === run.id ? "open" : ""}
            >
              <td>
                {run.note ?? "untitled"}
                <span className="when">
                  {" "}
                  {new Date(run.started_at).toLocaleDateString()}
                </span>
              </td>
              <td>{run.cases}</td>
              <td>{pct(run.pass_at_1)}</td>
              <td>{pct(run.pass_at_3)}</td>
              <td>{run.avg_attempts}</td>
              <td>{run.avg_latency_ms ? `${(run.avg_latency_ms / 1000).toFixed(1)}s` : "—"}</td>
              <td>${run.cost_usd.toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {open && <Detail run={open} />}
    </>
  );
}
