import React, { useState, useEffect } from "react";
import { submittoleaderboardPath } from "../constants/RouteConstants";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";

const Leaderboard = () => {
  const [openIndex, setOpenIndex] = useState(null);
  const [liveLeaderboard, setLiveLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();

  const handleClick = (index) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  // Fetch live leaderboard data
  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${process.env.REACT_APP_BACK_END_HOST}/public/get_leaderboard`);
        if (response.data.success) {
          setLiveLeaderboard(response.data.leaderboard);
        } else {
          setError("Failed to load leaderboard data");
        }
      } catch (err) {
        setError("Error connecting to leaderboard API");
        console.error("Leaderboard fetch error:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchLeaderboard();
  }, []);

  const faqs = [
    {
      question: "Where can I find the evaluation datasets",
      answer:
        "You can access the evaluation set by following the dataset link listed with our submittoleaderboard component. If you have difficulty downloading them or need direct access, just send us an email at nvidra@anote.ai and we will provide the questions promptly.",
    },
    {
      question: "How many times can I submit?",
      answer:
        "There's no strict limit on submissions. You're welcome to submit multiple times, but for the most meaningful insights, we encourage you to submit only when there are substantial updates or improvements to your model.",
    },
    {
      question: "What am I expected to submit?",
      answer:
        "We only require the outputs your model generates for each query in the evaluation set. You do not need to share model weights, code, or other confidential information—simply the answers.",
    },
    {
      question: "When can I expect to receive the results for my submission?",
      answer:
        "We typically process and evaluate new submissions within a few business days. Once your results are ready, we will contact you via email with your score and ranking details.",
    },
    {
      question: "Do I need to give my LLM extra information to accurately run the tests?",
      answer:
        "We do not mandate any special pre-training or additional data, though you could use our fine tuning API. The goal is to see how your model performs under realistic conditions.",
    },
  ];


  // No hardcoded datasets - use only live data from API
  const [datasets, setDatasets] = useState([]);

  // Fetch available datasets from API
  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        const response = await axios.get(`${process.env.REACT_APP_BACK_END_HOST}/public/get_leaderboard`);
        if (response.data.success) {
          // Group submissions by dataset to create dataset structure
          const groupedData = {};
          response.data.leaderboard.forEach(submission => {
            let datasetDisplayName;
            if (submission.dataset_name.includes('_bertscore')) {
              const language = submission.dataset_name.replace('flores_', '').replace('_translation_bertscore', '');
              datasetDisplayName = `${language.charAt(0).toUpperCase() + language.slice(1)} – BERTScore`;
            } else {
              const language = submission.dataset_name.replace('flores_', '').replace('_translation', '');
              datasetDisplayName = `${language.charAt(0).toUpperCase() + language.slice(1)} – BLEU`;
            }

            if (!groupedData[submission.dataset_name]) {
              groupedData[submission.dataset_name] = {
                name: datasetDisplayName,
                url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
                models: []
              };
            }

            groupedData[submission.dataset_name].models.push({
              rank: submission.rank,
              model: submission.model_name,
              score: submission.score,
              updated: new Date(submission.submitted_at).toLocaleDateString()
            });
          });

          // Sort models within each dataset by rank
          Object.values(groupedData).forEach(dataset => {
            dataset.models.sort((a, b) => a.rank - b.rank);
          });

          setDatasets(Object.values(groupedData));
        }
      } catch (err) {
        console.error("Error fetching datasets:", err);
      }
    };

    fetchDatasets();
  }, []);
  
  // Check if we should show full leaderboard for a specific dataset
  const showFullLeaderboard = location.state?.showFullLeaderboard;
  const selectedDataset = location.state?.selectedDataset;
  
  // If showing full leaderboard for a specific dataset
  if (showFullLeaderboard && selectedDataset) {
    // Find the matching dataset from live leaderboard
    const datasetSubmissions = liveLeaderboard.filter(submission => {
      let datasetDisplayName;
      if (submission.dataset_name.includes('_bertscore')) {
        const language = submission.dataset_name.replace('flores_', '').replace('_translation_bertscore', '');
        datasetDisplayName = `${language.charAt(0).toUpperCase() + language.slice(1)} – BERTScore`;
      } else {
        const language = submission.dataset_name.replace('flores_', '').replace('_translation', '');
        datasetDisplayName = `${language.charAt(0).toUpperCase() + language.slice(1)} – BLEU`;
      }
      return datasetDisplayName === selectedDataset;
    });

    // Sort by score (descending) and assign proper ranks starting from 1
    const rankedSubmissions = datasetSubmissions
      .sort((a, b) => b.score - a.score)
      .map((submission, index) => ({
        ...submission,
        rank: index + 1
      }));

    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 pb-20 mx-3">
        <div className="w-full max-w-6xl">
          <div className="mb-8 flex items-center justify-between">
            <button
              onClick={() => navigate('/evaluations')}
              className="text-blue-400 hover:text-blue-300 underline text-sm"
            >
              ← Back to Evaluations
            </button>
            <h1 className="text-3xl font-bold text-white">{selectedDataset} - Full Leaderboard</h1>
            <div></div>
          </div>
          
          {loading ? (
            <div className="text-center py-12">
              <div className="text-white text-lg">Loading leaderboard...</div>
            </div>
          ) : rankedSubmissions.length > 0 ? (
            <div className="bg-gray-800 rounded-lg overflow-hidden">
              <div className="grid grid-cols-4 bg-gray-700 p-4 font-bold text-white">
                <div>Rank</div>
                <div>Model Name</div>
                <div>BLEU Score</div>
                <div>Submitted</div>
              </div>
              {rankedSubmissions.map((submission, index) => (
                <div
                  key={submission.id || index}
                  className={`grid grid-cols-4 p-4 ${
                    index % 2 === 0 ? "bg-gray-800" : "bg-gray-750"
                  } text-white`}
                >
                  <div className="font-bold text-yellow-400">#{submission.rank}</div>
                  <div className="font-semibold">{submission.model_name}</div>
                  <div className="text-green-300">{submission.score.toFixed(4)}</div>
                  <div className="text-gray-400 text-sm">
                    {new Date(submission.submitted_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="text-gray-400">No submissions found for {selectedDataset}</div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Default leaderboard view
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 pb-20 mx-3">
      <h1 className="text-4xl font-bold text-white mb-4 mt-8">LLM Leaderboards</h1>
      <button
        className="btn-black px-6 py-2 mb-8 rounded-md text-lg font-semibold transition-colors"
        onClick={() => navigate(submittoleaderboardPath)}
      >
        Submit Model to Leaderboard
      </button>

      {/* Live Model Submissions */}
      <div className="w-full max-w-4xl p-6 bg-gradient-to-r from-green-900 to-blue-900 rounded-lg shadow-lg mb-12">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-white">🔥 Live Model Submissions</h2>
          <span className="text-green-300 text-sm">Real-time data from your API</span>
        </div>
        
        {loading && (
          <div className="text-center py-8">
            <div className="text-white">Loading live submissions...</div>
          </div>
        )}
        
        {error && (
          <div className="text-center py-8">
            <div className="text-red-300">⚠️ {error}</div>
          </div>
        )}
        
        {!loading && !error && liveLeaderboard.length > 0 && (
          <>
            <div className="grid grid-cols-5 text-white font-bold text-center bg-gray-900 p-4 rounded-t-lg">
              <div>Rank</div>
              <div>Model</div>
              <div>Score</div>
              <div>Dataset</div>
              <div>Submitted</div>
            </div>
            <div>
              {liveLeaderboard.slice(0, 10).map((submission, index) => (
                <div
                  key={index}
                  className={`grid grid-cols-5 text-center p-4 ${
                    index % 2 === 0
                      ? "bg-gray-700 text-white"
                      : "bg-gray-800 text-white"
                  }`}
                >
                  <div className="font-bold text-yellow-400">#{submission.rank}</div>
                  <div className="font-semibold">{submission.model_name}</div>
                  <div className="text-green-300">{submission.score.toFixed(3)}</div>
                  <div className="text-blue-300 text-sm">{submission.dataset_name}</div>
                  <div className="text-gray-300 text-sm">
                    {new Date(submission.submitted_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
        
        {!loading && !error && liveLeaderboard.length === 0 && (
          <div className="text-center py-8">
            <div className="text-gray-300">No submissions yet. Be the first to submit!</div>
          </div>
        )}
      </div>

      <h2 className="text-3xl font-bold text-white mb-8 mt-12">📊 Benchmark Datasets</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {datasets.map((dataset, index) => (
          <div
            key={index}
            className="w-full max-w-3xl p-4 bg-gray-950 rounded-lg shadow-lg"
          >
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-white">{dataset.name}</h2>
              <a
                href={dataset.url}
                className="text-blue-400 hover:text-blue-500 text-sm underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                View Dataset
              </a>
            </div>
            <div className="grid grid-cols-4 text-white font-bold text-center bg-gray-900 p-4 rounded-t-lg">
              <div>Rank</div>
              <div>Model</div>
              <div>Score</div>
              <div>Last Updated</div>
            </div>
            <div>
              {dataset.models
                .map((model, modelIndex) => (
                  <div
                    key={modelIndex}
                    className={`grid grid-cols-4 text-center p-4 ${
                      modelIndex % 2 === 0
                        ? "bg-gray-700 text-white"
                        : "bg-gray-800 text-white"
                    }`}
                  >
                    <div>{model.rank}</div>
                    <div>{model.model}</div>
                    <div>{model.score}</div>
                    <div>{model.updated}</div>
                  </div>
                ))}
            </div>
          </div>
        ))}
      </div>

      {/* FAQs Section */}
      <div className="w-full md:w-3/4 mx-auto mt-20">
        <div className="bg-gray-900 rounded-xl p-10">
          <div className="text-yellow-500 text-3xl font-semibold mb-8">FAQs</div>
          {faqs.map((faq, index) => (
            <div
              className="bg-gray-800 px-5 py-4 my-4 rounded-xl cursor-pointer"
              onClick={() => handleClick(index)}
              key={index}
            >
              <div className="faq-header">
                <h2 className="text-xl font-medium bg-clip-text text-transparent bg-gradient-to-r from-turquoise-500 to-blue-400">
                  {faq.question}
                </h2>
              </div>
              {openIndex === index && (
                <div className="faq-answer mt-2 text-white">
                  <p>{faq.answer}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Leaderboard; 