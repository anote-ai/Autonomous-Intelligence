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
        const response = await axios.get("http://localhost:5001/public/get_leaderboard");
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


  const datasets = [
    {
      name: "FinanceBench - Retrieval Accuracy",
      url: "https://github.com/patronus-ai/financebench",
      models: [
        {
          rank: 1,
          model: "GPT-4o Fine Tuned",
          score: 0.632,
          ci: "0.61 - 0.65",
          updated: "Oct 2024",
        },
        {
          rank: 2,
          model: "Mistral Fine Tuned",
          score: 0.612,
          ci: "0.59 - 0.63",
          updated: "Oct 2024",
        },
        {
          rank: 3,
          model: "LLaMA 3 Fine Tuned",
          score: 0.593,
          ci: "0.57 - 0.61",
          updated: "Oct 2024",
        },
        {
          rank: 4,
          model: "Re-ranking",
          score: 0.573,
          ci: "0.55 - 0.59",
          updated: "Oct 2024",
        },
        {
          rank: 5,
          model: "Query Expansiong",
          score: 0.256,
          ci: "0.24 - 0.27",
          updated: "Sep 2024",
        },
        {
          rank: 6,
          model: "Base Case RAG",
          score: 0.24,
          ci: "0.22 - 0.26",
          updated: "Sep 2024",
        },
      ],
    },
    {
      name: "Amazon Reviews - Classification Accuracy",
      url: "https://huggingface.co/datasets/m-ric/amazon_product_reviews_datafiniti",
      models: [
        {
          rank: 1,
          model: "GPT-4o",
          score: 0.94,
          ci: "0.92 - 0.96",
          updated: "Sep 2024",
        },
        {
          rank: 2,
          model: "GPT-3.5",
          score: 0.91,
          ci: "0.89 - 0.93",
          updated: "Sep 2024",
        },
        {
          rank: 3,
          model: "LLaMA 3",
          score: 0.9,
          ci: "0.88 - 0.92",
          updated: "Oct 2024",
        },
        {
          rank: 4,
          model: "BERT",
          score: 0.89,
          ci: "0.87 - 0.91",
          updated: "Sep 2024",
        },
        {
          rank: 5,
          model: "SetFit",
          score: 0.87,
          ci: "0.85 - 0.89",
          updated: "Sep 2024",
        },
        {
          rank: 6,
          model: "Claude 2",
          score: 0.86,
          ci: "0.83 - 0.87",
          updated: "Oct 2024",
        },
      ],
    },
    {
      name: "RAG Instruct - Answer Accuracy",
      url: "https://huggingface.co/datasets/llmware/rag_instruct_benchmark_tester",
      models: [
        {
          rank: 1,
          model: "GPT-4o",
          score: 0.89,
          ci: "0.87 - 0.91",
          updated: "Oct 2024",
        },
        {
          rank: 2,
          model: "GPT 3.5",
          score: 0.86,
          ci: "0.84 - 0.88",
          updated: "Oct 2024",
        },
        {
          rank: 3,
          model: "Llama3",
          score: 0.85,
          ci: "0.83 - 0.87",
          updated: "Oct 2024",
        },
        {
          rank: 4,
          model: "Claude 2",
          score: 0.83,
          ci: "0.81 - 0.85",
          updated: "Oct 2024",
        },
        {
          rank: 5,
          model: "GPT4ALL",
          score: 0.82,
          ci: "0.80 - 0.84",
          updated: "Oct 2024",
        },
        {
          rank: 6,
          model: "FLARE",
          score: 0.81,
          ci: "0.79 - 0.83",
          updated: "Oct 2024",
        },
      ],
    },
    {
      name: "Financial Phrasebank - Classification Accuracy",
      url: "https://huggingface.co/datasets/takala/financial_phrasebank",
      models: [
        {
          rank: 1,
          model: "Gemini",
          score: 0.95,
          ci: "0.93 - 0.97",
          updated: "Sep 2024",
        },
        {
          rank: 2,
          model: "GPT-4o",
          score: 0.93,
          ci: "0.91 - 0.95",
          updated: "Sep 2024",
        },
        {
          rank: 3,
          model: "Llama3",
          score: 0.92,
          ci: "0.90 - 0.94",
          updated: "Sep 2024",
        },
        {
          rank: 4,
          model: "BERT",
          score: 0.92,
          ci: "0.90 - 0.94",
          updated: "Sep 2024",
        },
        {
          rank: 5,
          model: "SetFit",
          score: 0.89,
          ci: "0.87 - 0.91",
          updated: "Sep 2024",
        },
        {
          rank: 6,
          model: "Claude 2",
          score: 0.87,
          ci: "0.85 - 0.88",
          updated: "Oct 2024",
        },
      ],
    },
    {
      name: "TREC - Hierarchical Classification Accuracy",
      url: "https://huggingface.co/datasets/CogComp/trec",
      models: [
        {
          rank: 1,
          model: "Claude 2",
          score: 0.85,
          ci: "0.83 - 0.87",
          updated: "Sep 2024",
        },
        {
          rank: 2,
          model: "GPT-4o",
          score: 0.82,
          ci: "0.80 - 0.84",
          updated: "Sep 2024",
        },
        {
          rank: 3,
          model: "Mistral",
          score: 0.81,
          ci: "0.79 - 0.83",
          updated: "Sep 2024",
        },
        {
          rank: 4,
          model: "BERT",
          score: 0.8,
          ci: "0.78 - 0.82",
          updated: "Sep 2024",
        },
        {
          rank: 5,
          model: "SetFit",
          score: 0.79,
          ci: "0.77 - 0.81",
          updated: "Sep 2024",
        },
      ],
    },
    {
      name: "Banking Dataset - Classification Accuracy",
      url: "https://huggingface.co/datasets/takala/financial_phrasebank",
      models: [
        {
          rank: 1,
          model: "GPT-4o",
          score: 0.93,
          ci: "0.91 - 0.95",
          updated: "Sep 2024",
        },
        {
          rank: 2,
          model: "Gemini",
          score: 0.91,
          ci: "0.89 - 0.93",
          updated: "Sep 2024",
        },
        {
          rank: 3,
          model: "Mistral",
          score: 0.9,
          ci: "0.88 - 0.92",
          updated: "Sep 2024",
        },
        {
          rank: 4,
          model: "BERT",
          score: 0.89,
          ci: "0.87 - 0.91",
          updated: "Sep 2024",
        },
        {
          rank: 5,
          model: "SetFit",
          score: 0.87,
          ci: "0.85 - 0.89",
          updated: "Sep 2024",
        },
      ],
    },
    {
      "name": "ARC-SMART",
      "url": "https://huggingface.co/datasets/vipulgupta/arc-smart",
      "models": [
        {
          "rank": 1,
          "model": "Qwen2-72B-Instruct",
          "score": 0.83,
          "updated": "Oct-2024"
        },
        {
          "rank": 2,
          "model": "Meta-Llama-3.1-70B-Instruct",
          "score": 0.819,
          "updated": "Oct-2024"
        },
        {
          "rank": 3,
          "model": "Meta-Llama-3-70B-Instruct",
          "score": 0.819,
          "updated": "Oct-2024"
        },
        {
          "rank": 4,
          "model": "Gemma-2-27b-it",
          "score": 0.788,
          "updated": "Oct-2024"
        },
        {
          "rank": 5,
          "model": "Phi-3.5-MoE-instruct",
          "score": 0.785,
          "updated": "Oct-2024"
        },
        {
          "rank": 6,
          "model": "Phi-3-medium-4k-instruct",
          "score": 0.781,
          "updated": "Oct-2024"
        },
        {
          "rank": 7,
          "model": "Mixtral-8x22B-Instruct-v0.1",
          "score": 0.762,
          "updated": "Oct-2024"
        }
      ]
    },
    {
      "name": "MMLU-SMART",
      "url": "https://huggingface.co/datasets/vipulgupta/mmlu-smart",
      "models": [
        {
          "rank": 1,
          "model": "Qwen2-72B-Instruct",
          "score": 0.743,
          "updated": "Oct-2024"
        },
        {
          "rank": 2,
          "model": "Meta-Llama-3.1-70B-Instruct",
          "score": 0.714,
          "updated": "Oct-2024"
        },
        {
          "rank": 3,
          "model": "Meta-Llama-3-70B-Instruct",
          "score": 0.692,
          "updated": "Oct-2024"
        },
        {
          "rank": 4,
          "model": "Phi-3.5-MoE-instruct",
          "score": 0.67,
          "updated": "Oct-2024"
        },
        {
          "rank": 5,
          "model": "Phi-3-medium-4k-instruct",
          "score": 0.656,
          "updated": "Oct-2024"
        },
        {
          "rank": 6,
          "model": "Mixtral-8x22B-Instruct-v0.1",
          "score": 0.653,
          "updated": "Oct-2024"
        },
        {
          "rank": 7,
          "model": "Gemma-2-27b-it",
          "score": 0.639,
          "updated": "Oct-2024"
        }
      ]
    },
    {
      "name": "CommonsenseQA-SMART",
      "url": "https://huggingface.co/datasets/vipulgupta/commonsense_qa_smart",
      "models": [
        {
          "rank": 1,
          "model": "Qwen2-72B-Instruct",
          "score": 0.845,
          "updated": "Oct-2024"
        },
        {
          "rank": 2,
          "model": "Yi-1.5-34B-Chat",
          "score": 0.776,
          "updated": "Oct-2024"
        },
        {
          "rank": 3,
          "model": "Meta-Llama-3-70B-Instruct",
          "score": 0.771,
          "updated": "Oct-2024"
        },
        {
          "rank": 4,
          "model": "Qwen1.5-32B-Chat",
          "score": 0.767,
          "updated": "Oct-2024"
        },
        {
          "rank": 5,
          "model": "Meta-Llama-3.1-70B-Instruct",
          "score": 0.741,
          "updated": "Oct-2024"
        },
        {
          "rank": 6,
          "model": "Phi-3.5-MoE-instruct",
          "score": 0.739,
          "updated": "Oct-2024"
        },
        {
          "rank": 7,
          "model": "Gemma-2-9b-it",
          "score": 0.733,
          "updated": "Oct-2024"
        }
      ]
    },
    {
      "name": "Geolocation Inference - Median Distance Error",
      "url": "https://github.com/njspyx/location-inference",
      "models": [
          {
              "rank": 1,
              "model": "O1",
              "score": 182.73,
              "updated": "Feb 2025"
          },
          {
              "rank": 2,
              "model": "GPT-4o",
              "score": 216.13,
              "updated": "Feb 2025"
          },
          {
              "rank": 3,
              "model": "Gemini 1.5 Pro",
              "score": 287.27,
              "updated": "Feb 2025"
          },
          {
              "rank": 4,
              "model": "Gemini 1.5 Flash",
              "score": 298.86,
              "updated": "Feb 2025"
          },
          {
              "rank": 5,
              "model": "Gemini 1.5 Flash 8B",
              "score": 304.96,
              "updated": "Feb 2025"
          },
          {
              "rank": 6,
              "model": "GPT-4o Mini",
              "score": 380.85,
              "updated": "Feb 2025"
          },
          {
              "rank": 7,
              "model": "Claude 3.5 Sonnet",
              "score": 382.07,
              "updated": "Feb 2025"
          },
          {
              "rank": 8,
              "model": "Qwen2VL 7B Instruct",
              "score": 475.25,
              "updated": "Feb 2025"
          }
      ]
  }
  ];
  
  // Check if we should show full leaderboard for a specific dataset
  const showFullLeaderboard = location.state?.showFullLeaderboard;
  const selectedDataset = location.state?.selectedDataset;
  
  // If showing full leaderboard for a specific dataset
  if (showFullLeaderboard && selectedDataset) {
    // Find the matching dataset from live leaderboard
    const datasetSubmissions = liveLeaderboard.filter(submission => {
      const datasetDisplayName = `${submission.dataset_name.replace('flores_', '').replace('_translation', '')} – BLEU`.replace(/^\w/, c => c.toUpperCase());
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