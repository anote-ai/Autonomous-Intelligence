import React, { useRef, useState, useEffect } from "react";
import Papa from "papaparse";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowRight, faX } from "@fortawesome/free-solid-svg-icons";
import { Modal, TextInput } from "flowbite-react";
import Select from "react-select";
import { useDispatch } from "react-redux";
import { FaDatabase } from "react-icons/fa";
import axios from "axios";
import { useLocation } from "react-router-dom";

import { loadDatasets, useDatasets } from "../redux/DatasetSlice";
import { SelectStyles } from "../styles/SelectStyles";

import {
  FlowPage,
  NLPTask,
  NLPTaskMap,
  FlowType,
  NLPTaskFileName,
  FlowTypeFileName,
} from "../constants/DbEnums";

const SubmitToLeaderboard = ({
  flowType = FlowType.PREDICT,
  // Hooks to navigate out or set page states
  setPageNumber,
  backHome,

  // Hooks related to CSV data
  setLocalCsvData,
  setHasMoreRows,

  // Hooks related to dataset info
  nameToGive,
  setNameToGive,
  trainingFlow,
  setTrainingFlow,
  csvFileName,
  setCsvFileName,
  documentBankFileNames,
  setDocumentBankFileNames,
  assignedTaskType,
  setAssignedTaskType,
  selectedDatasetId,
  setSelectedDatasetId,
}) => {
  // ---------- Additional State for User/Organization Form ----------
  const location = useLocation();

  const [formData, setFormData] = useState({
    benchmarkDataset: "",
    submissionName: "",
    firstName: "",
    lastName: "",
    email: "",
    companyName: "",
    jobTitle: "",
    linkedIn: "",
    modelResults: "", // Add this for model results input
  });
  const [submissionStatus, setSubmissionStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiResponse, setApiResponse] = useState(null);

  // New state for model results file upload
  const [modelResultsFile, setModelResultsFile] = useState(null);
  const [parsedModelResults, setParsedModelResults] = useState([]);
  const fileInputRefResults = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmissionStatus("");
    setApiResponse(null);

    try {
      // Validate required fields for submit_model API
      if (!formData.benchmarkDataset || !formData.submissionName || !parsedModelResults.length) {
        setSubmissionStatus("Error! Please fill in Benchmark Dataset, Submission Name, and upload Model Results.");
        setIsSubmitting(false);
        return;
      }

      // Prepare data for submit_model API
      const submitData = {
        benchmarkDatasetName: formData.benchmarkDataset,
        modelName: formData.submissionName,
        modelResults: parsedModelResults,
        sentence_ids: Array.from({length: parsedModelResults.length}, (_, i) => i)
      };

      const apiUrl = `${process.env.REACT_APP_BACK_END_HOST}/public/submit_model`;
      console.log("API URL:", apiUrl);
      console.log("Submitting to submit_model API:", submitData);

      // Call your submit_model API
      const response = await axios.post(apiUrl, submitData, {
        headers: { "Content-Type": "application/json" }
      });

      if (response.data.success) {
        setApiResponse(response.data);
        setSubmissionStatus(`Success! Your model scored ${response.data.score.toFixed(4)} BLEU score.`);
        
        // Also submit to Google Sheets for record keeping (optional)
        const googleSheetsData = {
          ...formData,
          bleuScore: response.data.score,
          submissionDate: new Date().toISOString()
        };

        try {
          await fetch("https://script.google.com/macros/s/YOUR_SCRIPT_URL/exec", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(googleSheetsData),
          });
        } catch (googleError) {
          console.log("Google Sheets submission failed (non-critical):", googleError);
        }

      } else {
        setSubmissionStatus(`Error! ${response.data.error || "Submission failed"}`);
      }

    } catch (error) {
      console.error("Submission error:", error);
      if (error.response) {
        setSubmissionStatus(`Error! ${error.response.data.error || "Server error"}`);
      } else {
        setSubmissionStatus("Error! Failed to submit. Please check your connection and try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  // Handle model results file upload
  const handleModelResultsFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      setModelResultsFile(file);
      
      if (file.name.endsWith('.csv')) {
        // Parse CSV file
        Papa.parse(file, {
          header: true,
          complete: function (results) {
            // Look for model_output column, or fall back to second column
            const columnKeys = Object.keys(results.data[0]);
            const modelOutputKey = columnKeys.find(key => 
              key.toLowerCase().includes('model_output') || 
              key.toLowerCase().includes('output') ||
              key.toLowerCase().includes('translation')
            ) || columnKeys[1]; // Default to second column if no specific column found
            
            const modelResults = results.data
              .map(row => row[modelOutputKey])
              .filter(result => result && result.trim() !== '');
            setParsedModelResults(modelResults);
            console.log("Parsed model results:", modelResults.slice(0, 3));
          },
          error: function(error) {
            console.error("CSV parsing error:", error);
            setSubmissionStatus("Error parsing CSV file. Please check the format.");
          }
        });
      } else if (file.name.endsWith('.json')) {
        // Parse JSON file
        const reader = new FileReader();
        reader.onload = (e) => {
          try {
            const jsonData = JSON.parse(e.target.result);
            // Assume it's an array of strings
            if (Array.isArray(jsonData)) {
              setParsedModelResults(jsonData);
            } else {
              setSubmissionStatus("Error: JSON file should contain an array of model results.");
            }
          } catch (error) {
            console.error("JSON parsing error:", error);
            setSubmissionStatus("Error parsing JSON file. Please check the format.");
          }
        };
        reader.readAsText(file);
      } else {
        setSubmissionStatus("Error: Please upload a CSV or JSON file containing model results.");
      }
    }
  };

  // ---------- Existing local states ----------
  const fileInputRefCsv = useRef(null);
  const fileInputRefDocumentBanks = useRef(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedTaskType, setSelectedTaskType] = useState("");

  // Toggling whether input text col is doc name
  const [inputTextColContainsDocumentNames, setInputTextColContainsDocumentNames] =
    useState(false);

  // Drag state
  const [isCsvDragActive, setIsCsvDragActive] = useState(false);
  const [isDocBankDragActive, setIsDocBankDragActive] = useState(false);

  // Some conditions from your existing snippet
  let dispatch = useDispatch();
  useEffect(() => {
    // If we're in PREDICT flow, load known datasets from the Redux store
    if (flowType === FlowType.PREDICT) {
      dispatch(loadDatasets());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle preselected dataset from evaluations page
  useEffect(() => {
    if (location.state?.preselectedDataset) {
      setFormData(prev => ({
        ...prev,
        benchmarkDataset: location.state.preselectedDataset
      }));
    }
  }, [location.state]);

  const datasets = useDatasets();

  // ---------- Benchmark Dataset Modal & Options ----------
  const connectorOptions = [
    // BLEU Evaluation Datasets
    { value: "flores_spanish_translation", label: "Spanish Translation (FLORES+ BLEU)", taskType: "Translation" },
    { value: "flores_japanese_translation", label: "Japanese Translation (FLORES+ BLEU)", taskType: "Translation" },
    { value: "flores_arabic_translation", label: "Arabic Translation (FLORES+ BLEU)", taskType: "Translation" },
    { value: "flores_chinese_translation", label: "Chinese Translation (FLORES+ BLEU)", taskType: "Translation" },
    { value: "flores_korean_translation", label: "Korean Translation (FLORES+ BLEU)", taskType: "Translation" },
    
    // BERTScore Evaluation Datasets
    { value: "flores_spanish_translation_bertscore", label: "Spanish Translation (FLORES+ BERTScore)", taskType: "Translation" },
    { value: "flores_japanese_translation_bertscore", label: "Japanese Translation (FLORES+ BERTScore)", taskType: "Translation" },
    { value: "flores_arabic_translation_bertscore", label: "Arabic Translation (FLORES+ BERTScore)", taskType: "Translation" },
    { value: "flores_chinese_translation_bertscore", label: "Chinese Translation (FLORES+ BERTScore)", taskType: "Translation" },
    { value: "flores_korean_translation_bertscore", label: "Korean Translation (FLORES+ BERTScore)", taskType: "Translation" },
  ];

  const filteredOptions = connectorOptions.filter(
    (option) => selectedTaskType === "" || option.taskType === selectedTaskType
  );

  // For the <Select> dropdown, we'll just use the same list (ignoring taskType filtering):
  const connectorOptionsForSelect = connectorOptions.map((o) => ({
    value: o.value,
    label: o.label,
  }));

  const handleOpenModal = () => setIsModalOpen(true);
  const handleCloseModal = () => setIsModalOpen(false);

  const handleDatasetSelect = async (datasetName) => {
    // Set the selected dataset
    setFormData(prev => ({ ...prev, benchmarkDataset: datasetName }));
    
    // Download source sentences for the selected dataset
    try {
              const response = await axios.get(`${process.env.REACT_APP_BACK_END_HOST || "http://localhost:5001"}/public/get_source_sentences?count=10`);
      console.log("Source sentences for", datasetName, ":", response.data.source_sentences?.slice(0, 3));
    } catch (error) {
      console.error("Error fetching source sentences:", error);
    }
    
    handleCloseModal();
  };

  const onConnectorCardClick = (value) => {
    handleDatasetSelect(value);
  };

  // For the <Select> onChange
  const onBenchmarkSelectChange = (selectedOption) => {
    setFormData(prev => ({ ...prev, benchmarkDataset: selectedOption.value }));
    // Also set assignedTaskType based on match
    const found = connectorOptions.find((o) => o.value === selectedOption.value);
    if (found) {
      setSelectedTaskType(found.taskType);
    }
  };

  return (
    <div className="w-screen bg-gray-900 text-white min-h-screen flex items-center justify-center">
      <div className="w-full bg-gray-900 max-w-4xl mx-auto border border-blue-300 mt-8 px-10 py-5 rounded-xl text-white space-y-5">
        {/* Header + Close */}
        <div className="flex flex-row items-center justify-between">
          <div className="font-bold text-xl">Model Leaderboard Submission</div>
        </div>

        {/* Download Benchmark Dataset Button */}
        {flowType === FlowType.PREDICT && (
          <button
            className="underline text-sm text-yellow-500 hover:text-yellow-400"
            onClick={handleOpenModal}
          >
            Download Benchmark Dataset
          </button>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm mb-1">Benchmark Dataset Name *</label>
              <Select
                styles={SelectStyles}
                options={connectorOptionsForSelect}
                placeholder="Select a Benchmark..."
                onChange={onBenchmarkSelectChange}
                value={connectorOptionsForSelect.find(option => option.value === formData.benchmarkDataset)}
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Model/Submission Name *</label>
              <input
                type="text"
                name="submissionName"
                value={formData.submissionName}
                onChange={handleChange}
                className="w-full px-4 py-2 rounded-md bg-gray-700 focus:ring-2 focus:ring-blue-400"
                placeholder="e.g., my-spanish-model-v1"
                required
              />
            </div>
            <div>
              <label className="block text-sm mb-1">First Name *</label>
              <input
                type="text"
                name="firstName"
                value={formData.firstName}
                onChange={handleChange}
                className="w-full px-4 py-2 rounded-md bg-gray-700 focus:ring-2 focus:ring-blue-400"
                required
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Last Name *</label>
              <input
                type="text"
                name="lastName"
                value={formData.lastName}
                onChange={handleChange}
                className="w-full px-4 py-2 rounded-md bg-gray-700 focus:ring-2 focus:ring-blue-400"
                required
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Email *</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="w-full px-4 py-2 rounded-md bg-gray-700 focus:ring-2 focus:ring-blue-400"
                required
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Company Name *</label>
              <input
                type="text"
                name="companyName"
                value={formData.companyName}
                onChange={handleChange}
                className="w-full px-4 py-2 rounded-md bg-gray-700 focus:ring-2 focus:ring-blue-400"
                required
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Job Title</label>
              <input
                type="text"
                name="jobTitle"
                value={formData.jobTitle}
                onChange={handleChange}
                className="w-full px-4 py-2 rounded-md bg-gray-700 focus:ring-2 focus:ring-blue-400"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">LinkedIn URL</label>
              <input
                type="url"
                name="linkedIn"
                value={formData.linkedIn}
                onChange={handleChange}
                className="w-full px-4 py-2 rounded-md bg-gray-700 focus:ring-2 focus:ring-blue-400"
              />
            </div>
          </div>

          {/* Model Results Upload Section */}
          <div className="mt-6">
            <label className="block text-sm mb-1">Model Results File * (CSV or JSON)</label>
            <div 
              onClick={() => fileInputRefResults.current?.click()}
              className="w-full rounded bg-gray-800 h-32 flex flex-col items-center justify-center py-4 cursor-pointer border-2 border-dashed border-gray-600 hover:border-blue-400"
            >
              <div className="font-semibold">Upload Model Results</div>
              <div className="text-xs text-gray-400 mt-1">
                CSV (first column) or JSON array of model outputs
              </div>
              <div className="text-white text-sm mt-2">
                {modelResultsFile ? `Selected: ${modelResultsFile.name}` : "No file selected"}
              </div>
              {parsedModelResults.length > 0 && (
                <div className="text-green-400 text-xs mt-1">
                  ✓ Parsed {parsedModelResults.length} model results
                </div>
              )}
              <input
                type="file"
                className="hidden"
                ref={fileInputRefResults}
                accept=".csv,.json"
                onChange={handleModelResultsFileUpload}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 text-white font-bold py-2 px-4 rounded-md focus:ring-4 focus:ring-blue-300"
          >
            {isSubmitting ? "Submitting..." : "Submit to Leaderboard"}
          </button>
        </form>

        {/* Results Display */}
        {submissionStatus && (
          <div className={`mt-4 p-3 rounded-md ${
            submissionStatus.includes("Success") ? "bg-green-900 text-green-200" : "bg-red-900 text-red-200"
          }`}>
            <p className="text-center text-sm">{submissionStatus}</p>
          </div>
        )}

        {apiResponse && (
          <div className="mt-4 p-4 bg-gray-800 rounded-md">
            <h3 className="text-lg font-semibold text-green-400 mb-2">API Response:</h3>
            <pre className="text-xs text-gray-300 overflow-x-auto">
              {JSON.stringify(apiResponse, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Benchmark Datasets Modal */}
      {isModalOpen && (
        <Modal
          size="3xl"
          show={isModalOpen}
          onClose={handleCloseModal}
          theme={{
            root: {
              show: {
                on: "flex bg-gray-900 bg-opacity-50 dark:bg-opacity-80",
              },
            },
            content: {
              base: "relative h-full w-full p-4 md:h-auto",
              inner: "relative rounded-lg shadow bg-gray-800 flex flex-col max-h-[90vh] text-white",
            },
          }}
        >
          <Modal.Header className="border-b border-gray-600 pb-1 text-center">
            <div className="flex justify-center items-center w-full text-center">
              <h2 className="font-bold text-xl text-center text-white">
                Benchmark Datasets
              </h2>
            </div>
          </Modal.Header>
          <Modal.Body className="w-full overflow-y-auto">
            <div className="text-center mb-4 text-sm">
              Supported benchmark test datasets include various task types like
              Classification, Chatbot, NER, and Translation.
            </div>

            {/* Buttons to filter dataset cards by type */}
            <div className="flex justify-center space-x-4 mb-6">
              <button
                className={`px-4 py-2 rounded-lg transition-all duration-300 transform hover:scale-105 ${
                  selectedTaskType === "Translation"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-600 text-gray-200 hover:bg-gray-500"
                }`}
                onClick={() => setSelectedTaskType("Translation")}
              >
                Translation
              </button>
              <button
                className={`px-4 py-2 rounded-lg transition-all duration-300 transform hover:scale-105 ${
                  selectedTaskType === "Classification"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-600 text-gray-200 hover:bg-gray-500"
                }`}
                onClick={() => setSelectedTaskType("Classification")}
              >
                Classification
              </button>
              <button
                className={`px-4 py-2 rounded-lg transition-all duration-300 transform hover:scale-105 ${
                  selectedTaskType === "Chatbot"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-600 text-gray-200 hover:bg-gray-500"
                }`}
                onClick={() => setSelectedTaskType("Chatbot")}
              >
                Chatbot
              </button>
              <button
                className={`px-4 py-2 rounded-lg transition-all duration-300 transform hover:scale-105 ${
                  selectedTaskType === ""
                    ? "bg-blue-600 text-white"
                    : "bg-gray-600 text-gray-200 hover:bg-gray-500"
                }`}
                onClick={() => setSelectedTaskType("")}
              >
                All
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {filteredOptions.map((option, index) => (
                <div
                  key={index}
                  className={`p-4 border rounded-lg shadow-md cursor-pointer transition-all duration-300 hover:shadow-xl ${
                    formData.benchmarkDataset === option.value
                      ? "bg-blue-600 text-white"
                      : "bg-gray-700 text-gray-200 hover:bg-gray-600"
                  }`}
                  onClick={() => onConnectorCardClick(option.value)}
                >
                  <div className="flex flex-col items-center text-center">
                    <FaDatabase className="mb-2" size={20} />
                    <div className="text-sm font-semibold mb-1">
                      {option.label}
                    </div>
                    <div className="text-xs text-gray-300">
                      {option.taskType}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Modal.Body>
        </Modal>
      )}
    </div>
  );
};

export default SubmitToLeaderboard; 