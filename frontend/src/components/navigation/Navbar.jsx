import { useTheme } from "../../hooks/useTheme";

function Navbar({
  isSidebarOpen,
  setIsSidebarOpen,
  isProfileOpen,
  setIsProfileOpen,
  setIsAuthOpen,
  isAuthenticated,
}) {
  const { theme } = useTheme();

  return (
    <>
      {/* Open Sidebar Button (visible when closed) */}
      {isAuthenticated && !isSidebarOpen && (
        <button
          onClick={() => setIsSidebarOpen(true)}
          className={`fixed z-20 p-2 rounded-lg shadow-md hover:shadow-lg transition-shadow ${
            theme === "dark" ? "bg-gray-800" : "bg-white"
          }`}
          style={{ top: "24px", left: "24px" }}
        >
          <svg
            className={`w-5 h-5 ${
              theme === "dark" ? "text-gray-200" : "text-gray-700"
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
        </button>
      )}

      {/* Sign In Button (top right when not authenticated) */}
      {!isAuthenticated && (
        <div className="fixed top-6 right-6 z-40 flex gap-3">
          <button
            onClick={() => setIsAuthOpen(true)}
            className={`px-3 py-1.5 text-sm rounded-full hover:scale-105 transition-all duration-300 flex items-center justify-center shadow-md hover:shadow-lg font-medium ${
              theme === "dark"
                ? "bg-blue-600 hover:bg-blue-700 text-white"
                : "bg-blue-600 hover:bg-blue-700 text-white"
            }`}
          >
            Sign In
          </button>
        </div>
      )}

      {/* Expandable Sidebar Panel */}
      <div
        className={`fixed top-0 left-0 h-full w-64 border-r shadow-lg transition-transform duration-300 ease-in-out z-50 ${
          theme === "dark"
            ? "bg-gray-800 border-gray-700"
            : "bg-white border-gray-200"
        } ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="p-6 flex flex-col h-full">
          <div className="flex items-center justify-between mb-6">
            <button
              onClick={() => setIsSidebarOpen(false)}
              className={`p-2 rounded-lg transition-colors shadow-md ${
                theme === "dark"
                  ? "bg-gray-700 hover:bg-gray-600"
                  : "bg-white hover:bg-gray-100"
              }`}
            >
              <svg
                className={`w-5 h-5 ${
                  theme === "dark" ? "text-gray-200" : "text-gray-700"
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>

            <button
              className={`w-10 h-10 border rounded-full shadow-sm hover:shadow-md transition-shadow flex items-center justify-center ${
                theme === "dark"
                  ? "bg-gray-700 border-gray-600"
                  : "bg-white border-gray-200"
              }`}
            >
              <svg
                className={`w-4 h-4 ${
                  theme === "dark" ? "text-gray-200" : "text-gray-700"
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
          </div>

          <h2
            className={`text-xl font-semibold mb-2 ${
              theme === "dark" ? "text-white" : "text-gray-900"
            }`}
          >
            History
          </h2>

          {/* Chat History Section */}
          <div className="space-y-0 flex-1">
            <button
              className={`w-full text-left px-3 py-2 rounded-lg transition-colors text-sm ${
                theme === "dark"
                  ? "hover:bg-gray-700 text-gray-200"
                  : "hover:bg-gray-100 text-gray-700"
              }`}
            >
              New chat
            </button>
          </div>

          {/* Profile Section at Bottom */}
          <div
            className={`flex items-center gap-3 mt-6 pt-6 border-t ${
              theme === "dark" ? "border-gray-700" : "border-gray-200"
            }`}
          >
            <button
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              className={`w-12 h-12 bg-linear-to-br from-blue-500 to-purple-600 rounded-full hover:from-blue-600 hover:to-purple-700 transition-all duration-300 flex items-center justify-center shadow-lg hover:shadow-xl hover:scale-105 ${
                theme === "dark"
                  ? "ring-2 ring-gray-700"
                  : "ring-2 ring-gray-200"
              }`}
            >
              <svg
                className="w-6 h-6 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                />
              </svg>
            </button>
            <div>
              <p
                className={`font-semibold ${
                  theme === "dark" ? "text-white" : "text-gray-900"
                }`}
              >
                User Name
              </p>
              <p
                className={`text-sm ${
                  theme === "dark" ? "text-gray-400" : "text-gray-500"
                }`}
              >
                user@email.com
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default Navbar;
