import ChatHistory from "./components/ChatHistory";
import { Link } from "react-router-dom";
import { useState, useEffect } from "react";

// Example SVG icons (replace with your own or use a library like react-icons)
const icons = {
  newChat: (
    <svg width="20" height="20" fill="none">
      <path
        d="M4 10h12M10 4v12"
        stroke="#fff"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  ),
};

const Sidebar = ({ handleChatSelect }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Listen for sidebar collapse events
  useEffect(() => {
    const handleSidebarToggle = () => {
      setIsCollapsed((prev) => !prev);
    };

    window.addEventListener("toggleSidebar", handleSidebarToggle);
    return () => {
      window.removeEventListener("toggleSidebar", handleSidebarToggle);
    };
  }, []);

  // Emit sidebar state changes
  useEffect(() => {
    window.dispatchEvent(
      new CustomEvent("sidebarStateChange", {
        detail: { isCollapsed },
      })
    );
  }, [isCollapsed]);

  const handleToggle = () => {
    setIsCollapsed((prev) => !prev);
  };
  return (
    <aside
      className={`flex flex-col z-50 h-screen bg-slate-900/20 text-white p-2 mt-3 justify-between shadow-lg transition-all duration-300 ${
        isCollapsed ? "w-16" : "w-72"
      }`}
    >
      <div className="pt-10 md:pt-0 md:z-50">
        {/* Top logo and collapse icon */}
        <div className="flex items-center mb-2 justify-between px-2">
          {!isCollapsed && (
            <img alt="pancea logo" width={30} height={30} src="/logonew.png" />
          )}
          <button
            onClick={handleToggle}
            data-slot="sidebar-trigger"
            className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50 size-7 -ml-1"
            data-sidebar="trigger"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="lucide lucide-panel-left"
            >
              <rect width="18" height="18" x="3" y="3" rx="2"></rect>
              <path d="M9 3v18"></path>
            </svg>
            <span className="sr-only">Toggle Sidebar</span>
          </button>
        </div>
        {!isCollapsed && (
          <>
            <Link to="/">
              <SidebarItem icon={icons.newChat} label="New chat" />
            </Link>
            <ChatHistory handleChatSelect={handleChatSelect} />
          </>
        )}
      </div>
    </aside>
  );
};

function SidebarItem({ icon, label }) {
  return (
    <div className="flex items-center gap-3 px-2 py-2 hover:bg-gray-800 rounded cursor-pointer">
      <span className="w-6 h-6 flex items-center justify-center">{icon}</span>
      <span className="font-medium text-base">{label}</span>
    </div>
  );
}

export default Sidebar;
