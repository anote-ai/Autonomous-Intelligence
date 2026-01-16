import { useState, useEffect } from "react";
import { useTheme } from "../../hooks/useTheme";
import { useChatHistory } from "../../hooks/useChatHistory";
import { chatAPI } from "../../utils/api";
import { useNavigate, useParams } from "react-router-dom";
import ShareModal from "../common/ShareModal";

function Navbar({
  isSidebarOpen,
  setIsSidebarOpen,
  isProfileOpen,
  setIsProfileOpen,
  setIsAuthOpen,
  isAuthenticated,
}) {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const { chatId } = useParams();
  const {
    chatHistory,
    isLoadingChats,
    loadChatHistory,
    refreshChatHistory,
    notifyDeletedChat,
  } = useChatHistory();
  const [dropdownOpenId, setDropdownOpenId] = useState(null);
  const [renameModalOpen, setRenameModalOpen] = useState(false);
  const [renamingChat, setRenamingChat] = useState(null);
  const [newChatName, setNewChatName] = useState("");
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deletingChat, setDeletingChat] = useState(null);
  const [shareModalOpen, setShareModalOpen] = useState(false);
  const [sharingChat, setSharingChat] = useState(null);

  // Load chat history when component mounts and user is authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadChatHistory();
    }
  }, [isAuthenticated, loadChatHistory]);

  const handleChatClick = (chatUuid) => {
    navigate(`/chats/${chatUuid}`);
    // Optionally close sidebar on mobile
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  };

  const handleNewChat = () => {
    navigate("/");
    // Optionally close sidebar on mobile
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  };

  const handleDeleteChat = async (chatUuid, chatName, e) => {
    e.stopPropagation();
    setDeletingChat({ uuid: chatUuid, name: chatName });
    setDeleteModalOpen(true);
    setDropdownOpenId(null);
  };

  const confirmDelete = async () => {
    if (!deletingChat) return;

    try {
      await chatAPI.deleteChat(deletingChat.uuid);

      // Notify that chat was deleted
      notifyDeletedChat(deletingChat.uuid);

      // Refresh chat history after deletion
      refreshChatHistory();

      // If deleting the currently active chat, redirect to home
      if (chatId === deletingChat.uuid) {
        navigate("/");
      }

      setDeleteModalOpen(false);
      setDeletingChat(null);
    } catch {
      alert("Failed to delete chat");
    }
  };

  const handleRenameChat = async (chatUuid, currentName, e) => {
    e.stopPropagation();
    setRenamingChat({ uuid: chatUuid, name: currentName });
    setNewChatName(currentName);
    setRenameModalOpen(true);
    setDropdownOpenId(null);
  };

  const submitRename = async () => {
    if (!newChatName.trim() || !renamingChat) return;

    if (newChatName === renamingChat.name) {
      setRenameModalOpen(false);
      return;
    }

    try {
      await chatAPI.updateChat(renamingChat.uuid, newChatName);
      // Refresh chat history after rename
      refreshChatHistory();
      setRenameModalOpen(false);
      setRenamingChat(null);
      setNewChatName("");
    } catch (error) {
      console.error("Error renaming chat:", error);
      alert("Failed to rename chat");
    }
  };

  const handleRenameKeyPress = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      submitRename();
    } else if (e.key === "Escape") {
      setRenameModalOpen(false);
    }
  };

  const handleShareChat = async (chatUuid, chatName, e) => {
    e.stopPropagation();
    setSharingChat({ uuid: chatUuid, name: chatName });
    setShareModalOpen(true);
    setDropdownOpenId(null);
  };

  const handleDropdownToggle = (id) => {
    setDropdownOpenId(dropdownOpenId === id ? null : id);
  };

  return (
    <>
      {/* Open Sidebar Button (visible when closed) */}
      {isAuthenticated && !isSidebarOpen && (
        <button
          onClick={() => setIsSidebarOpen(true)}
          className={`fixed z-20 cursor-pointer p-2 rounded-lg top-6 left-6 shadow-md hover:shadow-lg transition-shadow ${
            theme === "dark" ? "bg-gray-800" : "bg-gray-50"
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
      )}

      {/* Sign In Button (top right when not authenticated) */}
      {!isAuthenticated && (
        <div className="fixed top-6 z-40 w-full px-4 md:px-0">
          <div className="max-w-5xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2">
              <img src="/logo.png" alt="Logo" className="h-8 w-auto" />
              <span className="text-xl font-bold text-gray-50 select-none">
                Panacea
              </span>
            </div>
            <button
              onClick={() => setIsAuthOpen(true)}
              className={`px-3 py-1.5 cursor-pointer text-sm rounded-md hover:scale-105 transition-all duration-300 flex items-center justify-center shadow-md hover:shadow-lg font-medium ${
                theme === "dark"
                  ? "bg-teal-500 hover:bg-teal-600 text-white"
                  : "bg-teal-500 hover:bg-teal-600 text-white"
              }`}
            >
              Sign In
            </button>
          </div>
        </div>
      )}

      {/* Expandable Sidebar Panel */}
      <div
        className={`fixed top-0 left-0 h-full w-64 border-r shadow-lg transition-transform duration-300 ease-in-out z-50 ${
          theme === "dark"
            ? "bg-gray-800 border-gray-700"
            : "bg-gray-50 border-gray-200"
        } ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className=" flex overflow-auto flex-col h-full">
          <div className="flex py-4 px-5 items-center  sticky top-0  justify-between">
            <div className="flex items-center gap-1">
              <img src="/logo.png" alt="Logo" className="h-8 w-auto" />
              <span className="text-lg font-bold text-gray-50 select-none">
                Panacea
              </span>
            </div>

            <button
              onClick={() => setIsSidebarOpen(false)}
              className={`p-1 cursor-pointer rounded-md transition-colors shadow-md ${
                theme === "dark"
                  ? "bg-gray-700 hover:bg-gray-600"
                  : "bg-gray-50 hover:bg-gray-100"
              }`}
            >
              <svg
                className={`w-6 h-6 ${
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
          </div>
          {/* Scrollable section: New Chat, History, Chat List */}
          <div className="flex overflow-auto px-5 h-full flex-col">
            <button
              onClick={handleNewChat}
              className={`flex items-center cursor-pointer gap-2 px-3 py-1.5 mb-4 w-full rounded-lg  transition-shadow text-sm font-normal text-left ${
                theme === "dark"
                  ? "bg-gray-800 border-gray-700 text-white hover:bg-gray-700"
                  : "bg-gray-50 border-gray-200 text-gray-900 hover:bg-gray-100"
              }`}
            >
              <svg
                className="w-5 h-5 mr-1 text-inherit"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M16.862 3.487a2.25 2.25 0 1 1 3.182 3.182l-9.193 9.193a2 2 0 0 1-.708.447l-3.327 1.109a.5.5 0 0 1-.634-.634l1.11-3.327a2 2 0 0 1 .446-.708l9.194-9.192zm0 0L19 5.625M18 14.25v4.25A1.5 1.5 0 0 1 16.5 20h-9A1.5 1.5 0 0 1 6 18.5v-9A1.5 1.5 0 0 1 7.5 8h4.25"
                />
              </svg>
              <span className="text-base ">New chat</span>
            </button>
            <h2
              className={`text-xl font-semibold  ${
                theme === "dark" ? "text-white" : "text-gray-900"
              }`}
            >
              <span className="text-sm text-gray-300">Your chats</span>
            </h2>
            {/* Chat History Section */}
            <div className="space-y-1 flex-1">
              {isLoadingChats ? (
                <div className="flex justify-center py-4">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                </div>
              ) : chatHistory.length === 0 ? (
                <p
                  className={`text-sm text-center py-4 ${
                    theme === "dark" ? "text-gray-400" : "text-gray-500"
                  }`}
                >
                  No chats yet
                </p>
              ) : (
                chatHistory.map((chat) => (
                  <div
                    key={chat.chat_uuid}
                    onClick={() => handleChatClick(chat.chat_uuid)}
                    className="relative group flex items-center justify-between px-3 py-1 rounded-lg transition-colors text-sm cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    <span
                      className={`truncate flex-1 ${
                        theme === "dark" ? "text-gray-200" : "text-gray-700"
                      }`}
                    >
                      {chat.name}
                    </span>
                    <button
                      className="p-1 ml-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDropdownToggle(chat.chat_uuid);
                      }}
                      tabIndex={0}
                      aria-label="Open chat options"
                    >
                      <svg
                        className="w-5 h-5 text-gray-400"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        viewBox="0 0 24 24"
                      >
                        <circle cx="5" cy="12" r="1.5" />
                        <circle cx="12" cy="12" r="1.5" />
                        <circle cx="19" cy="12" r="1.5" />
                      </svg>
                    </button>
                    {/* Dropdown menu */}
                    {dropdownOpenId === chat.chat_uuid && (
                      <div
                        className={`absolute right-0 top-8 z-50 w-32 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1 animate-fade-in`}
                      >
                        <button
                          onClick={(e) =>
                            handleShareChat(chat.chat_uuid, chat.name, e)
                          }
                          className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200"
                        >
                          Share
                        </button>
                        <button
                          onClick={(e) =>
                            handleRenameChat(chat.chat_uuid, chat.name, e)
                          }
                          className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200"
                        >
                          Rename
                        </button>
                        <button
                          onClick={(e) =>
                            handleDeleteChat(chat.chat_uuid, chat.name, e)
                          }
                          className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 text-red-600 dark:text-red-400"
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Profile Section at Bottom */}
          <button
            onClick={() => setIsProfileOpen(!isProfileOpen)}
            className={`flex px-6  sticky bottom-0  items-center  gap-3 hover:cursor-pointer w-full  p-2 text-left hover:opacity-80 transition-opacity ${
              theme === "dark" ? "border-gray-700" : "border-gray-200"
            }`}
          >
            <div
              className={`w-8 h-8 bg-linear-to-br from-blue-500 to-purple-600 rounded-full hover:from-blue-600 hover:to-purple-700 transition-all duration-300 flex items-center justify-center shadow-lg hover:shadow-xl hover:scale-105 ${
                theme === "dark"
                  ? "ring-2 ring-gray-700"
                  : "ring-2 ring-gray-200"
              }`}
            >
              <svg
                className="w-4 h-4 text-white"
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
            <div>
              <p
                className={`font-semibold text-sm ${
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
                Free Plan
              </p>
            </div>
          </button>
        </div>
      </div>

      {/* Rename Modal */}
      {renameModalOpen && (
        <div className="fixed inset-0 z-100 flex items-center justify-center bg-black bg-opacity-50">
          <div
            className={`w-full max-w-md mx-4 p-6 rounded-lg shadow-xl ${
              theme === "dark" ? "bg-gray-800" : "bg-white"
            }`}
          >
            <h3
              className={`text-lg font-semibold mb-4 ${
                theme === "dark" ? "text-white" : "text-gray-900"
              }`}
            >
              Rename Chat
            </h3>
            <input
              type="text"
              value={newChatName}
              onChange={(e) => setNewChatName(e.target.value)}
              onKeyDown={handleRenameKeyPress}
              autoFocus
              className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                theme === "dark"
                  ? "bg-gray-700 border-gray-600 text-white"
                  : "bg-white border-gray-300 text-gray-900"
              }`}
              placeholder="Enter new chat name"
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => {
                  setRenameModalOpen(false);
                  setRenamingChat(null);
                  setNewChatName("");
                }}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  theme === "dark"
                    ? "bg-gray-700 hover:bg-gray-600 text-gray-200"
                    : "bg-gray-200 hover:bg-gray-300 text-gray-700"
                }`}
              >
                Cancel
              </button>
              <button
                onClick={submitRename}
                disabled={!newChatName.trim()}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  !newChatName.trim()
                    ? "bg-gray-400 text-gray-200 cursor-not-allowed"
                    : "bg-blue-500 hover:bg-blue-600 text-white"
                }`}
              >
                Rename
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteModalOpen && deletingChat && (
        <div className="fixed inset-0 z-100 flex items-center justify-center bg-black bg-opacity-50">
          <div
            className={`w-full max-w-md mx-4 p-6 rounded-lg shadow-xl ${
              theme === "dark" ? "bg-gray-800" : "bg-white"
            }`}
          >
            <h3
              className={`text-lg font-semibold mb-4 ${
                theme === "dark" ? "text-white" : "text-gray-900"
              }`}
            >
              Delete Chat
            </h3>
            <p
              className={`mb-6 ${
                theme === "dark" ? "text-gray-300" : "text-gray-600"
              }`}
            >
              Are you sure you want to delete "{deletingChat.name}"? This action
              cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setDeleteModalOpen(false);
                  setDeletingChat(null);
                }}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  theme === "dark"
                    ? "bg-gray-700 hover:bg-gray-600 text-gray-200"
                    : "bg-gray-200 hover:bg-gray-300 text-gray-700"
                }`}
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="px-4 py-2 rounded-lg bg-red-500 hover:bg-red-600 text-white transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Share Modal */}
      <ShareModal
        isOpen={shareModalOpen}
        onClose={() => {
          setShareModalOpen(false);
          setSharingChat(null);
        }}
        chatUuid={sharingChat?.uuid}
        chatName={sharingChat?.name}
        theme={theme}
      />
    </>
  );
}

export default Navbar;
