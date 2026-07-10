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
      {/* key={pathname} forces a remount on navigation, replaying the
          .layout-content fade-in as a lightweight page transition */}
      <main className="layout-content" key={location.pathname}>
        <Outlet />
      </main>
    </div>
  );
}
