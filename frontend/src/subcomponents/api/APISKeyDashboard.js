import React, { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import {
  useAPIKeys,
  generateAPIKey,
  deleteAPIKey,
  getAPIKeys,
  useNumCredits,
  getAPIUsageDashboard,
  getBillingSummary,
  useAPIUsageDashboard,
  useBillingSummary,
  createCreditCheckout,
} from "../../redux/UserSlice";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faTrash,
  faCopy,
  faArrowLeft,
  faPlus,
  faKey,
  faExclamationTriangle,
  faCoins,
} from "@fortawesome/free-solid-svg-icons";
import copy from "copy-to-clipboard";
import {
  Button,
  Table,
  Badge,
  Tooltip,
  Modal,
  TextInput,
  Label,
  Tabs,
} from "flowbite-react";
import { useNavigate } from "react-router-dom"

export function APISKeyDashboard() {
  const dispatch = useDispatch();
  const apiKeys = useAPIKeys();
  const numCredits = useNumCredits();
  const usageDashboard = useAPIUsageDashboard();
  const billingSummary = useBillingSummary();
  const [copiedKey, setCopiedKey] = useState(null);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState(null); // Track newly created key
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [rateLimit, setRateLimit] = useState(60);
  const [isCreating, setIsCreating] = useState(false);
  const navigate = useNavigate()

  const hasSufficientCredits = numCredits >= 1;

  const handleGenerateAPIKeys = () => {
    if (!hasSufficientCredits) {
      alert(
        "Insufficient credits. You need at least 1 credit to generate an API key."
      );
      return;
    }
    setShowCreateModal(true);
  };

  const handleCreateAPIKey = async () => {
    if (!keyName.trim()) {
      return;
    }

    setIsCreating(true);
    try {
      const result = await dispatch(generateAPIKey({
        name: keyName.trim(),
        expires_at: expiresAt || null,
        rate_limit_per_minute: Number(rateLimit) || 60,
      }));
      if (result.payload && !result.payload.error) {
        setNewlyCreatedKey(result.payload.key);
        setShowCreateModal(false);
        setKeyName("");
        setExpiresAt("");
        setRateLimit(60);
        // Auto-hide after 30 seconds for security
        setTimeout(() => setNewlyCreatedKey(null), 30000);
      } else if (result.payload && result.payload.error) {
        // Handle credit insufficiency or other errors
        alert(`Failed to create API key: ${result.payload.error}`);
      }
    } catch (error) {
      console.error("Failed to create API key:", error);
      alert("Failed to create API key. Please try again.");
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteAPIKey = (apiKeyId) => {
    dispatch(deleteAPIKey(apiKeyId));
  };

  const handleCopyAPIKey = (apiKey, keyId) => {
    copy(apiKey);
    setCopiedKey(keyId);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleBuyCredits = async (credits) => {
    const result = await dispatch(createCreditCheckout({ credits }));
    if (result.payload?.url) {
      window.location.assign(result.payload.url);
    } else {
      alert(result.payload?.error || "Failed to start checkout.");
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  useEffect(() => {
    dispatch(getAPIKeys());
    dispatch(getAPIUsageDashboard());
    dispatch(getBillingSummary());
  }, [dispatch]);

  const renderSummaryNumber = (value) => Number(value || 0).toLocaleString();

  return (
    <div className="min-h-screen bg-gray-900 pt-20">
      <div className="max-w-6xl mx-auto px-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
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
            <div className="flex items-center gap-2">
              <FontAwesomeIcon
                icon={faCoins}
                className={`w-4 h-4 ${
                  hasSufficientCredits ? "text-green-400" : "text-red-400"
                }`}
              />
              <span
                className={`text-sm font-medium ${
                  hasSufficientCredits ? "text-green-400" : "text-red-400"
                }`}
              >
                {numCredits} Credits
              </span>
            </div>
          </div>

          <div className="flex flex-col items-end gap-2">
            <Button
              onClick={handleGenerateAPIKeys}
              disabled={!hasSufficientCredits}
              className={`font-semibold ${
                hasSufficientCredits
                  ? "bg-cyan-600 hover:bg-cyan-700 text-white"
                  : "bg-gray-500 text-gray-300 cursor-not-allowed"
              }`}
            >
              <FontAwesomeIcon className="w-4 h-4 mr-2" icon={faPlus} />
              Create New API Key
            </Button>
            {!hasSufficientCredits && (
              <p className="text-red-400 text-xs text-right">
                Need at least 1 credit to create API keys
              </p>
            )}
          </div>
        </div>

        {/* Security Notice */}
        {newlyCreatedKey && (
          <Modal
            show={!!newlyCreatedKey}
            onClose={() => setNewlyCreatedKey(null)}
            size="lg"
          >
            <Modal.Header className="bg-gray-800 border-gray-700">
              <span className="text-white">API Key Created Successfully</span>
            </Modal.Header>
            <Modal.Body className="bg-gray-800">
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <FontAwesomeIcon
                    icon={faExclamationTriangle}
                    className="text-yellow-400 mt-1"
                  />
                  <div className="flex-1">
                    <h3 className="text-yellow-200 font-semibold mb-2">
                      Important Security Notice
                    </h3>
                    <p className="text-yellow-300 text-sm mb-4">
                      Your API key is shown below. This is the only time it will
                      be displayed. Make sure to copy and store it securely
                      before closing this modal.
                    </p>
                  </div>
                </div>

                <div className="bg-gray-700 p-4 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-gray-400 text-sm">Your API Key:</p>
                    <button
                      onClick={() =>
                        handleCopyAPIKey(newlyCreatedKey, "new-key")
                      }
                      className={`px-3 py-1 rounded text-sm transition-colors ${
                        copiedKey === "new-key"
                          ? "text-green-400 bg-green-900"
                          : "text-cyan-400 hover:bg-gray-600"
                      }`}
                    >
                      <FontAwesomeIcon icon={faCopy} className="w-3 h-3 mr-1" />
                      {copiedKey === "new-key" ? "Copied!" : "Copy"}
                    </button>
                  </div>
                  <code className="text-green-300 font-mono text-sm bg-gray-900 p-3 rounded block overflow-x-auto">
                    {newlyCreatedKey}
                  </code>
                </div>
              </div>
            </Modal.Body>
            <Modal.Footer className="bg-gray-800 border-gray-700">
              <Button
                onClick={() => setNewlyCreatedKey(null)}
                className="bg-cyan-600 hover:bg-cyan-700"
              >
                I've Saved My API Key
              </Button>
            </Modal.Footer>
          </Modal>
        )}

        <Tabs aria-label="API platform dashboard" variant="underline">
          <Tabs.Item active title="API Keys">
        <div>
          {apiKeys.length > 0 ? (
            <div className="overflow-x-auto">
              <Table className="w-full bg-black">
                <Table.Head>
                  <Table.HeadCell className="font-semibold">
                    Name
                  </Table.HeadCell>
                  <Table.HeadCell className="font-semibold">
                    API Key
                  </Table.HeadCell>
                  <Table.HeadCell className=" font-semibold">
                    Created
                  </Table.HeadCell>
                  <Table.HeadCell className=" font-semibold">
                    Last Used
                  </Table.HeadCell>
                  <Table.HeadCell className="font-semibold">
                    Status
                  </Table.HeadCell>
                  <Table.HeadCell className=" font-semibold">
                    Actions
                  </Table.HeadCell>
                </Table.Head>
                <Table.Body className="divide-y divide-gray-700">
                  {apiKeys.map((apiKey) => (
                    <Table.Row
                      key={apiKey.id}
                      className="bg-gray-800 border hover:bg-gray-750 transition-colors"
                    >
                      <Table.Cell className="text-gray-300 font-medium">
                        {apiKey.name || "Untitled Key"}
                      </Table.Cell>
                      <Table.Cell className="font-mono text-gray-300">
                        <div className="flex items-center gap-2">
                          <code
                            className="px-3 py-2 rounded w-full text-sm bg-gray-700 text-gray-300"
                          >
                            {apiKey.key_prefix ? `${apiKey.key_prefix}...` : apiKey.key}
                          </code>
                        </div>
                      </Table.Cell>
                      <Table.Cell className="text-gray-300">
                        {formatDate(apiKey.created)}
                      </Table.Cell>
                      <Table.Cell className="text-gray-300">
                        {apiKey.last_used ? formatDate(apiKey.last_used) : "Never"}
                      </Table.Cell>
                      <Table.Cell>
                        <Badge color={apiKey.status === "active" ? "success" : "gray"} size="sm">
                          {apiKey.status || "active"}
                        </Badge>
                        <div className="text-xs text-gray-400 mt-1">
                          {apiKey.rate_limit_per_minute || 60}/min
                        </div>
                      </Table.Cell>
                      <Table.Cell>
                        <div className="flex items-center gap-2">
                          <Tooltip content="Delete API key">
                            <button
                              className="p-2 rounded text-red-400 hover:bg-gray-700 transition-colors"
                              onClick={() => handleDeleteAPIKey(apiKey.id)}
                            >
                              <FontAwesomeIcon
                                icon={faTrash}
                                className="w-4 h-4"
                              />
                            </button>
                          </Tooltip>
                        </div>
                      </Table.Cell>
                    </Table.Row>
                  ))}
                </Table.Body>
              </Table>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <FontAwesomeIcon
                icon={faKey}
                className="w-16 h-16 text-gray-600 mb-4"
              />
              <h3 className="text-2xl font-semibold text-gray-400 mb-2">
                No API Keys Found
              </h3>
              <p className="text-gray-500 mb-6 max-w-md">
                You haven't created any API keys yet. Create your first API key
                to start using the service.
              </p>
            </div>
          )}
        </div>
          </Tabs.Item>
          <Tabs.Item title="Usage">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <div className="bg-gray-800 p-4 rounded">
                <div className="text-gray-400 text-sm">Requests</div>
                <div className="text-white text-2xl font-semibold">{renderSummaryNumber(usageDashboard?.summary?.total_requests)}</div>
              </div>
              <div className="bg-gray-800 p-4 rounded">
                <div className="text-gray-400 text-sm">Credits Used</div>
                <div className="text-white text-2xl font-semibold">{renderSummaryNumber(usageDashboard?.summary?.credits_used)}</div>
              </div>
              <div className="bg-gray-800 p-4 rounded">
                <div className="text-gray-400 text-sm">Input Tokens</div>
                <div className="text-white text-2xl font-semibold">{renderSummaryNumber(usageDashboard?.summary?.prompt_tokens)}</div>
              </div>
              <div className="bg-gray-800 p-4 rounded">
                <div className="text-gray-400 text-sm">Output Tokens</div>
                <div className="text-white text-2xl font-semibold">{renderSummaryNumber(usageDashboard?.summary?.completion_tokens)}</div>
              </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <BreakdownTable title="Endpoint Breakdown" rows={usageDashboard?.by_endpoint || []} nameKey="endpoint" />
              <BreakdownTable title="API Key Breakdown" rows={usageDashboard?.by_key || []} nameKey="key_prefix" />
            </div>
          </Tabs.Item>
          <Tabs.Item title="Billing">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
              <div className="bg-gray-800 p-5 rounded">
                <div className="text-gray-400 text-sm">Current Balance</div>
                <div className="text-white text-3xl font-semibold">{renderSummaryNumber(billingSummary?.balance)} credits</div>
              </div>
              {(billingSummary?.credit_packs || []).map((pack) => (
                <div key={pack.label} className="bg-gray-800 p-5 rounded flex items-center justify-between">
                  <div>
                    <div className="text-white font-semibold">{pack.label}</div>
                    <div className="text-gray-400 text-sm">{renderSummaryNumber(pack.credits)} credits</div>
                  </div>
                  <Button onClick={() => handleBuyCredits(pack.credits)} className="bg-cyan-600 hover:bg-cyan-700">Buy</Button>
                </div>
              ))}
            </div>
            <BreakdownTable title="Recent Usage Transactions" rows={billingSummary?.transactions || []} nameKey="description" />
          </Tabs.Item>
        </Tabs>

        {/* Create API Key Modal */}
        <Modal
          show={showCreateModal}
          onClose={() => {
            setShowCreateModal(false);
            setKeyName("");
          }}
          size="md"
        >
          <Modal.Header className="bg-gray-800 border-gray-700">
            <span className="text-white">Create New API Key</span>
          </Modal.Header>
          <Modal.Body className="bg-gray-800">
            <div className="space-y-4">
              <div>
                <Label
                  htmlFor="keyName"
                  className="block text-sm font-medium text-gray-300 mb-2"
                >
                  API Key Name
                </Label>
                <TextInput
                  id="keyName"
                  type="text"
                  placeholder="Enter a name for your API key"
                  value={keyName}
                  onChange={(e) => setKeyName(e.target.value)}
                  className="w-full"
                  required
                />
                <p className="text-gray-400 text-xs mt-1">
                  Choose a descriptive name to help you identify this key later
                </p>
              </div>
              <div>
                <Label htmlFor="expiresAt" className="block text-sm font-medium text-gray-300 mb-2">
                  Expiry Date
                </Label>
                <TextInput id="expiresAt" type="date" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="rateLimit" className="block text-sm font-medium text-gray-300 mb-2">
                  Rate Limit Per Minute
                </Label>
                <TextInput id="rateLimit" type="number" min="1" value={rateLimit} onChange={(e) => setRateLimit(e.target.value)} />
              </div>
            </div>
          </Modal.Body>
          <Modal.Footer className="bg-gray-800 border-gray-700">
            <Button
              color="gray"
            onClick={() => {
                setShowCreateModal(false);
                setKeyName("");
                setExpiresAt("");
                setRateLimit(60);
              }}
              className="bg-gray-600 hover:bg-gray-700"
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateAPIKey}
              disabled={!keyName.trim() || isCreating}
              className="bg-cyan-600 hover:bg-cyan-700"
            >
              {isCreating ? "Creating..." : "Create API Key"}
            </Button>
          </Modal.Footer>
        </Modal>    
      </div>
    </div>
  );
}

function BreakdownTable({ title, rows, nameKey }) {
  return (
    <div className="overflow-x-auto bg-gray-800 rounded">
      <div className="px-4 py-3 text-white font-semibold">{title}</div>
      <Table className="w-full bg-black">
        <Table.Head>
          <Table.HeadCell>Name</Table.HeadCell>
          <Table.HeadCell>Calls</Table.HeadCell>
          <Table.HeadCell>Credits</Table.HeadCell>
        </Table.Head>
        <Table.Body className="divide-y divide-gray-700">
          {rows.length === 0 ? (
            <Table.Row className="bg-gray-800">
              <Table.Cell className="text-gray-400" colSpan={3}>No usage yet</Table.Cell>
            </Table.Row>
          ) : rows.map((row, index) => (
            <Table.Row key={`${row[nameKey] || row.name || index}`} className="bg-gray-800">
              <Table.Cell className="text-gray-300">{row.name || row[nameKey] || "Unknown"}</Table.Cell>
              <Table.Cell className="text-gray-300">{row.total_calls || ""}</Table.Cell>
              <Table.Cell className="text-gray-300">{row.total_credits || Math.abs(row.credits || 0)}</Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table>
    </div>
  );
}
