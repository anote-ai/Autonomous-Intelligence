import React, { useState, useEffect, useCallback } from "react";
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  SafeAreaView, RefreshControl, ActivityIndicator, Alert, TextInput, Modal,
} from "react-native";
import { router } from "expo-router";
import { useAppTheme, useAppAuth } from "./_layout";
import { BottomNav } from "../src/components/BottomNav";
import { getPendingApprovals, approveRun, rejectRun, ApprovalRequest } from "../src/api";

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function formatWorkflow(name: string): string {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ApprovalsScreen() {
  const { theme } = useAppTheme();
  const { token } = useAppAuth();
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState<string | null>(null);

  // Reject modal state
  const [rejectTarget, setRejectTarget] = useState<ApprovalRequest | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const fetchApprovals = useCallback(async () => {
    try {
      setError(null);
      setApprovals(await getPendingApprovals());
    } catch {
      setError("Could not load approvals.");
    }
  }, []);

  useEffect(() => {
    if (!token) { router.replace("/login"); return; }
    fetchApprovals().finally(() => setLoading(false));
  }, [token, fetchApprovals]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchApprovals();
    setRefreshing(false);
  }, [fetchApprovals]);

  const handleApprove = async (item: ApprovalRequest) => {
    Alert.alert(
      "Approve run",
      `Approve "${formatWorkflow(item.workflow)}"?\n\n${item.message}`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Approve",
          onPress: async () => {
            setActing(item.id);
            try {
              await approveRun(item.run_id, item.id);
              setApprovals((prev) => prev.filter((a) => a.id !== item.id));
            } catch {
              Alert.alert("Error", "Could not approve. Please try again.");
            } finally {
              setActing(null);
            }
          },
        },
      ]
    );
  };

  const handleRejectConfirm = async () => {
    if (!rejectTarget) return;
    if (!rejectReason.trim()) {
      Alert.alert("Reason required", "Please enter a reason for rejection.");
      return;
    }
    const target = rejectTarget;
    setRejectTarget(null);
    setActing(target.id);
    try {
      await rejectRun(target.run_id, target.id, rejectReason.trim());
      setApprovals((prev) => prev.filter((a) => a.id !== target.id));
    } catch {
      Alert.alert("Error", "Could not reject. Please try again.");
    } finally {
      setActing(null);
      setRejectReason("");
    }
  };

  const renderItem = ({ item }: { item: ApprovalRequest }) => {
    const isActing = acting === item.id;
    return (
      <View style={[styles.card, { backgroundColor: theme.surface, borderColor: "#8B5CF6" }]}>
        {/* Tap card header to go to full run detail */}
        <TouchableOpacity
          onPress={() => router.push({ pathname: "/run/[id]", params: { id: item.run_id } })}
          accessibilityRole="button"
          accessibilityLabel={`View ${formatWorkflow(item.workflow)} run detail`}
        >
          <View style={styles.cardHeader}>
            <View style={styles.cardLeft}>
              <Text style={[styles.workflow, { color: theme.text }]} numberOfLines={1}>
                {formatWorkflow(item.workflow)}
              </Text>
              <Text style={[styles.time, { color: theme.textMuted }]}>
                Requested {relativeTime(item.created_at)}
              </Text>
            </View>
            <Text style={[styles.arrow, { color: theme.textMuted }]}>›</Text>
          </View>
          <Text style={[styles.message, { color: theme.text }]} numberOfLines={3}>
            {item.message}
          </Text>
          {item.context ? (
            <Text style={[styles.context, { color: theme.textMuted }]} numberOfLines={2}>
              {item.context}
            </Text>
          ) : null}
        </TouchableOpacity>

        {/* Action buttons */}
        <View style={styles.actions}>
          <TouchableOpacity
            style={[styles.btn, styles.rejectBtn, { borderColor: "#EF4444" }]}
            onPress={() => { setRejectTarget(item); setRejectReason(""); }}
            disabled={isActing}
            accessibilityRole="button"
            accessibilityLabel={`Reject ${formatWorkflow(item.workflow)}`}
          >
            <Text style={[styles.btnText, { color: "#EF4444" }]}>✗  Reject</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.btn, styles.approveBtn, { backgroundColor: "#10B981", opacity: isActing ? 0.5 : 1 }]}
            onPress={() => handleApprove(item)}
            disabled={isActing}
            accessibilityRole="button"
            accessibilityLabel={`Approve ${formatWorkflow(item.workflow)}`}
          >
            <Text style={[styles.btnText, { color: "#fff" }]}>
              {isActing ? "…" : "✓  Approve"}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={theme.text} />
        </View>
        <BottomNav active="approvals" pendingApprovals={0} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
      {/* Header */}
      <View style={[styles.header, { borderBottomColor: theme.border }]}>
        <View style={styles.headerLeft}>
          <Text style={[styles.headerTitle, { color: theme.text }]}>Approvals</Text>
          {approvals.length > 0 && (
            <View style={styles.headerBadge}>
              <Text style={styles.headerBadgeText}>{approvals.length}</Text>
            </View>
          )}
        </View>
        <TouchableOpacity onPress={onRefresh} style={styles.headerBtn} accessibilityLabel="Refresh">
          <Text style={{ fontSize: 18 }}>↻</Text>
        </TouchableOpacity>
      </View>

      {error ? (
        <View style={styles.center}>
          <Text style={[styles.emptyText, { color: theme.textMuted }]}>{error}</Text>
        </View>
      ) : approvals.length === 0 ? (
        <View style={styles.center}>
          <Text style={{ fontSize: 40 }}>✅</Text>
          <Text style={[styles.emptyText, { color: theme.textMuted }]}>All caught up!</Text>
          <Text style={[styles.emptySubtext, { color: theme.textMuted }]}>
            No runs waiting for your approval
          </Text>
        </View>
      ) : (
        <FlatList
          data={approvals}
          keyExtractor={(a) => a.id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        />
      )}

      {/* Reject reason modal */}
      <Modal
        visible={!!rejectTarget}
        transparent
        animationType="slide"
        onRequestClose={() => setRejectTarget(null)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setRejectTarget(null)}
        />
        <View style={[styles.modalSheet, { backgroundColor: theme.surface }]}>
          <Text style={[styles.modalTitle, { color: theme.text }]}>Reject run</Text>
          <Text style={[styles.modalSub, { color: theme.textMuted }]}>
            This action will be logged in the audit trail.
          </Text>
          <TextInput
            style={[styles.reasonInput, { color: theme.text, borderColor: theme.border, backgroundColor: theme.inputBg }]}
            placeholder="Reason for rejection…"
            placeholderTextColor={theme.textMuted}
            value={rejectReason}
            onChangeText={setRejectReason}
            multiline
            maxLength={500}
            autoFocus
          />
          <View style={styles.modalActions}>
            <TouchableOpacity
              style={[styles.modalBtn, { borderColor: theme.border }]}
              onPress={() => setRejectTarget(null)}
            >
              <Text style={{ color: theme.textMuted }}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.modalBtn, { backgroundColor: "#EF4444" }]}
              onPress={handleRejectConfirm}
            >
              <Text style={{ color: "#fff", fontWeight: "600" }}>Confirm Reject</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      <BottomNav active="approvals" pendingApprovals={approvals.length} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  center: { flex: 1, justifyContent: "center", alignItems: "center", gap: 10 },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1,
  },
  headerLeft: { flexDirection: "row", alignItems: "center", gap: 8 },
  headerTitle: { fontSize: 20, fontWeight: "700" },
  headerBadge: {
    backgroundColor: "#8B5CF6", borderRadius: 10, minWidth: 20,
    height: 20, alignItems: "center", justifyContent: "center", paddingHorizontal: 5,
  },
  headerBadgeText: { color: "#fff", fontSize: 12, fontWeight: "700" },
  headerBtn: { padding: 8 },
  list: { padding: 12, gap: 12 },
  card: { borderRadius: 12, borderWidth: 2, padding: 14, gap: 12 },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" },
  cardLeft: { flex: 1, gap: 2 },
  arrow: { fontSize: 20 },
  workflow: { fontSize: 15, fontWeight: "600" },
  time: { fontSize: 12 },
  message: { fontSize: 14, lineHeight: 20 },
  context: { fontSize: 12, lineHeight: 18, fontStyle: "italic" },
  actions: { flexDirection: "row", gap: 10 },
  btn: { flex: 1, paddingVertical: 10, borderRadius: 8, alignItems: "center" },
  rejectBtn: { borderWidth: 1, backgroundColor: "transparent" },
  approveBtn: {},
  btnText: { fontSize: 14, fontWeight: "600" },
  emptyText: { fontSize: 16, fontWeight: "600" },
  emptySubtext: { fontSize: 14 },
  modalOverlay: {
    position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: "rgba(0,0,0,0.5)",
  },
  modalSheet: {
    position: "absolute", bottom: 0, left: 0, right: 0,
    borderTopLeftRadius: 20, borderTopRightRadius: 20,
    padding: 20, gap: 14,
  },
  modalTitle: { fontSize: 18, fontWeight: "700" },
  modalSub: { fontSize: 13 },
  reasonInput: {
    borderWidth: 1, borderRadius: 10, padding: 12,
    fontSize: 14, minHeight: 80, textAlignVertical: "top",
  },
  modalActions: { flexDirection: "row", gap: 10 },
  modalBtn: {
    flex: 1, paddingVertical: 12, borderRadius: 10, alignItems: "center", borderWidth: 1,
  },
});
