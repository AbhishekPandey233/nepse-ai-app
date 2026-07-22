import { Navigate, Outlet, useLocation } from "react-router-dom";

import Sidebar from "./Sidebar.jsx";

export default function Layout() {
  const location = useLocation();

  if (!localStorage.getItem("token")) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="layout">
      <Sidebar />
      <main className="layout-content" key={location.pathname}>
        <Outlet />
      </main>
    </div>
  );
}
