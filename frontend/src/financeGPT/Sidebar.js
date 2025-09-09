import React from "react";
import ChatHistory from "./components/ChatHistory";
import { Link } from "react-router-dom";

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
  )
};


const Sidebar = ({ handleChatSelect }) => {
  return (
    <aside className="flex flex-col h-screen w-72 bg-slate-900/20 text-white p-4 justify-between shadow-lg">
      <div className="mt-10">
        {/* Top logo and collapse icon */}
        <Link to="/">
          <SidebarItem icon={icons.newChat} label="New chat" />
        </Link>
        <ChatHistory handleChatSelect={handleChatSelect} />
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
