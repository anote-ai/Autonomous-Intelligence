import React, { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

const TranslateSentences = () => {
  const [error, setError] = useState(null);
  const [datasets, setDatasets] = useState([]); // Made dynamic
  const navigate = useNavigate();



  const handleSubmitToLeaderboard = () => {
    navigate("/submit-to-leaderboard");
  };

  // Fetch dynamic leaderboard data
  useEffect(() => {
    const fetchLeaderboardData = async () => {
      try {
        const response = await axios.get("http://localhost:5001/public/get_leaderboard");
        if (response.data.success) {
          // Group submissions by dataset and metric, create the same structure as before
          const groupedData = {};
          response.data.leaderboard.forEach(submission => {
            // Create appropriate key based on dataset name and evaluation metric
            let key;
            let displayName;
            
            if (submission.dataset_name.includes('_bertscore')) {
              // BERTScore datasets
              const language = submission.dataset_name.replace('flores_', '').replace('_translation_bertscore', '');
              key = `${submission.dataset_name}`;
              displayName = `${language.charAt(0).toUpperCase() + language.slice(1)} – BERTScore`;
            } else {
              // BLEU datasets - use the exact dataset name as key
              const language = submission.dataset_name.replace('flores_', '').replace('_translation', '');
              key = `${submission.dataset_name}`;
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

          // Sort models by score (descending) and assign ranks within each category
          Object.keys(groupedData).forEach(key => {
            groupedData[key].models.sort((a, b) => b.score - a.score);
            groupedData[key].models = groupedData[key].models.map((model, index) => ({
              ...model,
              rank: index + 1  // Rank starts at 1 for each category
            }));
          });
          
          console.log('Available leaderboard keys:', Object.keys(groupedData));
          console.log('Grouped data:', groupedData);
          
          // Create datasets in original static order, but replace BLEU sections with dynamic data
          const datasets = [
            // Spanish BLEU - dynamic data
            groupedData['flores_spanish_translation'] || {
              name: "Spanish – BLEU",
              url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
              models: [
                { rank: 1, model: "GPT-4o Zero-Shot", score: 0.523, updated: "Aug 2025" },
                { rank: 2, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.521, updated: "Aug 2025" },
                { rank: 3, model: "Gemini 2.5 Flash Zero-Shot", score: 0.511, updated: "Aug 2025" },
              ]
            },
            // Spanish BERTScore - dynamic data
            groupedData['flores_spanish_translation_bertscore'] || {
              name: "Spanish – BERTScore",
              url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
              models: [
                { rank: 1, model: "GPT-4o Zero-Shot", score: 0.886, updated: "Aug 2025" },
                { rank: 2, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.886, updated: "Aug 2025" },
                { rank: 3, model: "Gemini 2.5 Flash Zero-Shot", score: 0.883, updated: "Aug 2025" },
              ]
            },
            // Japanese BLEU - dynamic data
            groupedData['flores_japanese_translation'] || {
              name: "Japanese – BLEU",
              url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
              models: [
                { rank: 1, model: "GPT-4o Zero-Shot", score: 0.66, updated: "Aug 2025" },
                { rank: 2, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.652, updated: "Aug 2025" },
                { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.639, updated: "Aug 2025" },
              ]
            },
            // Japanese BERTScore - dynamic data
            groupedData['flores_japanese_translation_bertscore'] || {
              name: "Japanese – BERTScore",
              url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
              models: [
                { rank: 1, model: "GPT-4o Zero-Shot", score: 0.883, updated: "Aug 2025" },
                { rank: 2, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.878, updated: "Aug 2025" },
                { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.874, updated: "Aug 2025" },
              ]
            },
            // Arabic BLEU - dynamic data
            groupedData['flores_arabic_translation'] || {
              name: "Arabic – BLEU",
              url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
              models: [
                { rank: 1, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.53, updated: "Aug 2025" },
                { rank: 2, model: "GPT-4o Zero-Shot", score: 0.524, updated: "Aug 2025" },
                { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.518, updated: "Aug 2025" },
              ]
            },
            // Arabic BERTScore - dynamic data
            groupedData['flores_arabic_translation_bertscore'] || {
              name: "Arabic – BERTScore",
              url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
              models: [
                { rank: 1, model: "GPT-4o Zero-Shot", score: 0.887, updated: "Aug 2025" },
                { rank: 2, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.887, updated: "Aug 2025" },
                { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.884, updated: "Aug 2025" },
              ]
            },
            // Chinese BLEU - dynamic data  
            groupedData['flores_chinese_translation'] || {
              name: "Chinese – BLEU",
              url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
              models: [
                { rank: 1, model: "GPT-4o Zero-Shot", score: 0.616, updated: "Aug 2025" },
                { rank: 2, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.615, updated: "Aug 2025" },
                { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.257, updated: "Aug 2025" },
              ]
            },
            // Chinese BERTScore - dynamic data
            groupedData['flores_chinese_translation_bertscore'] || {
              name: "Chinese – BERTScore",
              url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
              models: [
                { rank: 1, model: "GPT-4o Zero-Shot", score: 0.898, updated: "Aug 2025" },
                { rank: 2, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.897, updated: "Aug 2025" },
                { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.892, updated: "Aug 2025" },
              ]
            },
            // Korean BLEU - dynamic data
            groupedData['flores_korean_translation'] || {
              name: "Korean – BLEU",
              url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
              models: [
                { rank: 1, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.581, updated: "Aug 2025" },
                { rank: 2, model: "GPT-4o Zero-Shot", score: 0.577, updated: "Aug 2025" },
                { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.559, updated: "Aug 2025" },
              ]
            },
            // Korean BERTScore - dynamic data
            groupedData['flores_korean_translation_bertscore'] || {
              name: "Korean – BERTScore",
              url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
              models: [
                { rank: 1, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.874, updated: "Aug 2025" },
                { rank: 2, model: "GPT-4o Zero-Shot", score: 0.872, updated: "Aug 2025" },
                { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.868, updated: "Aug 2025" },
              ]
            },
          ];

          console.log('Final datasets array length:', datasets.length);
          console.log('Final datasets:', datasets.map(d => d.name));
          setDatasets(datasets);
        }
      } catch (err) {
        console.error("Error fetching leaderboard data:", err);
        // Fallback to original static data if API fails
        setDatasets([
          {
            name: "Spanish – BLEU",
            url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
            models: [
              { rank: 1, model: "GPT-4o Zero-Shot", score: 0.523, updated: "Aug 2025" },
              { rank: 2, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.521, updated: "Aug 2025" },
              { rank: 3, model: "Gemini 2.5 Flash Zero-Shot", score: 0.511, updated: "Aug 2025" },
            ],
          },
          // ... other static datasets as fallback
        ]);
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
              {dataset.models.slice(0, 5).map((m) => (
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
                    onClick={() => navigate('/leaderboard', { 
                      state: { 
                        selectedDataset: dataset.name,
                        showFullLeaderboard: true 
                      } 
                    })}
                    className="text-blue-400 hover:text-blue-300 underline text-sm font-medium transition-colors"
                  >
                    View all {dataset.models.length} models →
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
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
