import React from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { router } from "expo-router";
import { useAppTheme } from "../../app/_layout";

export type NavTab = "chat" | "runs" | "approvals";

interface Props {
  active: NavTab;
  pendingApprovals?: number;
}

const TABS: { key: NavTab; label: string; icon: string; route: string }[] = [
  { key: "chat",      label: "Chat",      icon: "💬", route: "/chat" },
  { key: "runs",      label: "Runs",      icon: "⚡", route: "/runs" },
  { key: "approvals", label: "Approvals", icon: "✅", route: "/approvals" },
];

export function BottomNav({ active, pendingApprovals = 0 }: Props) {
  const { theme } = useAppTheme();

  return (
    <View style={[styles.bar, { backgroundColor: theme.surface, borderTopColor: theme.border }]}>
      {TABS.map((tab) => {
        const isActive = tab.key === active;
        const showBadge = tab.key === "approvals" && pendingApprovals > 0;
        return (
          <TouchableOpacity
            key={tab.key}
            style={styles.tab}
            onPress={() => { if (!isActive) router.replace(tab.route as any); }}
            accessibilityRole="tab"
            accessibilityState={{ selected: isActive }}
            accessibilityLabel={tab.label}
          >
            <View style={styles.iconWrap}>
              <Text style={styles.icon}>{tab.icon}</Text>
              {showBadge && (
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>
                    {pendingApprovals > 9 ? "9+" : String(pendingApprovals)}
                  </Text>
                </View>
              )}
            </View>
            <Text style={[styles.label, { color: isActive ? theme.text : theme.textMuted }]}>
              {tab.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: "row",
    borderTopWidth: 1,
    paddingBottom: 4,
  },
  tab: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 8,
    gap: 2,
  },
  iconWrap: {
    position: "relative",
    width: 28,
    height: 28,
    alignItems: "center",
    justifyContent: "center",
  },
  icon: { fontSize: 20 },
  badge: {
    position: "absolute",
    top: -4,
    right: -8,
    backgroundColor: "#EF4444",
    borderRadius: 8,
    minWidth: 16,
    height: 16,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 3,
  },
  badgeText: { color: "#fff", fontSize: 10, fontWeight: "700" },
  label: { fontSize: 11, fontWeight: "500" },
});
