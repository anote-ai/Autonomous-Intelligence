import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  View, Text, FlatList, TextInput, TouchableOpacity,
  StyleSheet, SafeAreaView, KeyboardAvoidingView, Platform,
  ActivityIndicator, Alert
} from "react-native";
import { router } from "expo-router";
import { useAppTheme, useAppAuth } from "./_layout";
import RocketLogo from "../src/components/RocketLogo";
import { BottomNav } from "../src/components/BottomNav";
import { getSessions, getSession, deleteSession, getPendingApprovals, Session, Message } from "../src/api";
import { API_BASE, MODELS } from "../src/constants";

export default function ChatScreen() {
  const { theme, dark, toggle } = useAppTheme();
  const { token, logout } = useAppAuth();

  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState(MODELS[0]);
  const [streaming, setStreaming] = useState(false);
  const [showSidebar, setShowSidebar] = useState(false);
  const [pendingApprovals, setPendingApprovals] = useState(0);
  const flatListRef = useRef<FlatList>(null);
  const abortRef = useRef<boolean>(false);

  const loadSessions = useCallback(async () => {
    try { setSessions(await getSessions()); } catch {}
  }, []);

  const loadPendingCount = useCallback(async () => {
    try { setPendingApprovals((await getPendingApprovals()).length); } catch {}
  }, []);

  const loadMessages = useCallback(async (id: string) => {
    try { setMessages(await getSession(id)); } catch {}
  }, []);

  useEffect(() => { loadSessions(); }, [loadSessions]);
  useEffect(() => { loadPendingCount(); }, [loadPendingCount]);

  const openSession = async (id: string) => {
    setActiveSession(id);
    await loadMessages(id);
    setShowSidebar(false);
  };

  const newChat = () => {
    setActiveSession(null);
    setMessages([]);
    setShowSidebar(false);
  };

  const doLogout = async () => {
    await logout();
    router.replace("/login");
  };

  const deleteSessionItem = async (id: string) => {
    try {
      await deleteSession(id);
      if (activeSession === id) newChat();
      loadSessions();
    } catch {}
  };

  const send = async () => {
    if (!input.trim() || streaming) return;
    const text = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setStreaming(true);
    abortRef.current = false;

    let assistantContent = "";
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      const res = await fetch(`${API_BASE}/api/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: text, session_id: activeSession, model }),
      });

      if (!res.ok || !res.body) throw new Error("Stream error");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (!abortRef.current) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6).trim();
          if (data === "[DONE]") break;
          try {
            const parsed = JSON.parse(data);
            if (parsed.type === "text") {
              assistantContent += parsed.text ?? "";
              const content = assistantContent;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = { role: "assistant", content };
                return updated;
              });
            }
            if (parsed.type === "session_id" && !activeSession) {
              setActiveSession(parsed.session_id);
              loadSessions();
            }
          } catch {}
        }
      }
    } catch (e: any) {
      if (!abortRef.current) {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: "Sorry, something went wrong." };
          return updated;
        });
      }
    } finally {
      setStreaming(false);
      loadSessions();
    }
  };

  const renderMessage = ({ item, index }: { item: Message; index: number }) => (
    <View style={[
      styles.messageRow,
      item.role === "user" ? styles.userRow : styles.assistantRow
    ]}>
      {item.role === "assistant" && (
        <View style={[styles.avatar, { backgroundColor: theme.surfaceAlt }]}>
          <RocketLogo size={18} bodyColor={theme.rocketBody} accentColor={theme.rocketAccent} />
        </View>
      )}
      <View style={[
        styles.bubble,
        item.role === "user"
          ? [styles.userBubble, { backgroundColor: theme.userBubble }]
          : styles.assistantBubble
      ]}>
        <Text style={[styles.messageText, { color: theme.text }]}>
          {item.content}
          {streaming && index === messages.length - 1 && item.role === "assistant" && item.content === "" ? "▋" : ""}
        </Text>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
      {/* Header */}
      <View style={[styles.header, { borderBottomColor: theme.border }]}>
        <TouchableOpacity onPress={() => setShowSidebar((s) => !s)} style={styles.headerBtn}>
          <Text style={{ fontSize: 20, color: theme.text }}>{"☰"}</Text>
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: theme.text }]} numberOfLines={1}>
          {MODELS.find((m) => m === model)?.split("-").slice(0, 2).join("-") ?? "Anote AI"}
        </Text>
        <TouchableOpacity onPress={toggle} style={styles.headerBtn}>
          <Text style={{ fontSize: 20 }}>{dark ? "☀️" : "🌙"}</Text>
        </TouchableOpacity>
      </View>

      {/* Sidebar overlay */}
      {showSidebar && (
        <TouchableOpacity
          style={styles.overlay}
          activeOpacity={1}
          onPress={() => setShowSidebar(false)}
        />
      )}
      {showSidebar && (
        <View style={[styles.sidebar, { backgroundColor: theme.surface }]}>
          <View style={styles.sidebarHeader}>
            <RocketLogo size={24} bodyColor={theme.rocketBody} accentColor={theme.rocketAccent} />
            <Text style={[styles.sidebarTitle, { color: theme.text }]}>Anote AI</Text>
          </View>
          <TouchableOpacity
            style={[styles.newChatBtn, { backgroundColor: theme.surfaceAlt }]}
            onPress={newChat}
          >
            <Text style={[{ color: theme.text, fontWeight: "600" }]}>+ New chat</Text>
          </TouchableOpacity>
          <FlatList
            data={sessions}
            keyExtractor={(s) => s.id}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={[
                  styles.sessionItem,
                  activeSession === item.id && { backgroundColor: theme.surfaceAlt }
                ]}
                onPress={() => openSession(item.id)}
                onLongPress={() =>
                  Alert.alert("Delete", "Delete this chat?", [
                    { text: "Cancel" },
                    { text: "Delete", style: "destructive", onPress: () => deleteSessionItem(item.id) },
                  ])
                }
              >
                <Text style={[styles.sessionTitle, { color: theme.text }]} numberOfLines={1}>
                  {item.title || "New chat"}
                </Text>
              </TouchableOpacity>
            )}
            style={styles.sessionList}
          />
          <TouchableOpacity style={styles.logoutBtn} onPress={doLogout}>
            <Text style={[{ color: theme.textMuted }]}>Sign out</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Messages */}
      {messages.length === 0 ? (
        <View style={styles.emptyState}>
          <RocketLogo size={64} bodyColor={theme.rocketBody} accentColor={theme.rocketAccent} />
          <Text style={[styles.emptyText, { color: theme.textMuted }]}>How can I help you today?</Text>
        </View>
      ) : (
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(_, i) => String(i)}
          renderItem={renderMessage}
          contentContainerStyle={styles.messageList}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
        />
      )}

      {/* Input */}
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={[styles.inputArea, { borderTopColor: theme.border }]}>
          <View style={[styles.inputRow, { backgroundColor: theme.inputBg, borderColor: theme.border }]}>
            <TextInput
              style={[styles.textInput, { color: theme.text }]}
              placeholder="Message Anote AI..."
              placeholderTextColor={theme.textMuted}
              value={input}
              onChangeText={setInput}
              multiline
              maxLength={4000}
            />
            <TouchableOpacity
              style={[styles.sendBtn, { backgroundColor: theme.sendButton, opacity: input.trim() || streaming ? 1 : 0.3 }]}
              onPress={streaming ? () => { abortRef.current = true; } : send}
              disabled={!streaming && !input.trim()}
            >
              <Text style={[styles.sendBtnText, { color: theme.sendButtonText }]}>
                {streaming ? "■" : "↑"}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
      <BottomNav active="chat" pendingApprovals={pendingApprovals} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 12, paddingVertical: 10, borderBottomWidth: 1 },
  headerBtn: { padding: 8 },
  headerTitle: { fontSize: 15, fontWeight: "600", flex: 1, textAlign: "center" },
  overlay: { ...StyleSheet.absoluteFillObject, backgroundColor: "rgba(0,0,0,0.4)", zIndex: 10 },
  sidebar: { position: "absolute", left: 0, top: 0, bottom: 0, width: 260, zIndex: 20, paddingTop: 56 },
  sidebarHeader: { flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 16, paddingBottom: 12 },
  sidebarTitle: { fontSize: 16, fontWeight: "600" },
  newChatBtn: { marginHorizontal: 8, marginBottom: 8, padding: 12, borderRadius: 8, alignItems: "center" },
  sessionList: { flex: 1 },
  sessionItem: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: 8, marginHorizontal: 8, marginBottom: 2 },
  sessionTitle: { fontSize: 13 },
  logoutBtn: { padding: 16, alignItems: "center" },
  emptyState: { flex: 1, justifyContent: "center", alignItems: "center", gap: 16 },
  emptyText: { fontSize: 16 },
  messageList: { paddingVertical: 16, paddingHorizontal: 12 },
  messageRow: { flexDirection: "row", marginBottom: 16, alignItems: "flex-start" },
  userRow: { justifyContent: "flex-end" },
  assistantRow: { justifyContent: "flex-start" },
  avatar: { width: 32, height: 32, borderRadius: 16, justifyContent: "center", alignItems: "center", marginRight: 8, marginTop: 2 },
  bubble: { maxWidth: "80%", borderRadius: 16, padding: 12 },
  userBubble: {},
  assistantBubble: {},
  messageText: { fontSize: 14, lineHeight: 20 },
  inputArea: { borderTopWidth: 1, padding: 12 },
  inputRow: { flexDirection: "row", alignItems: "flex-end", borderRadius: 16, borderWidth: 1, paddingLeft: 14, paddingRight: 6, paddingVertical: 6 },
  textInput: { flex: 1, fontSize: 14, maxHeight: 120, paddingVertical: 6 },
  sendBtn: { width: 36, height: 36, borderRadius: 18, justifyContent: "center", alignItems: "center", marginLeft: 6 },
  sendBtnText: { fontSize: 16, fontWeight: "bold" },
});
