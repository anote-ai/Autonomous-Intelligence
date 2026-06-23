import React, { useState, useEffect, useCallback } from "react";
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  SafeAreaView, RefreshControl, ActivityIndicator,
} from "react-native";
import { router } from "expo-router";
import { useAppTheme, useAppAuth } from "./_layout";
import { BottomNav } from "../src/components/BottomNav";
import { getRuns, getPendingApprovals, Run, RunStatus } from "../src/api";

type Filter = "all" | "active" | "needs_action" | "completed";

const STATUS_CONFIG: Record<RunStatus, { label: string; color: string; dot: string }> = {
  running:           { label: "Running",          color: "#3B82F6", dot: "🔵" },
  paused:            { label: "Paused",            color: "#F59E0B", dot: "🟡" },
  awaiting_approval: { label: "Needs Approval",    color: "#8B5CF6", dot: "🟣" },
  failed:            { label: "Failed",            color: "#EF4444", dot: "🔴" },
  completed:         { label: "Completed",         color: "#10B981", dot: "🟢" },
};

function needsAction(status: RunStatus) {
  return status === "awaiting_approval" || status === "failed";
}

function isActive(status: RunStatus) {
  return status === "running" || status === "paused";
}

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

export default function RunsScreen() {
  const { theme } = useAppTheme();
  const { token } = useAppAuth();
  const [runs, setRuns] = useState<Run[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [runList, approvals] = await Promise.all([getRuns(), getPendingApprovals()]);
      setRuns(runList);
      setPendingCount(approvals.length);
    } catch {
      setError("Could not load runs. Pull down to retry.");
    }
  }, []);

  useEffect(() => {
    if (!token) { router.replace("/login"); return; }
    fetchData().finally(() => setLoading(false));
  }, [token, fetchData]);

  // Poll running runs every 10 s
  useEffect(() => {
    const hasRunning = runs.some((r) => r.status === "running");
    if (!hasRunning) return;
    const id = setInterval(fetchData, 10000);
    return () => clearInterval(id);
  }, [runs, fetchData]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  }, [fetchData]);

  const filtered = runs.filter((r) => {
    if (filter === "active") return isActive(r.status);
    if (filter === "needs_action") return needsAction(r.status);
    if (filter === "completed") return r.status === "completed";
    return true;
  });

  const FILTERS: { key: Filter; label: string }[] = [
    { key: "all",          label: "All" },
    { key: "active",       label: "Active" },
    { key: "needs_action", label: "Needs Action" },
    { key: "completed",    label: "Done" },
  ];

  const renderRun = ({ item }: { item: Run }) => {
    const cfg = STATUS_CONFIG[item.status];
    const pct = item.steps_total > 0
      ? Math.round((item.steps_done / item.steps_total) * 100)
      : 0;
    return (
      <TouchableOpacity
        style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}
        onPress={() => router.push({ pathname: "/run/[id]", params: { id: item.id } })}
        accessibilityRole="button"
        accessibilityLabel={`${formatWorkflow(item.workflow)} run, status ${cfg.label}`}
      >
        <View style={styles.cardHeader}>
          <View style={styles.cardLeft}>
            <Text style={[styles.workflow, { color: theme.text }]} numberOfLines={1}>
              {formatWorkflow(item.workflow)}
            </Text>
            <View style={styles.statusRow}>
              <View style={[styles.statusDot, { backgroundColor: cfg.color }]} />
              <Text style={[styles.statusLabel, { color: cfg.color }]}>{cfg.label}</Text>
            </View>
          </View>
          <View style={styles.cardRight}>
            <Text style={[styles.timestamp, { color: theme.textMuted }]}>
              {relativeTime(item.updated_at)}
            </Text>
            <Text style={{ color: theme.textMuted, fontSize: 18 }}>›</Text>
          </View>
        </View>

        {/* Progress bar */}
        {item.steps_total > 0 && (
          <View style={styles.progressWrap}>
            <View style={[styles.progressTrack, { backgroundColor: theme.surfaceAlt }]}>
              <View style={[styles.progressFill, { backgroundColor: cfg.color, width: `${pct}%` }]} />
            </View>
            <Text style={[styles.progressText, { color: theme.textMuted }]}>
              {item.steps_done}/{item.steps_total} steps
            </Text>
          </View>
        )}

        {item.artifact_count > 0 && (
          <Text style={[styles.artifacts, { color: theme.textMuted }]}>
            {item.artifact_count} artifact{item.artifact_count !== 1 ? "s" : ""}
          </Text>
        )}

        {item.error && (
          <Text style={[styles.errorText, { color: "#EF4444" }]} numberOfLines={1}>
            {item.error}
          </Text>
        )}
      </TouchableOpacity>
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={theme.text} />
        </View>
        <BottomNav active="runs" pendingApprovals={pendingCount} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
      {/* Header */}
      <View style={[styles.header, { borderBottomColor: theme.border }]}>
        <Text style={[styles.headerTitle, { color: theme.text }]}>Runs</Text>
        <TouchableOpacity onPress={onRefresh} style={styles.headerBtn} accessibilityLabel="Refresh runs">
          <Text style={{ fontSize: 18 }}>↻</Text>
        </TouchableOpacity>
      </View>

      {/* Filter chips */}
      <View style={[styles.filters, { borderBottomColor: theme.border }]}>
        {FILTERS.map((f) => (
          <TouchableOpacity
            key={f.key}
            style={[
              styles.chip,
              { borderColor: theme.border, backgroundColor: filter === f.key ? theme.text : "transparent" },
            ]}
            onPress={() => setFilter(f.key)}
            accessibilityRole="radio"
            accessibilityState={{ selected: filter === f.key }}
          >
            <Text style={[styles.chipText, { color: filter === f.key ? theme.background : theme.textMuted }]}>
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {error ? (
        <View style={styles.center}>
          <Text style={[styles.emptyText, { color: theme.textMuted }]}>{error}</Text>
        </View>
      ) : filtered.length === 0 ? (
        <View style={styles.center}>
          <Text style={{ fontSize: 40 }}>⚡</Text>
          <Text style={[styles.emptyText, { color: theme.textMuted }]}>
            {filter === "all" ? "No runs yet" : `No ${filter.replace("_", " ")} runs`}
          </Text>
        </View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(r) => r.id}
          renderItem={renderRun}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        />
      )}

      <BottomNav active="runs" pendingApprovals={pendingCount} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  center: { flex: 1, justifyContent: "center", alignItems: "center", gap: 12 },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1,
  },
  headerTitle: { fontSize: 20, fontWeight: "700" },
  headerBtn: { padding: 8 },
  filters: {
    flexDirection: "row", paddingHorizontal: 12, paddingVertical: 8,
    gap: 8, borderBottomWidth: 1,
  },
  chip: {
    paddingHorizontal: 10, paddingVertical: 4, borderRadius: 16, borderWidth: 1,
  },
  chipText: { fontSize: 12, fontWeight: "500" },
  list: { padding: 12, gap: 10 },
  card: {
    borderRadius: 12, borderWidth: 1, padding: 14, gap: 10,
  },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" },
  cardLeft: { flex: 1, gap: 4 },
  cardRight: { alignItems: "flex-end", gap: 4, paddingLeft: 8 },
  workflow: { fontSize: 15, fontWeight: "600" },
  statusRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  statusLabel: { fontSize: 12, fontWeight: "500" },
  timestamp: { fontSize: 12 },
  progressWrap: { gap: 4 },
  progressTrack: { height: 4, borderRadius: 2, overflow: "hidden" },
  progressFill: { height: 4, borderRadius: 2 },
  progressText: { fontSize: 11 },
  artifacts: { fontSize: 11 },
  errorText: { fontSize: 12 },
  emptyText: { fontSize: 15 },
});
