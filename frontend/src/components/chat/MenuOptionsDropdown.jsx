import React from "react";

const MenuOptionsDropdown = ({
  showOptions,
  setShowOptions,
  isAuthenticated,
  dropdownRef,
  theme,
  menuOptions,
}) => (
  <div className="relative group flex" ref={dropdownRef}>
    <div className="flex items-center gap-2">
      <div className="relative group/button">
        <button
          onClick={() => isAuthenticated && setShowOptions(!showOptions)}
          disabled={!isAuthenticated}
          className={`p-2 rounded-full transition-colors ${
            isAuthenticated
              ? theme === "dark"
                ? "hover:bg-gray-600"
                : "hover:bg-gray-200"
              : "opacity-50 cursor-not-allowed"
          }`}
          aria-label="Open menu options"
        >
          <svg
            className={`w-4 h-4 ${
              theme === "dark" ? "text-gray-400" : "text-gray-500"
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
        </button>
        {!isAuthenticated && (
          <div className="absolute bottom-full left-0 mb-2 w-48 opacity-0 group-hover/button:opacity-100 pointer-events-none transition-opacity">
            <div
              className={`text-xs px-3 py-2 rounded shadow-lg ${
                theme === "dark"
                  ? "bg-gray-800 text-gray-200"
                  : "bg-gray-50 text-black"
              }`}
            >
              Login to use tools
            </div>
          </div>
        )}
      </div>
      {showOptions && (
        <div
          className={`absolute bottom-full left-0 mb-2 w-48 rounded-lg shadow-lg border overflow-hidden z-10 ${
            theme === "dark"
              ? "bg-gray-700 border-gray-600"
              : "bg-white border-gray-300"
          }`}
        >
          {menuOptions.map((option) => (
            <button
              key={option.id}
              className={`w-full cursor-pointer px-4 py-2 text-left flex items-center gap-2 transition-colors ${
                theme === "dark"
                  ? "text-white hover:bg-gray-600"
                  : "text-gray-900 hover:bg-gray-50"
              }`}
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d={option.icon}
                />
              </svg>
              <span className="text-sm">{option.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  </div>
);

export default MenuOptionsDropdown;
