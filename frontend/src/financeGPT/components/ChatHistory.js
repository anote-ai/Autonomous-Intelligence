import { useState } from "react";
import { createPortal } from "react-dom";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Dropdown } from "flowbite-react";

function ChatHistory({
  chats = [],
  handleChatSelect,
  onRenameChat,
  onDeleteChat,
}) {
  const [chatIdToDelete, setChatIdToDelete] = useState(null);
  const [chatToDelete, setChatToDelete] = useState("");
  const [showConfirmPopupChat, setShowConfirmPopupChat] = useState(false);
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [chatIdToRename, setChatIdToRename] = useState(null);
  const [newChatName, setNewChatName] = useState("");
  const { id } = useParams();
  const navigate = useNavigate();

  const handleDeleteChat = async (chat_id) => {
    const chatToDelete =
      chats.find((chat) => chat.id === chat_id)?.chat_name || "Chat";
    setChatToDelete(chatToDelete);
    setChatIdToDelete(chat_id);
    setShowConfirmPopupChat(true);
  };

  const confirmDeleteChat = async () => {
    try {
      await onDeleteChat(chatIdToDelete);
      setShowConfirmPopupChat(false);

      if (Number(id) === chatIdToDelete) {
        navigate("/");
      }
    } catch (e) {
      console.error("Error during chat deletion", e);
    }
  };

  const cancelDeleteChat = () => {
    setShowConfirmPopupChat(false);
    setChatIdToDelete(null);
    setChatToDelete("");
  };

  const handleRenameChat = async (chat_id) => {
    const currentName =
      chats.find((chat) => chat.id === chat_id)?.chat_name || "";
    setNewChatName(currentName);
    setChatIdToRename(chat_id);
    setShowRenameModal(true);
  };

  const confirmRenameChat = async () => {
    if (!newChatName.trim()) return;

    try {
      await onRenameChat(chatIdToRename, newChatName.trim());
      setShowRenameModal(false);
    } catch (e) {
      console.error("Error during chat rename", e);
    }
  };

  const cancelRenameChat = () => {
    setShowRenameModal(false);
    setChatIdToRename(null);
    setNewChatName("");
  };

  return (
    <>
      {/* Delete Confirmation Modal - Rendered outside parent */}
      {showConfirmPopupChat &&
        createPortal(
          <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-[9999]">
            <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4 shadow-2xl">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">
                Delete Chat
              </h3>
              <p className="text-gray-600 mb-8 text-lg">
                Are you sure you want to delete "
                <span className="font-semibold">{chatToDelete}</span>"? This
                action cannot be undone.
              </p>
              <div className="flex space-x-4">
                <button
                  onClick={cancelDeleteChat}
                  className="flex-1 px-6 py-3 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDeleteChat}
                  className="flex-1 px-6 py-3 text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors font-medium"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}

      {/* Rename Modal - Rendered outside parent */}
      {showRenameModal &&
        createPortal(
          <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-[9999]">
            <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4 shadow-2xl">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">
                Rename Chat
              </h3>
              <input
                type="text"
                value={newChatName}
                onChange={(e) => setNewChatName(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 mb-8 text-lg"
                placeholder="Enter new chat name"
                autoFocus
                onKeyPress={(e) => {
                  if (e.key === "Enter") {
                    confirmRenameChat();
                  }
                }}
              />
              <div className="flex space-x-4">
                <button
                  onClick={cancelRenameChat}
                  className="flex-1 px-6 py-3 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmRenameChat}
                  className="flex-1 px-6 py-3 text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors font-medium"
                  disabled={!newChatName.trim()}
                >
                  Save
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}

      <div className="h-full py-2">
        <div className="flex justify-between items-center ">
          <h2
            className={`text-gray-400 text-sm ${
              chats.length === 0 ? "hidden" : ""
            } font-bold`}
          >
            Chat History
          </h2>
        </div>
        <ul className="flex-col  w-full h-full py-2 flex">
          {[...chats].reverse().map((chat, index) => (
            <li
              key={index}
              className={`group hover:bg-gray-800 rounded-md px-2 py-1 cursor-pointer text-sm mb-1 flex w-full items-center gap-4 relative ${
                chat.id === Number(id)
                  ? "bg-slate-200/20 text-gray-300"
                  : "text-white"
              }`}
            >
              <span className="cursor-pointer  w-full truncate max-w-2xl">
                <Link
                  onClick={() => {
                    handleChatSelect(chat.id);
                  }}
                  className="w-full text-turquoise-200 block"
                  to={`/chat/${chat.id}`}
                >
                  {chat.chat_name}
                </Link>
              </span>
              <Dropdown
                theme={{
                  arrowIcon: "hidden",
                }}
                inline
                label="···"
                placement="left"
                className="ml-auto z-50  group-hover:inline text-white bg-gray-200 border-none p-1"
              >
                <Dropdown.Item onClick={() => handleRenameChat(chat.id)}>
                  <div className="flex items-center gap-2">
                    <svg width="16" height="16" fill="none" viewBox="0 0 24 24">
                      <path
                        d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                    Rename
                  </div>
                </Dropdown.Item>
                <Dropdown.Item onClick={() => handleDeleteChat(chat.id)}>
                  <div className="flex items-center gap-2">
                    <svg width="16" height="16" fill="none" viewBox="0 0 24 24">
                      <path
                        d="M3 6h18m-2 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2m-6 5v6m4-6v6"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                    Delete
                  </div>
                </Dropdown.Item>
              </Dropdown>
            </li>
          ))}
          {chats.length === 0 && (
            <li className="flex items-center justify-center h-full">
              <div className="text-gray-400 text-sm text-center">
                No chat yet. Start a conversation!
              </div>
            </li>
          )}
        </ul>
      </div>
    </>
  );
}

export default ChatHistory;
