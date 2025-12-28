import { useState } from "react";
import { useTheme } from "../../hooks/useTheme";

function ProfileSettings({ isOpen, onClose, onLogout, userData }) {
  const [activeMenu, setActiveMenu] = useState("profile");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const { theme, toggleTheme } = useTheme();

  if (!isOpen) return null;

  const renderContent = () => {
    switch (activeMenu) {
      case "profile":
        return (
          <>
            <h1
              className={`text-2xl font-bold mb-6 ${
                theme === "dark" ? "text-white" : ""
              }`}
            >
              My Profile
            </h1>
            <div className="space-y-4">
              <div>
                <label
                  className={`block text-sm font-medium mb-2 ${
                    theme === "dark" ? "text-gray-300" : "text-gray-600"
                  }`}
                >
                  Username
                </label>
                <input
                  type="text"
                  value={userData?.name || ""}
                  readOnly
                  className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
                    theme === "dark"
                      ? "bg-gray-700 border-gray-600 text-white focus:ring-gray-500"
                      : "bg-gray-100 border-gray-300 text-gray-900 focus:ring-gray-400"
                  }`}
                />
              </div>
              <div>
                <label
                  className={`block text-sm font-medium mb-2 ${
                    theme === "dark" ? "text-gray-300" : "text-gray-600"
                  }`}
                >
                  Email
                </label>
                <input
                  type="email"
                  value={userData?.email || ""}
                  readOnly
                  className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
                    theme === "dark"
                      ? "bg-gray-700 border-gray-600 text-white placeholder:text-gray-400 focus:ring-gray-500"
                      : "bg-gray-100 border-gray-300 text-gray-900 placeholder:text-gray-500 focus:ring-gray-400"
                  }`}
                />
              </div>
            </div>
          </>
        );
      case "settings":
        return (
          <>
            <h1
              className={`text-2xl font-bold mb-6 ${
                theme === "dark" ? "text-white" : ""
              }`}
            >
              Settings
            </h1>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <span
                    className={`block font-medium ${
                      theme === "dark" ? "text-white" : ""
                    }`}
                  >
                    Dark Mode
                  </span>
                  <span
                    className={`text-sm ${
                      theme === "dark" ? "text-gray-400" : "text-gray-500"
                    }`}
                  >
                    {theme === "dark" ? "Enabled" : "Disabled"}
                  </span>
                </div>
                <button
                  onClick={toggleTheme}
                  className={`relative w-12 h-6 rounded-full transition-colors ${
                    theme === "dark" ? "bg-blue-600" : "bg-gray-300"
                  }`}
                >
                  <div
                    className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow-md transition-transform ${
                      theme === "dark" ? "translate-x-7" : "translate-x-1"
                    }`}
                  />
                </button>
              </div>
            </div>
          </>
        );
      case "subscription":
        return (
          <>
            <h1
              className={`text-2xl font-bold mb-6 ${
                theme === "dark" ? "text-white" : ""
              }`}
            >
              Subscription
            </h1>
            <div className="space-y-6">
              {/* Current Plan */}
              <div
                className={`p-4 rounded-lg border ${
                  theme === "dark"
                    ? "bg-gray-700/50 border-gray-600"
                    : "bg-gray-50 border-gray-200"
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <h3
                    className={`font-semibold ${
                      theme === "dark" ? "text-white" : "text-gray-900"
                    }`}
                  >
                    Current Plan: Free
                  </h3>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${
                      theme === "dark"
                        ? "bg-gray-600 text-gray-200"
                        : "bg-gray-200 text-gray-700"
                    }`}
                  >
                    Active
                  </span>
                </div>
                <p
                  className={`text-sm ${
                    theme === "dark" ? "text-gray-300" : "text-gray-600"
                  }`}
                >
                  You're currently on the free plan. Upgrade to unlock premium
                  features.
                </p>
              </div>

              {/* Upgrade Options */}
              <div className="grid md:grid-cols-2 gap-4">
                {/* Pro Plan */}
                <div
                  className={`p-6 rounded-lg border-2 transition-all ${
                    theme === "dark"
                      ? "bg-gray-700/30 border-blue-600 hover:border-blue-500"
                      : "bg-white border-blue-500 hover:border-blue-600"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <svg
                      className="w-6 h-6 text-blue-500"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 10V3L4 14h7v7l9-11h-7z"
                      />
                    </svg>
                    <h3
                      className={`text-xl font-bold ${
                        theme === "dark" ? "text-white" : "text-gray-900"
                      }`}
                    >
                      Pro
                    </h3>
                  </div>
                  <div className="mb-4">
                    <span
                      className={`text-3xl font-bold ${
                        theme === "dark" ? "text-white" : "text-gray-900"
                      }`}
                    >
                      $9.99
                    </span>
                    <span
                      className={`text-sm ${
                        theme === "dark" ? "text-gray-400" : "text-gray-500"
                      }`}
                    >
                      /month
                    </span>
                  </div>
                  <ul className="space-y-2 mb-6">
                    <li
                      className={`flex items-center gap-2 text-sm ${
                        theme === "dark" ? "text-gray-300" : "text-gray-600"
                      }`}
                    >
                      <svg
                        className="w-5 h-5 text-green-500"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      Unlimited projects
                    </li>
                    <li
                      className={`flex items-center gap-2 text-sm ${
                        theme === "dark" ? "text-gray-300" : "text-gray-600"
                      }`}
                    >
                      <svg
                        className="w-5 h-5 text-green-500"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      Priority support
                    </li>
                    <li
                      className={`flex items-center gap-2 text-sm ${
                        theme === "dark" ? "text-gray-300" : "text-gray-600"
                      }`}
                    >
                      <svg
                        className="w-5 h-5 text-green-500"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      Advanced analytics
                    </li>
                  </ul>
                  <button className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors">
                    Upgrade to Pro
                  </button>
                </div>

                {/* Enterprise Plan */}
                <div
                  className={`p-6 rounded-lg border transition-all ${
                    theme === "dark"
                      ? "bg-gray-700/30 border-gray-600 hover:border-purple-500"
                      : "bg-white border-gray-300 hover:border-purple-500"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <svg
                      className="w-6 h-6 text-purple-500"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                      />
                    </svg>
                    <h3
                      className={`text-xl font-bold ${
                        theme === "dark" ? "text-white" : "text-gray-900"
                      }`}
                    >
                      Enterprise
                    </h3>
                  </div>
                  <div className="mb-4">
                    <span
                      className={`text-3xl font-bold ${
                        theme === "dark" ? "text-white" : "text-gray-900"
                      }`}
                    >
                      Custom
                    </span>
                  </div>
                  <ul className="space-y-2 mb-6">
                    <li
                      className={`flex items-center gap-2 text-sm ${
                        theme === "dark" ? "text-gray-300" : "text-gray-600"
                      }`}
                    >
                      <svg
                        className="w-5 h-5 text-green-500"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      Everything in Pro
                    </li>
                    <li
                      className={`flex items-center gap-2 text-sm ${
                        theme === "dark" ? "text-gray-300" : "text-gray-600"
                      }`}
                    >
                      <svg
                        className="w-5 h-5 text-green-500"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      Dedicated support
                    </li>
                    <li
                      className={`flex items-center gap-2 text-sm ${
                        theme === "dark" ? "text-gray-300" : "text-gray-600"
                      }`}
                    >
                      <svg
                        className="w-5 h-5 text-green-500"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      Custom integrations
                    </li>
                  </ul>
                  <button
                    className={`w-full px-4 py-2 rounded-lg font-medium transition-colors ${
                      theme === "dark"
                        ? "bg-gray-700 hover:bg-gray-600 text-white"
                        : "bg-gray-200 hover:bg-gray-300 text-gray-900"
                    }`}
                  >
                    Contact Sales
                  </button>
                </div>
              </div>
            </div>
          </>
        );
      case "account":
        return (
          <>
            <h1
              className={`text-2xl font-bold mb-6 ${
                theme === "dark" ? "text-white" : ""
              }`}
            >
              My Account
            </h1>
            <div className="space-y-6">
              {/* Account Information */}
              <div
                className={`p-4 rounded-lg border ${
                  theme === "dark"
                    ? "bg-gray-700/50 border-gray-600"
                    : "bg-gray-50 border-gray-200"
                }`}
              >
                <h3
                  className={`font-semibold mb-2 ${
                    theme === "dark" ? "text-white" : "text-gray-900"
                  }`}
                >
                  Account Status
                </h3>
                <p
                  className={`text-sm ${
                    theme === "dark" ? "text-gray-300" : "text-gray-600"
                  }`}
                >
                  Your account is active and in good standing.
                </p>
              </div>

              {/* Account Details */}
              <div className="space-y-3">
                <div
                  className={`flex justify-between items-center py-3 border-b ${
                    theme === "dark" ? "border-gray-700" : "border-gray-200"
                  }`}
                >
                  <span
                    className={`text-sm ${
                      theme === "dark" ? "text-gray-300" : "text-gray-600"
                    }`}
                  >
                    Member since
                  </span>
                  <span
                    className={`font-medium ${
                      theme === "dark" ? "text-white" : "text-gray-900"
                    }`}
                  >
                    December 2025
                  </span>
                </div>
                <div
                  className={`flex justify-between items-center py-3 border-b ${
                    theme === "dark" ? "border-gray-700" : "border-gray-200"
                  }`}
                >
                  <span
                    className={`text-sm ${
                      theme === "dark" ? "text-gray-300" : "text-gray-600"
                    }`}
                  >
                    Account Type
                  </span>
                  <span
                    className={`font-medium ${
                      theme === "dark" ? "text-white" : "text-gray-900"
                    }`}
                  >
                    Free
                  </span>
                </div>
              </div>

              {/* Danger Zone */}
              <div
                className={`mt-8 p-4 rounded-lg border-2 ${
                  theme === "dark"
                    ? "bg-red-900/10 border-red-800"
                    : "bg-red-50 border-red-200"
                }`}
              >
                <h3
                  className={`font-semibold mb-2 flex items-center gap-2 ${
                    theme === "dark" ? "text-red-400" : "text-red-600"
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
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                  Danger Zone
                </h3>
                <p
                  className={`text-sm mb-4 ${
                    theme === "dark" ? "text-gray-300" : "text-gray-600"
                  }`}
                >
                  Once you delete your account, there is no going back. Please
                  be certain.
                </p>
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    theme === "dark"
                      ? "bg-red-600 hover:bg-red-700 text-white"
                      : "bg-red-600 hover:bg-red-700 text-white"
                  }`}
                >
                  Delete Account
                </button>
              </div>
            </div>
          </>
        );
      default:
        return null;
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0  backdrop-blur-md z-70 ${
          theme === "dark" ? "bg-opacity-40" : "bg-opacity-20"
        }`}
        onClick={onClose}
      />

      {/* Settings Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-80">
        <div
          className={`lg:rounded-lg shadow-2xl w-full lg:max-w-4xl h-full lg:h-4/5 flex overflow-hidden ${
            theme === "dark"
              ? "text-white bg-gray-800 border-gray-700"
              : "text-gray-900 bg-white border-gray-200"
          } border`}
        >
          {/* Left Sidebar */}
          <div
            className={`w-64 border-r p-4 flex flex-col ${
              theme === "dark"
                ? "bg-gray-900 border-gray-700"
                : "bg-gray-50 border-gray-200"
            }`}
          >
            {/* Profile Section */}
            <div className="mb-6">
              <button
                onClick={() => setActiveMenu("profile")}
                className={`w-full flex items-center gap-3 p-3 rounded-lg transition-all cursor-pointer ${
                  activeMenu === "profile"
                    ? theme === "dark"
                      ? "bg-gray-800 text-white"
                      : "bg-gray-200 text-gray-900"
                    : theme === "dark"
                    ? "hover:bg-gray-800"
                    : "hover:bg-gray-100"
                }`}
              >
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center ring-2 ${
                    theme === "dark"
                      ? "bg-linear-to-br from-blue-600 to-purple-600 ring-blue-500/50"
                      : "bg-linear-to-br from-blue-500 to-purple-500 ring-blue-400/50"
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
                </div>
                <div className="flex-1 text-left">
                  <div
                    className={`font-semibold ${
                      theme === "dark" ? "text-white" : "text-gray-900"
                    }`}
                  >
                    {userData?.name || "User"}
                  </div>
                  <span
                    className={`text-xs flex items-center gap-1 ${
                      theme === "dark" ? "text-blue-300" : "text-blue-600"
                    }`}
                  >
                    Edit Profile ✎
                  </span>
                </div>
              </button>
            </div>

            {/* Menu Items */}
            <div className="flex-1 space-y-1 overflow-y-auto">
              <button
                onClick={() => setActiveMenu("account")}
                className={`w-full text-left px-3 py-2 rounded transition-colors flex items-center gap-3 cursor-pointer ${
                  activeMenu === "account"
                    ? theme === "dark"
                      ? "bg-gray-800 text-white"
                      : "bg-gray-200 text-gray-900"
                    : theme === "dark"
                    ? "text-gray-300 hover:bg-gray-800"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                <span>🔐</span> My Account
              </button>
              <button
                onClick={() => setActiveMenu("subscription")}
                className={`w-full text-left px-3 py-2 rounded transition-colors flex items-center gap-3 cursor-pointer ${
                  activeMenu === "subscription"
                    ? theme === "dark"
                      ? "bg-gray-800 text-white"
                      : "bg-gray-200 text-gray-900"
                    : theme === "dark"
                    ? "text-gray-300 hover:bg-gray-800"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                <span>💳</span> Subscription
              </button>
              <button
                onClick={() => setActiveMenu("settings")}
                className={`w-full text-left px-3 py-2 rounded transition-colors flex items-center gap-3 cursor-pointer ${
                  activeMenu === "settings"
                    ? theme === "dark"
                      ? "bg-gray-800 text-white"
                      : "bg-gray-200 text-gray-900"
                    : theme === "dark"
                    ? "text-gray-300 hover:bg-gray-800"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                <span>⚙️</span> Settings
              </button>
            </div>

            {/* Log Out */}
            <div
              className={`mt-4 pt-4 border-t ${
                theme === "dark" ? "border-gray-700" : "border-gray-200"
              }`}
            >
              <button
                onClick={onLogout}
                className={`w-full text-left px-3 py-2 rounded transition-colors flex items-center gap-3 cursor-pointer ${
                  theme === "dark"
                    ? "text-gray-300 hover:bg-red-900/30 hover:text-red-400"
                    : "text-gray-700 hover:bg-red-100 hover:text-red-600"
                }`}
              >
                <span>🚪</span> Log Out
              </button>
            </div>
          </div>

          {/* Right Content Area */}
          <div
            className={`flex-1 p-8 overflow-y-auto relative ${
              theme === "dark" ? "bg-gray-800" : "bg-white"
            }`}
          >
            {/* Close Button */}
            <button
              onClick={onClose}
              className={`absolute top-4 right-4 p-2 rounded-full transition-colors cursor-pointer ${
                theme === "dark" ? "hover:bg-gray-700" : "hover:bg-gray-100"
              }`}
            >
              <svg
                className={`w-6 h-6 ${
                  theme === "dark" ? "text-gray-300" : "text-gray-600"
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>

            {renderContent()}
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-90 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-opacity-60 backdrop-blur-sm"
            onClick={() => setShowDeleteConfirm(false)}
          />
          <div
            className={`relative w-full max-w-md mx-4 p-6 rounded-lg shadow-2xl ${
              theme === "dark"
                ? "bg-gray-800 text-white"
                : "bg-white text-gray-900"
            }`}
          >
            <div className="flex items-center gap-3 mb-4">
              <div
                className={`w-12 h-12 rounded-full flex items-center justify-center ${
                  theme === "dark" ? "bg-red-900/30" : "bg-red-100"
                }`}
              >
                <svg
                  className={`w-6 h-6 ${
                    theme === "dark" ? "text-red-400" : "text-red-600"
                  }`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-bold">Delete Account?</h3>
            </div>
            <p
              className={`mb-6 ${
                theme === "dark" ? "text-gray-300" : "text-gray-600"
              }`}
            >
              Are you absolutely sure you want to delete your account? This
              action cannot be undone and all your data will be permanently
              removed.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  theme === "dark"
                    ? "bg-gray-700 hover:bg-gray-600 text-white"
                    : "bg-gray-200 hover:bg-gray-300 text-gray-900"
                }`}
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  // Handle account deletion
                  console.log("Account deleted");
                  setShowDeleteConfirm(false);
                  onLogout();
                }}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
              >
                Delete Account
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default ProfileSettings;
