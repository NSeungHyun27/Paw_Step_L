import { createBrowserRouter } from "react-router";
import { Layout } from "./Layout";
import { Home } from "./pages/Home";
import { Upload } from "./pages/Upload";
import { Result } from "./pages/Result";
import { WalkRoute } from "./pages/WalkRoute";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: Home },
      { path: "upload", Component: Upload },
      { path: "result", Component: Result },
      { path: "walk-route", Component: WalkRoute },
    ],
  },
]);
