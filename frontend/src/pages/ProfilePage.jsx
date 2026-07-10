import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getMe } from "../api/client.js";
import ConfirmModal from "../components/ConfirmModal.jsx";
import ErrorRetry from "../components/ErrorRetry.jsx";
import LoadingSkeleton from "../components/LoadingSkeleton.jsx";

export default function ProfilePage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const result = await getMe();
      setData(result);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load profile.");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("token");
    navigate("/login");
  }

  return (
    <div className="profile-page">
      <h1>Profile</h1>

      {loading && (
        <div className="card">
          <LoadingSkeleton />
        </div>
      )}

      {error && (
        <div className="card">
          <ErrorRetry message={error} onRetry={load} />
        </div>
      )}

      {!loading && !error && data && (
        <div className="card">
          <div className="profile-field">
            <span className="stat-label">Email</span>
            <p className="stat-value">{data.email}</p>
          </div>
          <div className="profile-field">
            <span className="stat-label">Member since</span>
            <p className="stat-value">{new Date(data.created_at).toLocaleDateString()}</p>
          </div>
          <button type="button" className="btn-primary" onClick={() => setConfirmOpen(true)}>
            Log out
          </button>
        </div>
      )}

      {confirmOpen && (
        <ConfirmModal
          message="Are you sure you want to log out?"
          onConfirm={handleLogout}
          onCancel={() => setConfirmOpen(false)}
        />
      )}
    </div>
  );
}
