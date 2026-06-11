import ChatHistory from "./components/ChatHistory";
import { Link } from "react-router-dom";
import { apiKeyDashboardPath, usageDashboardPath } from "../constants/RouteConstants";

// Example SVG icons (replace with your own or use a library like react-icons)
const icons = {
  newChat: (
    <svg width="20" height="20" fill="none" viewBox="0 0 24 24">
      <path
        d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"
        stroke="#fff"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
};

const Sidebar = ({
  handleChatSelect,
  isCollapsed,
  onToggle,
  chats,
  chatsLoading = false,
  onRefreshChats,
  onRenameChat,
  onDeleteChat,
}) => {
  return (
    <aside
      className={`md:flex flex-col z-50 h-screen text-white md:p-2 md:py-5 justify-between shadow-lg ${
        isCollapsed
          ? "md:w-16 w-0"
          : "md:w-72 w-full bg-sidebar/20 fixed md:relative transition-all duration-300"
      }`}
    >
      <div className="pt-6 px-2 md:pt-0 cursor-pointer md:z-50">
        {/* Top logo and collapse icon */}
        <div className="flex items-center mb-2 justify-between px-2">
          {!isCollapsed && (
            <img alt="pancea logo" width={30} height={30} src="/logonew.png" />
          )}
          <button
            onClick={onToggle}
            data-slot="sidebar-trigger"
            className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive cursor-pointer hover:text-accent-foreground dark:hover:bg-accent/50 size-7 -ml-1"
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
              className="lucide lucide-panel-left cursor-pointer"
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
            <ChatHistory
              chats={chats}
              loading={chatsLoading}
              handleChatSelect={handleChatSelect}
              onRefreshChats={onRefreshChats}
              onRenameChat={onRenameChat}
              onDeleteChat={onDeleteChat}
            />
          </>
        )}
      </div>

      {/* Bottom nav links */}
      {!isCollapsed && (
        <div className="px-2 pb-4 border-t border-gray-700 pt-3 space-y-1">
          <Link to={apiKeyDashboardPath}>
            <SidebarItem
              icon={
                <svg width="18" height="18" fill="none" viewBox="0 0 24 24">
                  <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              }
              label="API Keys"
            />
          </Link>
          <Link to={usageDashboardPath}>
            <SidebarItem
              icon={
                <svg width="18" height="18" fill="none" viewBox="0 0 24 24">
                  <path d="M18 20V10M12 20V4M6 20v-6" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              }
              label="Usage"
            />
          </Link>
        </div>
      )}
    </aside>
  );
};

function SidebarItem({ icon, label }) {
  return (
    <div className="flex items-center gap-3 px-2 py-2 hover:bg-sidebar rounded cursor-pointer">
      <span className="w-6 h-6 flex items-center justify-center">{icon}</span>
      <span className="font-medium text-base">{label}</span>
    </div>
  );
}

export default Sidebar;
