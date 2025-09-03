import React, { useState } from "react";
import { Link, BrowserRouter as Router } from "react-router-dom";
import CheckLogin from "./components/CheckLogin";
import MainNav from "./components/MainNav";
import { Helmet } from "react-helmet";
import { Routes, Route, Navigate } from "react-router-dom";
import {
  accountPath,
  pricingRedirectPath,
  chatbotPath,
  apiKeyDashboardPath,
  downloadPrivateGPTPath,
  homePath,
  gtmPath,
  languages, // Import connector options from RouteConstants
  companies,
  createcompany,
} from "./constants/RouteConstants";
import PaymentsComponent from "./subcomponents/payments/PaymentsComponent";
import PaymentsProduct from "./subcomponents/payments/PaymentsProduct";
import { Flowbite } from "flowbite-react";
import { refreshCredits, useUser, viewUser } from "./redux/UserSlice";
import { useDispatch } from "react-redux";
import { useEffect } from "react";
import Home from "./financeGPT/components/Home";
import { APISKeyDashboard } from "./subcomponents/api/APISKeyDashboard";
import DownloadPrivateGPT from "./components/DownloadPrivateGPT.js";
import GTMChatbot from "./landing_page/landing_page_screens/Chatbots/companies/GTMChatbot";
import ChatbotLanding from "./landing_page/landing_page_screens/Chatbots/ChatbotLanding";
import Languages from "./landing_page/landing_page_screens/Chatbots/languages/Languages";
import Companies from "./landing_page/landing_page_screens/Chatbots/companies/Companies";
import CreateCompany from "./landing_page/landing_page_screens/Chatbots/companies/CreateCompany";

function Dashboard() {
  const [darkTheme, setDarkTheme] = useState(true);
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

  let dispatch = useDispatch();

  useEffect(() => {
    if (isLoggedIn) {
      dispatch(viewUser());
      // dispatch(refreshCredits());
    }
  }, [isLoggedIn]);

  let user = useUser();

  var showRestrictedRouteRequiringPayments = false;
  if (user && user["paid_user"] != 0) {
    showRestrictedRouteRequiringPayments = true;
  }

  var isFreeTrial = false;
  if (user && user["is_free_trial"] == true) {
    isFreeTrial = true;
  }
  var numDaysLeft = "";
  if (user && user["end_date"]) {
    var currentDate = new Date();
    var endDate = new Date(user["end_date"]);
    var timeDifference = endDate - currentDate;
    var daysDifference = Math.ceil(timeDifference / (1000 * 60 * 60 * 24));
    numDaysLeft = daysDifference.toString();
  }

  var publicRoutes = [
    //this system needs to be fixed, all routes should be accessible post log-in
    <Route
      key="root"
      index
      element={
        <CheckLogin darkTheme={darkTheme} setIsLoggedInParent={setIsLoggedIn} />
      }
    />,
    <Route path={homePath} element={<Home />} />,
    <Route path={gtmPath} element={<GTMChatbot />} />,
    <Route path={languages} element={<Languages />} />,
    <Route path="/languages/:lang" element={<Languages />} />,
    <Route path={createcompany} element={<CreateCompany />} />,
    <Route path={companies} element={<Companies />} />,
  ];
  var privateRoutes = [
    <Route
      index
      element={
        <CheckLogin
          darkTheme={darkTheme}
          setIsLoggedInParent={setIsLoggedIn}
          showRestrictedRouteRequiringPayments={
            showRestrictedRouteRequiringPayments
          }
        />
      }
    />,
    showRestrictedRouteRequiringUserSession ? (
      <Route path={accountPath} element={<PaymentsComponent />} />
    ) : null,
    showRestrictedRouteRequiringUserSession ? (
      <Route path={pricingRedirectPath} element={<PaymentsProduct />} />
    ) : null,
    showRestrictedRouteRequiringUserSession ? (
      <Route path={chatbotPath} element={<Home />} />
    ) : null,
    showRestrictedRouteRequiringUserSession ? (
      <Route path={downloadPrivateGPTPath} element={<DownloadPrivateGPT />} />
    ) : null,
    showRestrictedRouteRequiringUserSession ? (
      <Route path={apiKeyDashboardPath} element={<APISKeyDashboard />} />
    ) : null,
  ];

  var daysStr = "";
  if (numDaysLeft == "0") {
    daysStr = "less than a day";
  } else if (numDaysLeft == "1") {
    daysStr = "1 day";
  } else {
    daysStr = numDaysLeft.toString() + " days";
  }

  return (
    <Flowbite
    // theme={{
    //   dark: darkTheme,
    // }}
    >
      <div className="DashboardView flex flex-col min-h-screen">
        <div id="wrapperDiv" className="flex-grow">
          {/* {isLoggedIn && isFreeTrial && <div className="mt-2 mb-2 ml-6" style={{ color: "white" }}>
            Your free trial ends in {daysStr}
            <Link to={accountPath} className="ml-3 text-blue-500">Upgrade</Link>
          </div>} */}
          {isLoggedIn && (
            <MainNav
              // darkTheme={darkTheme}
              // setDarkTheme={setDarkTheme}
              setIsLoggedInParent={setIsLoggedIn}
            />
          )}
          <Helmet>
            <title>Panacea</title>
          </Helmet>
          <Routes>
            {publicRoutes}
            {privateRoutes}
            <Route path="*" element={<Navigate replace to="/" />} />
          </Routes>
        </div>
      </div>
    </Flowbite>
  );
}
export default Dashboard;
