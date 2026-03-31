/**
 * PlaybookView — read-only view of a shared chat snapshot.
 *
 * URL: /playbook/:uuid
 *
 * Fetches the shared messages via the existing backend endpoint, renders
 * them in a read-only chat UI, and optionally lets authenticated users
 * import the chat into their own workspace.
 */

import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faDownload,
  faLock,
  faCommentDots,
} from "@fortawesome/free-solid-svg-icons";
import { useUser } from "../../redux/UserSlice";
import fetcher from "../../http/RequestConfig";

export default function PlaybookView() {
  const { uuid } = useParams();
  const navigate = useNavigate();
  const user = useUser();

  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [importing, setImporting] = useState(false);

  // Fetch shared messages on mount
  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetcher("retrieve-shared-messages-from-chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ playbook_url: uuid }),
        });
        if (!res.ok) {
          setError("This playbook could not be found or has expired.");
          return;
        }
        const data = await res.json();
        setMessages(data.messages || []);
      } catch {
        setError("Failed to load the playbook. Please check your connection.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [uuid]);

  // Import: copies the shared chat into the user's own workspace
  const handleImport = async () => {
    if (!user) {
      navigate("/");
      return;
    }
    setImporting(true);
    try {
      const res = await fetcher(`playbook/${uuid}`, { method: "POST" });
      if (!res.ok) throw new Error("Import failed");
      const data = await res.json();
      const newChatId = data.new_chat_id;
      navigate(`/chat/${newChatId}`);
    } catch {
      alert("Failed to import. Please try again.");
    } finally {
      setImporting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-anoteblack-800 flex items-center justify-center">
        <div className="flex items-center gap-3 text-gray-400">
          <div className="w-5 h-5 border-2 border-gray-500 border-t-[#defe47] rounded-full animate-spin" />
          Loading playbook…
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-anoteblack-800 flex items-center justify-center">
        <div className="text-center text-red-400 space-y-3">
          <div className="text-5xl">🔗</div>
          <p className="text-lg font-medium">{error}</p>
          <button
            onClick={() => navigate("/")}
            className="mt-4 px-5 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
          >
            Go home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-anoteblack-800 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700 bg-gray-900/60 backdrop-blur">
        <div className="flex items-center gap-3">
          <FontAwesomeIcon
            icon={faLock}
            className="text-[#defe47] text-sm"
          />
          <span className="text-white font-semibold">Shared Playbook</span>
          <span className="text-xs text-gray-500 bg-gray-700 rounded-full px-2 py-0.5">
            Read-only
          </span>
        </div>

        <button
          onClick={handleImport}
          disabled={importing}
          className="flex items-center gap-2 px-4 py-2 bg-[#defe47] text-black text-sm font-semibold rounded-lg hover:bg-yellow-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {importing ? (
            <>
              <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
              Importing…
            </>
          ) : (
            <>
              <FontAwesomeIcon icon={faDownload} />
              {user ? "Import to my chats" : "Log in to import"}
            </>
          )}
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 py-16">
              <FontAwesomeIcon
                icon={faCommentDots}
                className="text-4xl mb-3 text-gray-600"
              />
              <p>This playbook has no messages.</p>
            </div>
          )}

          {messages.map((msg, idx) => {
            const isUser = msg.sent_from_user === 1;
            return (
              <div
                key={idx}
                className={`flex ${isUser ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow ${
                    isUser
                      ? "bg-[#222d3c] border border-[#2e3a4c] text-white rounded-br-none"
                      : "bg-[#181f29] border border-[#2e3a4c] text-white rounded-bl-none"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.message_text}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer nudge */}
      <div className="py-3 text-center text-xs text-gray-600 border-t border-gray-800">
        This is a read-only snapshot.{" "}
        {user ? (
          <button
            onClick={handleImport}
            className="text-[#defe47] hover:underline"
          >
            Import it to continue the conversation.
          </button>
        ) : (
          <button
            onClick={() => navigate("/")}
            className="text-[#defe47] hover:underline"
          >
            Log in to import and continue the conversation.
          </button>
        )}
      </div>
    </div>
  );
}
