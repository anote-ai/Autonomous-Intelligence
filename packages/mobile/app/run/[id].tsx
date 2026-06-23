import React, { useState, useEffect, useCallback } from "react";
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  SafeAreaView, ActivityIndicator, Alert, TextInput, Modal,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useAppTheme, useAppAuth } from "../_layout";
import {
  getRunDetail, approveRun, rejectRun, pauseRun, resumeRun, retryRun,
  RunDetail, RunStep, Artifact, AuditEntry, RunStatus,
} from "../../src/api";

const MAX_STEPS_INLINE = 20;

const STATUS_CONFIG: Record<RunStatus, { label: string; color: string; bg: string }> = {
  running:           { label: "Running",       color: "#3B82F6", bg: "#EFF6FF" },
  paused:            { label: "Paused",         color: "#F59E0B", bg: "#FFFBEB" },
  awaiting_approval: { label: "Needs Approval", color: "#8B5CF6", bg: "#F5F3FF" },
  failed:            { label: "Failed",         color: "#EF4444", bg: "#FEF2F2" },
  completed:         { label: "Completed",      color: "#10B981", bg: "#ECFDF5" },
};

const STEP_ICONS: Record<string, string> = {
  pending: "○", running: "●", done: "✓", failed: "✗",
};
const STEP_COLORS: Record<string, string> = {
  pending: "#9CA3AF", running: "#3B82F6", done: "#10B981", failed: "#EF4444",
};

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

