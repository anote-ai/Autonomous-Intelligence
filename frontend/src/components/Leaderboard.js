import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";

const Leaderboard = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [submissions, setSubmissions] = useState([]);

  // Get the selected dataset from navigation state
  const selectedDataset = location.state?.selectedDataset || "Unknown Dataset";

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        const response = await axios.get(`${process.env.REACT_APP_BACK_END_HOST}/public/get_leaderboard`);
        if (response.data.success) {
          // Filter submissions for the selected dataset
          const datasetSubmissions = response.data.leaderboard.filter(submission => {
            // Handle both BLEU and BERTScore datasets
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

          // Sort by score (descending) and add ranks
          const sortedSubmissions = datasetSubmissions
            .sort((a, b) => b.score - a.score)
            .map((submission, index) => ({
              ...submission,
              rank: index + 1
            }));

          setSubmissions(sortedSubmissions);
        }
      } catch (err) {
        console.error("Error fetching leaderboard:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchLeaderboard();
  }, [selectedDataset]);

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
        ) : submissions.length > 0 ? (
            <div className="bg-gray-800 rounded-lg overflow-hidden">
              <div className="grid grid-cols-4 bg-gray-700 p-4 font-bold text-white">
                <div>Rank</div>
                <div>Model Name</div>
              <div>Score</div>
                <div>Submitted</div>
              </div>
            {submissions.map((submission, index) => (
                <div
                  key={submission.id || index}
                  className={`grid grid-cols-4 p-4 ${
                  index % 2 === 0 ? "bg-gray-800" : "bg-gray-700"
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
            <div className="text-white text-lg">No submissions found for {selectedDataset}</div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Leaderboard; 