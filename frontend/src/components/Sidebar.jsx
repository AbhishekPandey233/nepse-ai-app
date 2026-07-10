import { useState } from "react";
import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/prediction", label: "Prediction" },
  { to: "/volatility", label: "Volatility" },
  { to: "/explainability", label: "Explainability" },
  { to: "/profile", label: "Profile" },
];

export default function Sidebar() {
  const [open, setOpen] = useState(false);

  function linkClass({ isActive }) {
    return `sidebar-link${isActive ? " active" : ""}`;
  }

  return (
    <>
      <div className="sidebar-topbar">
        <span className="sidebar-brand">NEPSE AI</span>
        <button
          type="button"
          className="hamburger"
          aria-label="Toggle navigation menu"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
        >
          <span />
          <span />
          <span />
        </button>
      </div>

      <nav className={`sidebar${open ? " sidebar-open" : ""}`}>
        <span className="sidebar-brand">NEPSE AI</span>
        {LINKS.map(({ to, label }) => (
          <NavLink key={to} to={to} className={linkClass} onClick={() => setOpen(false)}>
            {label}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
