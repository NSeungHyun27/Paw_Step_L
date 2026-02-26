import { Outlet } from "react-router";
import { BottomNav } from "./components/BottomNav";

export function Layout() {
  return (
    <>
      <main className="pb-24 min-h-screen">
        <Outlet />
      </main>
      <BottomNav />
    </>
  );
}
