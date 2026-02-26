import { useState } from "react";
import { Link, useLocation } from "react-router";

const tabs = [
  { path: "/", label: "홈", iconKey: "home" as const, iconPng: null as string | null },
  { path: "/upload", label: "생명", iconKey: "life" as const, iconPng: "/icons/Activity.png" },
  { path: "/walk-route", label: "강아지", iconKey: "paw" as const, iconPng: "/icons/Group_123202.png" },
] as const;

const INNER_CIRCLE = "#FFFFFF"; // 비선택: 흰색 원
const INNER_ACTIVE = "#5DADE2"; // 선택: 하늘색

const CIRCLE_SIZE = 44; // 원 크기 (작게)
const ICON_SIZE_PX = 22; // 원 안에 맞춤

const ICON_SIZE = 18;
const stroke = "#000";
const svgCommon = { width: ICON_SIZE, height: ICON_SIZE, viewBox: "0 0 24 24", fill: "none" as const, stroke, strokeWidth: "2", strokeLinecap: "round" as const, strokeLinejoin: "round" as const };

function IconSvg({ name }: { name: (typeof tabs)[number]["iconKey"]; active: boolean }) {
  if (name === "home") {
    return (
      <svg {...svgCommon}>
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
    );
  }
  if (name === "life") {
    return (
      <svg {...svgCommon}>
        <polyline points="2 12 5 12 6.5 4 9 20 11 6 13 18 15 12 17 12 22 12" />
      </svg>
    );
  }
  if (name === "paw") {
    return (
      <svg {...svgCommon}>
        <ellipse cx="12" cy="17" rx="6" ry="4.5" />
        <circle cx="8" cy="8.5" r="2.6" />
        <circle cx="11" cy="5.5" r="2.6" />
        <circle cx="13" cy="5.5" r="2.6" />
        <circle cx="16" cy="8.5" r="2.6" />
      </svg>
    );
  }
  return null;
}

function TabIcon({ tab, isActive }: { tab: (typeof tabs)[number]; isActive: boolean }) {
  const [imgError, setImgError] = useState(false);
  if (tab.iconPng && !imgError) {
    return (
      <img
        src={tab.iconPng}
        alt=""
        width={ICON_SIZE_PX}
        height={ICON_SIZE_PX}
        className="object-contain"
        style={{ maxWidth: ICON_SIZE_PX, maxHeight: ICON_SIZE_PX }}
        onError={() => setImgError(true)}
      />
    );
  }
  return <IconSvg name={tab.iconKey} active={isActive} />;
}

export function BottomNav() {
  const location = useLocation();
  const currentPath = location.pathname;

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 flex justify-center py-2 px-6"
      style={{ paddingBottom: "max(env(safe-area-inset-bottom), 8px)" }}
    >
      <div className="w-full max-w-md mx-auto">
        <div
          className="flex items-center justify-around rounded-xl px-3 py-2 shadow-sm w-full max-w-[calc(100%-48px)] mx-auto"
        style={{
          backgroundColor: "rgba(255,255,255,0.95)",
          border: "1px solid rgba(0,0,0,0.06)",
        }}
      >
        {tabs.map((tab) => {
          const isActive = currentPath === tab.path || (tab.path !== "/" && currentPath.startsWith(tab.path));
          return (
            <Link
              key={tab.path}
              to={tab.path}
              className="flex items-center justify-center no-underline"
              aria-current={isActive ? "page" : undefined}
              aria-label={tab.label}
            >
              <div
                className="flex flex-shrink-0 items-center justify-center rounded-full transition-colors duration-200"
                style={{
                  width: CIRCLE_SIZE,
                  height: CIRCLE_SIZE,
                  backgroundColor: isActive ? INNER_ACTIVE : INNER_CIRCLE,
                  boxShadow: "0 1px 2px rgba(0,0,0,0.08)",
                }}
              >
                <TabIcon tab={tab} isActive={isActive} />
              </div>
            </Link>
          );
        })}
        </div>
      </div>
    </nav>
  );
}
