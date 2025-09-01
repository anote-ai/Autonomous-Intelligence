import React, { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

const TranslateSentences = () => {
  const [error, setError] = useState(null);
  const [datasets, setDatasets] = useState([]); // Made dynamic
  const [openIndex, setOpenIndex] = useState(null);
  const [expandedDatasets, setExpandedDatasets] = useState({});
  const navigate = useNavigate();

  const handleClick = (index) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  const toggleDatasetExpansion = (datasetIndex) => {
    setExpandedDatasets(prev => ({
      ...prev,
      [datasetIndex]: !prev[datasetIndex]
    }));
  };

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



  const handleSubmitToLeaderboard = () => {
    navigate("/submit-to-leaderboard");
  };

  // Fetch dynamic leaderboard data
  useEffect(() => {
    const fetchLeaderboardData = async () => {
      try {
        console.log('Fetching from:', `${process.env.REACT_APP_BACK_END_HOST}/public/get_leaderboard`);
        const response = await axios.get(`${process.env.REACT_APP_BACK_END_HOST}/public/get_leaderboard`);
        console.log('API Response:', response.data);
        
        if (response.data.success && response.data.leaderboard) {
          // Group submissions by dataset and metric
          const groupedData = {};
          response.data.leaderboard.forEach(submission => {
            let key = submission.dataset_name;
            let displayName;
            
            if (submission.dataset_name.includes('_bertscore')) {
              const language = submission.dataset_name.replace('flores_', '').replace('_translation_bertscore', '');
              displayName = `${language.charAt(0).toUpperCase() + language.slice(1)} – BERTScore`;
            } else {
              const language = submission.dataset_name.replace('flores_', '').replace('_translation', '');
              displayName = `${language.charAt(0).toUpperCase() + language.slice(1)} – BLEU`;
            }
            
            if (!groupedData[key]) {
              groupedData[key] = {
                name: displayName,
                url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
                models: []
              };
            }
            groupedData[key].models.push({
              model: submission.model_name,
              score: submission.score,
              updated: new Date(submission.submitted_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
            });
          });

          // Sort models by score (descending) and assign ranks
          Object.keys(groupedData).forEach(key => {
            groupedData[key].models.sort((a, b) => b.score - a.score);
            groupedData[key].models = groupedData[key].models.map((model, index) => ({
              ...model,
              rank: index + 1
            }));
          });
          
          console.log('Available leaderboard keys:', Object.keys(groupedData));
          console.log('Grouped data:', groupedData);
          
          // Simply use all available datasets from the API
          const datasetsArray = Object.values(groupedData);
          console.log('Final datasets count:', datasetsArray.length);
          
          setDatasets(datasetsArray);
          setError(null); // Clear any previous errors
        } else {
          console.log('API returned unsuccessful response');
          setError("No leaderboard data available");
        }
      } catch (err) {
        console.error("Error fetching leaderboard data:", err);
        setError(`Failed to load leaderboard data: ${err.message}`);
      }
    };

    fetchLeaderboardData();
  }, []);

  return (
    <section className="bg-black min-h-screen py-10 px-4 text-gray-100">
      <div className="text-center mb-10">
        <h1 className="text-4xl sm:text-5xl font-extrabold bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent mb-4">
          Evaluation Leaderboard
        </h1>

        <button
          className="btn-black px-6 py-2 border border-yellow rounded hover:bg-white hover:text-white transition mb-6"
          onClick={handleSubmitToLeaderboard}
        >
        Submit Model to Leaderboard
        </button>
      </div>

      <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-12">
        {datasets.map((dataset, i) => (
          <div key={i} className="bg-gray-950 p-6 rounded-xl shadow-md border border-gray-800">
            <h2 className="text-xl font-semibold text-[#EDDC8F] mb-2">{dataset.name}</h2>
            <a
              href={dataset.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-400 hover:underline mb-4 inline-block"
            >
              View Dataset
            </a>
            <div className="mt-2 space-y-2">
              {(expandedDatasets[i] ? dataset.models : dataset.models.slice(0, 5)).map((m) => (
                <div
                  key={m.rank}
                  className="flex items-center justify-between bg-gray-900 p-3 rounded-lg"
                >
                  <div>
                    <p className="font-medium text-white">
                      {m.rank}. {m.model}
                    </p>
                    <p className="text-sm text-gray-400">
                      Updated: {m.updated}
                    </p>
                  </div>
                  <div className="text-lg font-bold text-[#F1CA57]">{typeof m.score === 'number' ? m.score.toFixed(3) : m.score}</div>
                </div>
              ))}
              {dataset.models.length > 5 && (
                <div className="mt-4 text-center">
                  <button
                    onClick={() => toggleDatasetExpansion(i)}
                    className="text-blue-400 hover:text-blue-300 underline text-sm font-medium transition-colors"
                  >
                    {expandedDatasets[i] ? 'Show less' : `View all ${dataset.models.length} models →`}
                  </button>
                </div>
              )}
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
      
      <div className="max-w-4xl mx-auto mt-16 flex flex-col items-center">
        {error && (
          <div className="mt-6 text-red-500 bg-red-900 p-4 rounded-md w-full text-center">
            {error}
          </div>
        )}
      </div>
    </section>
  );
};

export default TranslateSentences;
