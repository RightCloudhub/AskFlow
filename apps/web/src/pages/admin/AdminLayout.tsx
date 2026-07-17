import { Link, NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import { getToken, setToken } from "../../api/client";
import { useFeatures } from "../../plugins/features";
import { filterNav } from "../../plugins/registry";

export function AdminLayout() {
  const nav = useNavigate();
  const { features, ready } = useFeatures();
  if (!getToken()) return <Navigate to="/login" replace />;

  const items = filterNav(features);

  return (
    <div className="admin-shell">
      <aside className="admin-nav">
        <div className="sidebar-head">
          <span className="brand-mark sm">AF</span>
          <strong>Admin</strong>
        </div>
        {!ready ? <span className="muted">加载功能…</span> : null}
        {items.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === "/admin"}>
            {item.label}
          </NavLink>
        ))}
        <Link to="/">用户台</Link>
        <button
          className="linkish"
          type="button"
          onClick={() => {
            setToken(null);
            nav("/login");
          }}
        >
          退出
        </button>
      </aside>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  );
}
