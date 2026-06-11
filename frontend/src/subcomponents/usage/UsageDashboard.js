import React, { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import { getUsageHistory, useUsageHistory, useNumCredits } from "../../redux/UserSlice";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowLeft,
  faCoins,
  faChartBar,
  faDownload,
  faKey,
} from "@fortawesome/free-solid-svg-icons";
import { Button, Table, Badge } from "flowbite-react";
import { useNavigate, Link } from "react-router-dom";
import { apiKeyDashboardPath } from "../../constants/RouteConstants";

const ENDPOINT_CREDITS = {
  "/v1/chat/completions": 4,
  "/v1/question-answer": 5,
  "/v1/embeddings": 1,
  "/documents/upload": 1,
  "/documents/classify": 2,
  "/documents/extract": 3,
  "/documents/redact": 2,
};

function StatCard({ label, value, sub, color = "text-cyan-400" }) {
  return (
    <div className="bg-gray-800 rounded-xl p-5 flex flex-col gap-1 border border-gray-700">
      <span className="text-gray-400 text-sm">{label}</span>
      <span className={`text-3xl font-bold ${color}`}>{value}</span>
      {sub && <span className="text-gray-500 text-xs">{sub}</span>}
    </div>
  );
}

function DailyBarChart({ rows }) {
  if (!rows || rows.length === 0) return null;

  // Aggregate credits per day
  const byDay = {};
  rows.forEach((r) => {
    const day = r.created ? r.created.split("T")[0] : r.created;
    if (!day) return;
    byDay[day] = (byDay[day] || 0) + (r.credits_used || 0);
  });

  const days = Object.keys(byDay).sort().slice(-30);
  if (days.length === 0) return null;
  const maxVal = Math.max(...days.map((d) => byDay[d]), 1);

  return (
    <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <h3 className="text-gray-300 font-semibold mb-4">Daily Credit Usage (last 30 days)</h3>
      <div className="flex items-end gap-1 h-32">
        {days.map((day) => {
          const pct = (byDay[day] / maxVal) * 100;
          return (
            <div key={day} className="flex flex-col items-center flex-1 group relative">
              <div
                className="w-full bg-cyan-600 rounded-t hover:bg-cyan-500 transition-colors"
                style={{ height: `${pct}%`, minHeight: "2px" }}
              />
              <span className="text-gray-600 text-xs mt-1 rotate-45 origin-left hidden group-hover:block absolute bottom-0 left-0 bg-gray-900 px-1 rounded z-10 whitespace-nowrap">
                {day}: {byDay[day]} credits
              </span>
            </div>
          );
        })}
      </div>
      <div className="flex justify-between text-gray-600 text-xs mt-2">
        <span>{days[0]}</span>
        <span>{days[days.length - 1]}</span>
      </div>
    </div>
  );
}

