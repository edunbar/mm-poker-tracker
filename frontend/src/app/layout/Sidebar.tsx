import React from "react";
import { NavLink } from "react-router-dom";
import { adminNav } from "../../features/admin/nav";

const ACTIVE = "bg-emerald-600 text-white";
const INACTIVE = "text-gray-700 hover:bg-gray-50";

function renderPath(path: string) {
  // Replace :publicCode with example public code so NavLink works
  const exampleCode = process.env.REACT_APP_PUBLIC_CODE || "C4QROK";
  return path.replace(":publicCode", exampleCode);
}

export default function Sidebar() {
  return (
    <nav className="shadow-sm ring-1 ring-gray-100 rounded-lg bg-white p-3">
      <div className="text-sm font-semibold mb-3">Admin</div>

      <ul className="space-y-2">
        {adminNav.map((item) => (
          <li key={item.path}>
            <NavLink
              to={renderPath(item.path)}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-lg text-sm font-medium ${
                  isActive ? ACTIVE : INACTIVE
                }`
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
