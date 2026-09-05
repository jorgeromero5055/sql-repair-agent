import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  useNavigate,
} from "react-router-dom";
import { useEffect, useState } from "react";
import { createRepair, listRepairs, type RepairListItem } from "./api";
import "./App.css";
import Repair from "./Repair";
import Runs from "./Runs";

function Queue() {
  const [repairs, setRepairs] = useState<RepairListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await listRepairs();
        if (!cancelled) setRepairs(data);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    }

    load();
    const timer = setInterval(() => {
      const busy = repairs?.some(
        (r) => r.status === "queued" || r.status === "running"
      );
      if (busy) load();
    }, 3000);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [repairs]);

  if (error) return <p>Couldn't load repairs: {error}</p>;
  if (repairs === null) return <p>Loading…</p>;

  if (repairs.length === 0) {
    return (
      <>
        <h1>Queue</h1>
        <p className="subtitle">Nothing here yet.</p>
        <div className="empty">
          <p>
            Paste a broken SQL query and say what it was supposed to do. An agent
            fixes it, and you approve the result before anything is saved.
          </p>
          <Link to="/submit">Submit a repair</Link>
        </div>
      </>
    );
  }

  return (
    <>
      <h1>Queue</h1>
      <p className="subtitle">{repairs.length} repairs, newest first.</p>
      <ul className="queue">
        {repairs.map((r) => (
          <li key={r.id}>
            <Link to={`/repairs/${r.id}`}>
              <span className={`status ${r.status}`}>
                {r.status.replace("_", " ")}
              </span>
              <span className="intent">{r.intent}</span>
              <span className="when">
                {new Date(r.created_at).toLocaleDateString()}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}

function Submit() {
  const [intent, setIntent] = useState("");
  const [brokenQuery, setBrokenQuery] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createRepair(intent, brokenQuery);
      navigate("/queue");
    } catch (err) {
      setError((err as Error).message);
      setSubmitting(false);
    }
  }

  return (
    <>
      <h1>Submit a repair</h1>
      <p className="subtitle">
        The agent never sees an error message — it finds the problem by running
        the query itself.
      </p>
      <form className="form" onSubmit={onSubmit}>
        <div>
          <label htmlFor="intent">What was it supposed to do?</label>
          <input
            id="intent"
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="query">The broken query</label>
          <textarea
            id="query"
            value={brokenQuery}
            onChange={(e) => setBrokenQuery(e.target.value)}
            rows={8}
            required
          />
        </div>
        {error && <p className="error">Couldn't submit: {error}</p>}
        <div>
          <button type="submit" disabled={submitting}>
            {submitting ? "Submitting…" : "Repair"}
          </button>
        </div>
      </form>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <header className="topbar">
        <div className="topbar-inner">
          <Link to="/queue" className="brand">
            SQL Repair Agent
          </Link>
          <nav>
            <Link to="/queue">Queue</Link>
            <Link to="/runs">Runs</Link>
            <Link to="/submit">Submit</Link>
          </nav>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Queue />} />
          <Route path="/queue" element={<Queue />} />
          <Route path="/repairs/:id" element={<Repair />} />
          <Route path="/runs" element={<Runs />} />
          <Route path="/submit" element={<Submit />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