function formatBytes(b: number): string {
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1048576).toFixed(1)} MB`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StepRow({ step, theme }: { step: RunStep; theme: any }) {
  const [expanded, setExpanded] = useState(false);
  const color = STEP_COLORS[step.status];
  const icon = STEP_ICONS[step.status];
  const hasOutput = !!step.output;

  return (
    <TouchableOpacity
      onPress={() => hasOutput && setExpanded((e) => !e)}
      activeOpacity={hasOutput ? 0.7 : 1}
      accessibilityRole={hasOutput ? "button" : "text"}
      accessibilityLabel={`${step.name}, ${step.status}${step.latency_ms ? `, ${step.latency_ms}ms` : ""}`}
      accessibilityState={hasOutput ? { expanded } : undefined}
    >
      <View style={styles.stepRow}>
        <Text style={[styles.stepIcon, { color }]}>{icon}</Text>
        <View style={styles.stepMid}>
          <Text style={[styles.stepName, { color: theme.text }]} numberOfLines={expanded ? undefined : 1}>
            {step.name}
          </Text>
          {step.latency_ms !== undefined && (
            <Text style={[styles.stepMeta, { color: theme.textMuted }]}>{step.latency_ms} ms</Text>
          )}
        </View>
        {hasOutput && (
          <Text style={[styles.stepChevron, { color: theme.textMuted }]}>{expanded ? "∧" : "∨"}</Text>
        )}
      </View>
      {expanded && step.output && (
        <ScrollView
          horizontal
          style={[styles.outputScroll, { backgroundColor: theme.surfaceAlt }]}
          showsHorizontalScrollIndicator={false}
        >
          <Text style={[styles.outputText, { color: theme.text }]}>{step.output}</Text>
        </ScrollView>
      )}
    </TouchableOpacity>
  );
}

function ArtifactRow({ artifact, theme }: { artifact: Artifact; theme: any }) {
  const [expanded, setExpanded] = useState(false);
  const isPreviewable = artifact.type === "text" || artifact.type === "json";
  const isLarge = (artifact.size_bytes ?? 0) > 50_000;

  return (
    <TouchableOpacity
      onPress={() => isPreviewable && !isLarge && setExpanded((e) => !e)}
      activeOpacity={isPreviewable && !isLarge ? 0.7 : 1}
      accessibilityRole={isPreviewable ? "button" : "text"}
      accessibilityLabel={`Artifact: ${artifact.name}, type ${artifact.type}`}
    >
      <View style={[styles.artifactRow, { borderColor: theme.border }]}>
        <Text style={styles.artifactIcon}>
          {{ text: "📄", json: "📋", image: "🖼️", file: "📎" }[artifact.type] ?? "📎"}
        </Text>
        <View style={styles.artifactMid}>
          <Text style={[styles.artifactName, { color: theme.text }]} numberOfLines={1}>
            {artifact.name}
          </Text>
          {artifact.size_bytes !== undefined && (
            <Text style={[styles.artifactMeta, { color: theme.textMuted }]}>
              {formatBytes(artifact.size_bytes)}
              {isLarge ? " — too large to preview" : ""}
            </Text>
          )}
        </View>
        {isPreviewable && !isLarge && (
          <Text style={[styles.stepChevron, { color: theme.textMuted }]}>{expanded ? "∧" : "∨"}</Text>
        )}
      </View>
      {expanded && artifact.preview && (
        <ScrollView
          style={[styles.outputScroll, { backgroundColor: theme.surfaceAlt }]}
          nestedScrollEnabled
        >
          <Text style={[styles.outputText, { color: theme.text }]}>{artifact.preview}</Text>
        </ScrollView>
      )}
    </TouchableOpacity>
  );
}

function AuditRow({ entry, theme }: { entry: AuditEntry; theme: any }) {
  return (
    <View style={[styles.auditRow, { borderLeftColor: theme.border }]}>
      <Text style={[styles.auditAction, { color: theme.text }]}>{entry.action}</Text>
      <Text style={[styles.auditMeta, { color: theme.textMuted }]}>
        {entry.actor} · {relativeTime(entry.timestamp)}
      </Text>
      {entry.detail && (
        <Text style={[styles.auditDetail, { color: theme.textMuted }]}>{entry.detail}</Text>
      )}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Main screen
// ---------------------------------------------------------------------------

export default function RunDetailScreen() {
  const { theme } = useAppTheme();
  const { token } = useAppAuth();
  const { id } = useLocalSearchParams<{ id: string }>();

  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState(false);
  const [showAllSteps, setShowAllSteps] = useState(false);
  const [showAudit, setShowAudit] = useState(false);
  const [rejectVisible, setRejectVisible] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const fetchRun = useCallback(async () => {
    if (!id) return;
    try {
      setError(null);
      setRun(await getRunDetail(id));
    } catch {
      setError("Could not load run details.");
    }
  }, [id]);

  useEffect(() => {
    if (!token) { router.replace("/login"); return; }
    fetchRun().finally(() => setLoading(false));
  }, [token, fetchRun]);

  // Poll while running
  useEffect(() => {
    if (run?.status !== "running") return;
    const timer = setInterval(fetchRun, 5000);
    return () => clearInterval(timer);
  }, [run?.status, fetchRun]);

  const doAction = async (label: string, fn: () => Promise<void>) => {
    setActing(true);
    try {
      await fn();
      await fetchRun();
    } catch {
      Alert.alert("Error", `Could not ${label.toLowerCase()}. Please try again.`);
    } finally {
      setActing(false);
    }
  };

  const handleApprove = () => {
    if (!run?.approval) return;
    Alert.alert("Approve run", "Approve and continue this workflow?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Approve",
        onPress: () => doAction("Approve", () => approveRun(run.id, run.approval!.id)),
      },
    ]);
  };

  const handleRejectConfirm = () => {
    if (!run?.approval || !rejectReason.trim()) {
      Alert.alert("Reason required", "Enter a reason for rejection.");
      return;
    }
    setRejectVisible(false);
    doAction("Reject", () => rejectRun(run.id, run.approval!.id, rejectReason.trim()));
    setRejectReason("");
  };

  const handlePause = () =>
    doAction("Pause", () => pauseRun(run!.id));

  const handleResume = () =>
    doAction("Resume", () => resumeRun(run!.id));

  const handleRetry = () => {
    Alert.alert("Retry run", "Start this run again from the beginning?", [
      { text: "Cancel", style: "cancel" },
      { text: "Retry", onPress: () => doAction("Retry", () => retryRun(run!.id)) },
    ]);
  };

  if (loading || !run) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
        <View style={[styles.header, { borderBottomColor: theme.border }]}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
            <Text style={[styles.backText, { color: theme.text }]}>‹ Back</Text>
          </TouchableOpacity>
        </View>
        <View style={styles.center}>
          {error
            ? <Text style={[styles.errorMsg, { color: theme.textMuted }]}>{error}</Text>
            : <ActivityIndicator size="large" color={theme.text} />}
        </View>
      </SafeAreaView>
    );
  }

  const cfg = STATUS_CONFIG[run.status];
  const pct = run.steps_total > 0 ? Math.round((run.steps_done / run.steps_total) * 100) : 0;
  const visibleSteps = showAllSteps ? run.steps : run.steps.slice(0, MAX_STEPS_INLINE);
  const hiddenCount = run.steps.length - MAX_STEPS_INLINE;

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
      {/* Header */}
      <View style={[styles.header, { borderBottomColor: theme.border }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} accessibilityRole="button" accessibilityLabel="Go back">
          <Text style={[styles.backText, { color: theme.text }]}>‹ Back</Text>
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: theme.text }]} numberOfLines={1}>
          {formatWorkflow(run.workflow)}
        </Text>
        {/* Quick pause/resume in header for running runs */}
        {run.status === "running" && (
          <TouchableOpacity onPress={handlePause} disabled={acting} style={styles.headerAction} accessibilityLabel="Pause run">
            <Text style={{ fontSize: 18 }}>{acting ? "…" : "⏸"}</Text>
          </TouchableOpacity>
        )}
        {run.status === "paused" && (
          <TouchableOpacity onPress={handleResume} disabled={acting} style={styles.headerAction} accessibilityLabel="Resume run">
            <Text style={{ fontSize: 18 }}>{acting ? "…" : "▶"}</Text>
          </TouchableOpacity>
        )}
        {run.status !== "running" && run.status !== "paused" && <View style={styles.headerAction} />}
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Status banner */}
        <View style={[styles.statusBanner, { backgroundColor: cfg.bg, borderColor: cfg.color }]}>
          <Text style={[styles.statusLabel, { color: cfg.color }]}>{cfg.label}</Text>
          {run.steps_total > 0 && (
            <Text style={[styles.statusSub, { color: cfg.color }]}>
              {run.steps_done} / {run.steps_total} steps · {pct}%
            </Text>
          )}
        </View>

        {/* Progress bar */}
        {run.steps_total > 0 && (
          <View style={[styles.progressTrack, { backgroundColor: theme.surfaceAlt }]}>
            <View style={[styles.progressFill, { backgroundColor: cfg.color, width: `${pct}%` }]} />
          </View>
        )}

        {/* Error message */}
        {run.error && (
          <View style={[styles.errorBanner, { backgroundColor: "#FEF2F2", borderColor: "#EF4444" }]}>
            <Text style={styles.errorBannerTitle}>Error</Text>
            <Text style={styles.errorBannerText}>{run.error}</Text>
          </View>
        )}

        {/* Approval message */}
        {run.approval && (
          <View style={[styles.approvalBanner, { backgroundColor: "#F5F3FF", borderColor: "#8B5CF6" }]}>
            <Text style={styles.approvalTitle}>Approval Requested</Text>
            <Text style={styles.approvalMsg}>{run.approval.message}</Text>
            {run.approval.context ? (
              <Text style={styles.approvalCtx}>{run.approval.context}</Text>
            ) : null}
          </View>
        )}

        {/* Action buttons */}
        {(run.status === "awaiting_approval" || run.status === "failed") && (
          <View style={styles.actionRow}>
            {run.status === "awaiting_approval" && (
              <>
                <TouchableOpacity
                  style={[styles.actionBtn, { borderColor: "#EF4444" }]}
                  onPress={() => { setRejectReason(""); setRejectVisible(true); }}
                  disabled={acting}
                  accessibilityRole="button"
                  accessibilityLabel="Reject this run"
                >
                  <Text style={[styles.actionBtnText, { color: "#EF4444" }]}>✗  Reject</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.actionBtn, { backgroundColor: "#10B981", borderColor: "#10B981", opacity: acting ? 0.5 : 1 }]}
                  onPress={handleApprove}
                  disabled={acting}
                  accessibilityRole="button"
                  accessibilityLabel="Approve this run"
                >
                  <Text style={[styles.actionBtnText, { color: "#fff" }]}>
                    {acting ? "…" : "✓  Approve"}
                  </Text>
                </TouchableOpacity>
              </>
            )}
            {run.status === "failed" && (
              <TouchableOpacity
                style={[styles.actionBtn, styles.actionBtnFull, { backgroundColor: "#3B82F6", borderColor: "#3B82F6", opacity: acting ? 0.5 : 1 }]}
                onPress={handleRetry}
                disabled={acting}
                accessibilityRole="button"
                accessibilityLabel="Retry this run"
              >
                <Text style={[styles.actionBtnText, { color: "#fff" }]}>
                  {acting ? "Retrying…" : "↻  Retry"}
                </Text>
              </TouchableOpacity>
            )}
          </View>
        )}

        {/* Steps */}
        {run.steps.length > 0 && (
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>Steps</Text>
            <View style={[styles.sectionCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              {visibleSteps.map((step, i) => (
                <View key={step.id}>
                  <StepRow step={step} theme={theme} />
                  {i < visibleSteps.length - 1 && <View style={[styles.divider, { backgroundColor: theme.border }]} />}
                </View>
              ))}
              {!showAllSteps && hiddenCount > 0 && (
                <TouchableOpacity
                  style={styles.showMore}
                  onPress={() => setShowAllSteps(true)}
                  accessibilityRole="button"
                  accessibilityLabel={`Show ${hiddenCount} more steps`}
                >
                  <Text style={[styles.showMoreText, { color: theme.textMuted }]}>
                    Show {hiddenCount} more step{hiddenCount !== 1 ? "s" : ""} ∨
                  </Text>
                </TouchableOpacity>
              )}
              {showAllSteps && hiddenCount > 0 && (
                <TouchableOpacity style={styles.showMore} onPress={() => setShowAllSteps(false)}>
                  <Text style={[styles.showMoreText, { color: theme.textMuted }]}>Show less ∧</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>
        )}

        {/* Artifacts */}
        {run.artifacts.length > 0 && (
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>
              Artifacts ({run.artifacts.length})
            </Text>
            <View style={[styles.sectionCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              {run.artifacts.map((a, i) => (
                <View key={a.id}>
                  <ArtifactRow artifact={a} theme={theme} />
                  {i < run.artifacts.length - 1 && <View style={[styles.divider, { backgroundColor: theme.border }]} />}
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Audit log */}
        {run.audit_log.length > 0 && (
          <View style={styles.section}>
            <TouchableOpacity
              onPress={() => setShowAudit((s) => !s)}
              accessibilityRole="button"
              accessibilityState={{ expanded: showAudit }}
              accessibilityLabel="Toggle audit log"
            >
              <Text style={[styles.sectionTitle, { color: theme.text }]}>
                Audit log ({run.audit_log.length}) {showAudit ? "∧" : "∨"}
              </Text>
            </TouchableOpacity>
            {showAudit && (
              <View style={[styles.sectionCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
                {run.audit_log.map((e) => (
                  <AuditRow key={e.id} entry={e} theme={theme} />
                ))}
              </View>
            )}
          </View>
        )}

        {/* Timestamps */}
        <View style={styles.timestamps}>
          <Text style={[styles.tsText, { color: theme.textMuted }]}>
            Started {relativeTime(run.created_at)} · Updated {relativeTime(run.updated_at)}
          </Text>
        </View>
      </ScrollView>

      {/* Reject modal */}
      <Modal visible={rejectVisible} transparent animationType="slide" onRequestClose={() => setRejectVisible(false)}>
        <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={() => setRejectVisible(false)} />
        <View style={[styles.modalSheet, { backgroundColor: theme.surface }]}>
          <Text style={[styles.modalTitle, { color: theme.text }]}>Reject run</Text>
          <Text style={[styles.modalSub, { color: theme.textMuted }]}>
            This action will be recorded in the audit trail.
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
            <TouchableOpacity style={[styles.modalBtn, { borderColor: theme.border }]} onPress={() => setRejectVisible(false)}>
              <Text style={{ color: theme.textMuted }}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.modalBtn, { backgroundColor: "#EF4444" }]} onPress={handleRejectConfirm}>
              <Text style={{ color: "#fff", fontWeight: "600" }}>Confirm Reject</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  errorMsg: { fontSize: 15, textAlign: "center", paddingHorizontal: 32 },
  header: {
    flexDirection: "row", alignItems: "center", paddingHorizontal: 12,
    paddingVertical: 10, borderBottomWidth: 1, gap: 8,
  },
  backBtn: { paddingVertical: 4, paddingRight: 8 },
  backText: { fontSize: 17 },
  headerTitle: { flex: 1, fontSize: 16, fontWeight: "600" },
  headerAction: { width: 36, alignItems: "center" },
  scroll: { padding: 16, gap: 16, paddingBottom: 40 },
  statusBanner: {
    borderRadius: 12, borderWidth: 1.5, paddingHorizontal: 14, paddingVertical: 10, gap: 2,
  },
  statusLabel: { fontSize: 16, fontWeight: "700" },
  statusSub: { fontSize: 13 },
  progressTrack: { height: 6, borderRadius: 3, overflow: "hidden" },
  progressFill: { height: 6, borderRadius: 3 },
  errorBanner: {
    borderRadius: 10, borderWidth: 1, padding: 12, gap: 4,
  },
  errorBannerTitle: { color: "#EF4444", fontWeight: "600", fontSize: 13 },
  errorBannerText: { color: "#EF4444", fontSize: 13 },
  approvalBanner: {
    borderRadius: 10, borderWidth: 1.5, padding: 14, gap: 6,
  },
  approvalTitle: { color: "#8B5CF6", fontWeight: "700", fontSize: 14 },
  approvalMsg: { color: "#5B21B6", fontSize: 14, lineHeight: 20 },
  approvalCtx: { color: "#7C3AED", fontSize: 12, lineHeight: 18, fontStyle: "italic" },
  actionRow: { flexDirection: "row", gap: 10 },
  actionBtn: {
    flex: 1, paddingVertical: 12, borderRadius: 10, alignItems: "center",
    borderWidth: 1.5, backgroundColor: "transparent",
  },
  actionBtnFull: { flex: 1 },
  actionBtnText: { fontSize: 15, fontWeight: "600" },
  section: { gap: 8 },
  sectionTitle: { fontSize: 15, fontWeight: "600" },
  sectionCard: { borderRadius: 12, borderWidth: 1, overflow: "hidden" },
  stepRow: {
    flexDirection: "row", alignItems: "center", paddingHorizontal: 14,
    paddingVertical: 10, gap: 10,
  },
  stepIcon: { fontSize: 16, width: 20, textAlign: "center" },
  stepMid: { flex: 1, gap: 1 },
  stepName: { fontSize: 14 },
  stepMeta: { fontSize: 11 },
  stepChevron: { fontSize: 14 },
  outputScroll: { borderRadius: 6, margin: 8, marginTop: 0, maxHeight: 150, padding: 10 },
  outputText: { fontSize: 12, fontFamily: "monospace" },
  divider: { height: 1, marginHorizontal: 14 },
  showMore: { paddingVertical: 10, alignItems: "center" },
  showMoreText: { fontSize: 13 },
  artifactRow: {
    flexDirection: "row", alignItems: "center", paddingHorizontal: 14,
    paddingVertical: 10, gap: 10, borderBottomWidth: 0,
  },
  artifactIcon: { fontSize: 20 },
  artifactMid: { flex: 1, gap: 1 },
  artifactName: { fontSize: 14 },
  artifactMeta: { fontSize: 11 },
  auditRow: { paddingLeft: 12, paddingVertical: 8, marginHorizontal: 10, borderLeftWidth: 2, gap: 1 },
  auditAction: { fontSize: 13, fontWeight: "600" },
  auditMeta: { fontSize: 11 },
  auditDetail: { fontSize: 12, fontStyle: "italic" },
  timestamps: { alignItems: "center" },
  tsText: { fontSize: 11 },
  modalOverlay: {
    position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: "rgba(0,0,0,0.5)",
  },
  modalSheet: {
    position: "absolute", bottom: 0, left: 0, right: 0,
    borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, gap: 14,
  },
  modalTitle: { fontSize: 18, fontWeight: "700" },
  modalSub: { fontSize: 13 },
  reasonInput: {
    borderWidth: 1, borderRadius: 10, padding: 12, fontSize: 14,
    minHeight: 80, textAlignVertical: "top",
  },
  modalActions: { flexDirection: "row", gap: 10 },
  modalBtn: {
    flex: 1, paddingVertical: 12, borderRadius: 10, alignItems: "center", borderWidth: 1,
  },
});
