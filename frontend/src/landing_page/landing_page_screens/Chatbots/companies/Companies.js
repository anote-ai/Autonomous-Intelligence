import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { createcompany, companies} from "../../../../constants/RouteConstants";

const Companies = () => {
  const [companies, setCompanies] = useState([]);
  const urlObject = new URL(window.location.origin);

  //check log in status
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  const accessToken = localStorage.getItem("accessToken");
  const sessionToken = localStorage.getItem("sessionToken");
  if (accessToken || sessionToken) {
    if (!isLoggedIn) {
      setIsLoggedIn(true);
    }
  } else {
    if (isLoggedIn) {
      setIsLoggedIn(false);
    }
  }
  var showRestrictedRouteRequiringUserSession = isLoggedIn;

  var hostname = urlObject.hostname;
  if (hostname.startsWith("www.")) {
    hostname = hostname.substring(4);
  }
  urlObject.hostname = `chat.${hostname}`;

  //getting user's made chatbots
  const [userChatbots, setUserChatbots] = useState([]);


  var startPath = urlObject.toString();
  useEffect(() => {
    axios.get("/api/companies", { withCredentials: true })
      .then(res => setCompanies(res.data))
      .catch(err => console.error("Error fetching companies:", err));

    if (isLoggedIn && accessToken) {
      axios.get("/api/user/companies", {
        withCredentials: true,
        headers: {
          Authorization: `Bearer ${accessToken}`
        }
      })
      .then(res => {
        console.log("User Chatbots API Response:", res.data); // Add this
        setUserChatbots(res.data);
      })
      .catch(err => console.error("Error fetching user chatbots:", err));
    }
  }, [isLoggedIn, accessToken]);




  return (
    <section className="text-gray-100 body-font overflow-hidden min-h-screen bg-black px-4 py-10">
      <div className="flex flex-col text-center w-full mb-10">
        <h1 className="sm:text-5xl text-4xl font-extrabold title-font bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent w-fit mx-auto px-4 py-2">
          Companies
        </h1>
      </div>

      <div className="container mx-auto flex flex-col sm:flex-row sm:justify-center sm:items-start gap-12 px-4">
        <div className="sm:w-1/2 w-full flex flex-col items-center">
          <h2 className="text-2xl font-semibold mb-6 text-center">Our Company Chatbots</h2>

          <div className="w-full max-w-md h-60 overflow-y-auto border border-gray-600 rounded-md p-4 space-y-4">
          {companies.map((company) => (
              <Link
                key={company.id}
                to={company.path}
                className="block border border-gray-600 hover:border-yellow-400 p-3 rounded-md text-center hover:bg-gray-800 transition"
              >
                {company.name}
              </Link>
            ))}
          </div>
        </div>

        <div className="sm:w-1/2 w-full flex flex-col items-center text-center">
          <h2 className="text-2xl font-semibold mb-3">Make Your Own</h2>
          <p className="text-sm text-gray-400 max-w-xs mb-6">
            Create an intelligent chatbot for your company, no coding necessary.
          </p>

          {showRestrictedRouteRequiringUserSession && (
          <div className="w-full max-w-md border border-gray-600 rounded-md mb-6 p-4">
            <h3 className="text-lg font-semibold mb-2 text-left">Your Existing Chatbots</h3>
            <table className="w-full text-sm text-left text-gray-300">
              <thead className="text-xs uppercase text-gray-500 border-b border-gray-700">
                <tr>
                  <th scope="col" className="px-2 py-2">Name</th>
                  <th scope="col" className="px-2 py-2">Link</th>
                </tr>
              </thead>
              <tbody>
                {userChatbots.map((bot) => (
                  <tr key={bot.id}>
                    <td className="px-2 py-2">{bot.name}</td>
                    <td className="px-2 py-2">
                      <Link to={bot.path} className="text-yellow-400 hover:underline">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {showRestrictedRouteRequiringUserSession ? (
          <a
            href={companies}
            className="btn-black px-6 py-2 border border-white rounded hover:bg-white hover:text-black transition"
          >
            Get Started
          </a>
        ) : (
          <a
            href={startPath}
            className="btn-black px-6 py-2 border border-white rounded hover:bg-white hover:text-black transition"
          >
            Get Started
          </a>
        )}

        </div>
      </div>
    </section>
  );
};

export default Companies;