export function UsageDashboard() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const numCredits = useNumCredits();
  const usageData = useUsageHistory();

  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [loading, setLoading] = useState(false);

  const fetchUsage = async () => {
    setLoading(true);
    await dispatch(getUsageHistory({ startDate, endDate }));
    setLoading(false);
  };

  useEffect(() => {
    fetchUsage();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const rows = usageData?.usage || [];
  const summary = usageData?.summary || {};

  const formatDate = (ds) => {
    if (!ds) return "—";
    try {
      return new Date(ds).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return ds;
    }
  };

  const exportCSV = () => {
    const header = "Date,Endpoint,Model,Input Tokens,Output Tokens,Credits Used\n";
    const body = rows
      .map(
        (r) =>
          `"${r.created}","${r.endpoint}","${r.model || ""}",${r.prompt_tokens || 0},${
            r.completion_tokens || 0
          },${r.credits_used || 0}`
      )
      .join("\n");
    const blob = new Blob([header + body], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `usage-${startDate}-to-${endDate}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Per-endpoint breakdown
  const endpointBreakdown = {};
  rows.forEach((r) => {
    const ep = r.endpoint || "unknown";
    if (!endpointBreakdown[ep]) {
      endpointBreakdown[ep] = { calls: 0, tokens: 0, credits: 0 };
    }
    endpointBreakdown[ep].calls += 1;
    endpointBreakdown[ep].tokens += (r.prompt_tokens || 0) + (r.completion_tokens || 0);
    endpointBreakdown[ep].credits += r.credits_used || 0;
  });

  return (
    <div className="min-h-screen bg-gray-900 pt-20">
      <div className="max-w-6xl mx-auto px-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-8 flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <Button
              color="gray"
              outline
              size="sm"
              onClick={() => navigate("/")}
              className="hover:bg-gray-700 border-gray-600 text-gray-300"
            >
              <FontAwesomeIcon className="w-4 h-4 mr-2" icon={faArrowLeft} />
              Back
            </Button>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <FontAwesomeIcon icon={faChartBar} className="text-cyan-400" />
              API Usage
            </h1>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <FontAwesomeIcon icon={faCoins} className="text-cyan-400" />
            <span className="text-cyan-400 font-medium">{numCredits} credits remaining</span>
            <Link to={apiKeyDashboardPath}>
              <Button color="gray" outline size="sm" className="border-gray-600 text-gray-300">
                <FontAwesomeIcon icon={faKey} className="w-4 h-4 mr-2" />
                Manage API Keys
              </Button>
            </Link>
          </div>
        </div>

        {/* Date range filter */}
        <div className="flex items-center gap-3 mb-6 flex-wrap">
          <label className="text-gray-400 text-sm">From</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="bg-gray-800 text-gray-200 border border-gray-600 rounded px-3 py-1.5 text-sm focus:ring-cyan-500 focus:border-cyan-500"
          />
          <label className="text-gray-400 text-sm">To</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="bg-gray-800 text-gray-200 border border-gray-600 rounded px-3 py-1.5 text-sm focus:ring-cyan-500 focus:border-cyan-500"
          />
          <Button
            size="sm"
            onClick={fetchUsage}
            disabled={loading}
            className="bg-cyan-600 hover:bg-cyan-700"
          >
            {loading ? "Loading…" : "Apply"}
          </Button>
          {rows.length > 0 && (
            <Button
              size="sm"
              color="gray"
              outline
              onClick={exportCSV}
              className="border-gray-600 text-gray-300"
            >
              <FontAwesomeIcon icon={faDownload} className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
          )}
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard
            label="Total Requests"
            value={summary.total_requests ?? rows.length}
            sub={`${startDate} – ${endDate}`}
          />
          <StatCard
            label="Credits Used"
            value={summary.total_credits_used ?? rows.reduce((s, r) => s + (r.credits_used || 0), 0)}
            color="text-yellow-400"
          />
          <StatCard
            label="Input Tokens"
            value={(summary.total_prompt_tokens ?? rows.reduce((s, r) => s + (r.prompt_tokens || 0), 0)).toLocaleString()}
            color="text-green-400"
          />
          <StatCard
            label="Output Tokens"
            value={(summary.total_completion_tokens ?? rows.reduce((s, r) => s + (r.completion_tokens || 0), 0)).toLocaleString()}
            color="text-purple-400"
          />
        </div>

        {/* Daily chart */}
        <DailyBarChart rows={rows} />

        {/* Per-endpoint breakdown */}
        {Object.keys(endpointBreakdown).length > 0 && (
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
            <h3 className="text-gray-300 font-semibold mb-4">Breakdown by Endpoint</h3>
            <div className="overflow-x-auto">
              <Table className="w-full bg-gray-800">
                <Table.Head>
                  <Table.HeadCell>Endpoint</Table.HeadCell>
                  <Table.HeadCell>Calls</Table.HeadCell>
                  <Table.HeadCell>Total Tokens</Table.HeadCell>
                  <Table.HeadCell>Credits Used</Table.HeadCell>
                  <Table.HeadCell>Credits/Call</Table.HeadCell>
                </Table.Head>
                <Table.Body className="divide-y divide-gray-700">
                  {Object.entries(endpointBreakdown)
                    .sort((a, b) => b[1].credits - a[1].credits)
                    .map(([ep, stats]) => (
                      <Table.Row key={ep} className="bg-gray-800 hover:bg-gray-750">
                        <Table.Cell className="font-mono text-gray-300 text-sm">{ep}</Table.Cell>
                        <Table.Cell className="text-gray-300">{stats.calls}</Table.Cell>
                        <Table.Cell className="text-gray-300">{stats.tokens.toLocaleString()}</Table.Cell>
                        <Table.Cell className="text-yellow-400 font-medium">{stats.credits}</Table.Cell>
                        <Table.Cell className="text-gray-400">
                          {(stats.credits / stats.calls).toFixed(1)}
                        </Table.Cell>
                      </Table.Row>
                    ))}
                </Table.Body>
              </Table>
            </div>
          </div>
        )}

        {/* Full request log */}
        <div className="bg-gray-800 rounded-xl border border-gray-700">
          <div className="p-5 border-b border-gray-700">
            <h3 className="text-gray-300 font-semibold">Request Log</h3>
          </div>
          {rows.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <FontAwesomeIcon icon={faChartBar} className="w-12 h-12 text-gray-600 mb-4" />
              <p className="text-gray-400 text-lg font-medium">No API usage in this period</p>
              <p className="text-gray-500 text-sm mt-1">
                Make your first API call using one of your keys to see usage here.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table className="w-full bg-gray-800">
                <Table.Head>
                  <Table.HeadCell>Date</Table.HeadCell>
                  <Table.HeadCell>Endpoint</Table.HeadCell>
                  <Table.HeadCell>Model</Table.HeadCell>
                  <Table.HeadCell>Input</Table.HeadCell>
                  <Table.HeadCell>Output</Table.HeadCell>
                  <Table.HeadCell>Credits</Table.HeadCell>
                </Table.Head>
                <Table.Body className="divide-y divide-gray-700">
                  {rows.slice().reverse().map((row, i) => (
                    <Table.Row key={i} className="bg-gray-800 hover:bg-gray-750">
                      <Table.Cell className="text-gray-400 text-sm whitespace-nowrap">
                        {formatDate(row.created)}
                      </Table.Cell>
                      <Table.Cell className="font-mono text-gray-300 text-sm">
                        {row.endpoint}
                      </Table.Cell>
                      <Table.Cell className="text-gray-400 text-sm">
                        {row.model ? (
                          <Badge color="indigo" size="sm">{row.model}</Badge>
                        ) : "—"}
                      </Table.Cell>
                      <Table.Cell className="text-gray-300 text-sm">
                        {(row.prompt_tokens || 0).toLocaleString()}
                      </Table.Cell>
                      <Table.Cell className="text-gray-300 text-sm">
                        {(row.completion_tokens || 0).toLocaleString()}
                      </Table.Cell>
                      <Table.Cell>
                        <Badge color="warning" size="sm">{row.credits_used || 0}</Badge>
                      </Table.Cell>
                    </Table.Row>
                  ))}
                </Table.Body>
              </Table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
