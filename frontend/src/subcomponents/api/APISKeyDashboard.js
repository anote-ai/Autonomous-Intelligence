import React, { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import {
  useAPIKeys,
  generateAPIKey,
  deleteAPIKey,
  getAPIKeys,
  useNumCredits,
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
import "../../styles/APIKeyDashboard.css";
import {
  Button,
  Table,
  Card,
  Badge,
  Tooltip,
  Modal,
  TextInput,
  Label,
} from "flowbite-react";

export function APISKeyDashboard() {
  const dispatch = useDispatch();
  const apiKeys = useAPIKeys();
  const numCredits = useNumCredits();
  const [copiedKey, setCopiedKey] = useState(null);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState(null); // Track newly created key
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [isCreating, setIsCreating] = useState(false);

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
      const result = await dispatch(generateAPIKey({ name: keyName.trim() }));
      if (result.payload && !result.payload.error) {
        setNewlyCreatedKey(result.payload.key);
        setShowCreateModal(false);
        setKeyName("");
        // Auto-hide after 30 seconds for security
        setTimeout(() => {
          setNewlyCreatedKey(null);
        }, 30000);
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

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const maskApiKey = (key) => {
    if (key.length <= 8) return "••••••••";
    return `${key.substring(0, 4)}${"•".repeat(key.length - 8)}${key.substring(
      key.length - 4
    )}`;
  };

  const isKeyVisible = (apiKey) => {
    return newlyCreatedKey === apiKey.key;
  };

  useEffect(() => {
    dispatch(getAPIKeys());
  }, [dispatch]);

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
              onClick={() => window.history.back()}
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

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="bg-gray-800 border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Available Credits</p>
                <p
                  className={`text-2xl font-bold ${
                    hasSufficientCredits ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {numCredits}
                </p>
              </div>
              <div
                className={`p-3 rounded-lg ${
                  hasSufficientCredits ? "bg-green-600" : "bg-red-600"
                }`}
              >
                <FontAwesomeIcon
                  icon={faCoins}
                  className="w-6 h-6 text-white"
                />
              </div>
            </div>
          </Card>

          <Card className="bg-gray-800 border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Total Keys</p>
                <p className="text-2xl font-bold text-white">
                  {apiKeys.length}
                </p>
              </div>
              <div className="p-3 bg-cyan-600 rounded-lg">
                <FontAwesomeIcon icon={faKey} className="w-6 h-6 text-white" />
              </div>
            </div>
          </Card>

          <Card className="bg-gray-800 border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Active Keys</p>
                <p className="text-2xl font-bold text-white">
                  {apiKeys.length}
                </p>
              </div>
              <div className="p-3 bg-green-600 rounded-lg">
                <FontAwesomeIcon icon={faKey} className="w-6 h-6 text-white" />
              </div>
            </div>
          </Card>
        </div>

        {/* API Keys Table */}
        <Card className="bg-gray-800 border-gray-700">
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-white">
                Your API Keys
              </h2>
              <Badge color="info" size="sm">
                {apiKeys.length} {apiKeys.length === 1 ? "Key" : "Keys"}
              </Badge>
            </div>

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
                              className={`px-3 py-2 rounded w-full text-sm ${
                                isKeyVisible(apiKey)
                                  ? "bg-green-900 text-green-300 border border-green-700"
                                  : "bg-gray-700 text-gray-300"
                              }`}
                            >
                              {isKeyVisible(apiKey)
                                ? apiKey.key
                                : maskApiKey(apiKey.key)}
                            </code>
                          </div>
                        </Table.Cell>
                        <Table.Cell className="text-gray-300">
                          {formatDate(apiKey.created)}
                        </Table.Cell>
                        <Table.Cell>
                          <Badge color="success" size="sm">
                            Active
                          </Badge>
                        </Table.Cell>
                        <Table.Cell>
                          <div className="flex items-center gap-2">
                            {isKeyVisible(apiKey) && (
                              <Tooltip
                                content={
                                  copiedKey === apiKey.id
                                    ? "Copied!"
                                    : "Copy to clipboard"
                                }
                              >
                                <button
                                  className={`p-2 rounded transition-colors ${
                                    copiedKey === apiKey.id
                                      ? "text-green-400 bg-green-900"
                                      : "text-cyan-400 hover:bg-gray-700"
                                  }`}
                                  onClick={() =>
                                    handleCopyAPIKey(apiKey.key, apiKey.id)
                                  }
                                >
                                  <FontAwesomeIcon
                                    icon={faCopy}
                                    className="w-4 h-4"
                                  />
                                </button>
                              </Tooltip>
                            )}
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
              <div className="text-center py-12">
                <FontAwesomeIcon
                  icon={faKey}
                  className="w-16 h-16 text-gray-600 mb-4"
                />
                <h3 className="text-lg font-semibold text-gray-300 mb-2">
                  No API Keys Found
                </h3>
                <p className="text-gray-400 mb-6">
                  {hasSufficientCredits
                    ? 'Use the "Create New API Key" button above to start using our services'
                    : "You need at least 1 credit to create API keys"}
                </p>
              </div>
            )}
          </div>
        </Card>

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
            </div>
          </Modal.Body>
          <Modal.Footer className="bg-gray-800 border-gray-700">
            <Button
              color="gray"
              onClick={() => {
                setShowCreateModal(false);
                setKeyName("");
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

        {/* Documentation Link */}
        <div className="mt-8 text-center">
          <a
            href="https://docs.anote.ai/api/anoteapi.html"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            📚 View API Documentation
          </a>
        </div>
      </div>
    </div>
  );
}
