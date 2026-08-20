import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL;

function Queue() {
  const [status, setStatus] = useState<string>("loading...");

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then((d) => setStatus(JSON.stringify(d)))
      .catch((e) => setStatus("failed: " + e.message));
  }, []);

  return (
    <>
      <h1>Queue</h1>
      <p>API says: {status}</p>
    </>
  );
}

function Repair() {
  return <h1>Repair</h1>;
}

function Runs() {
  return <h1>Runs</h1>;
}

export default function App() {
  return (
    <BrowserRouter>
      <nav>
        <Link to="/queue">Queue</Link> | <Link to="/runs">Runs</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Queue />} />
        <Route path="/queue" element={<Queue />} />
        <Route path="/repairs/:id" element={<Repair />} />
        <Route path="/runs" element={<Runs />} />
      </Routes>
    </BrowserRouter>
  );
}
