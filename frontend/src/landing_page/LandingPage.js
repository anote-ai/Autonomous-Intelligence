import "./landing_page_styles/LandingPage.css";
import "./landing_page_styles/LandingPageFiletypes.css";
import "./landing_page_styles/LandingPageValue.css";
import "./landing_page_styles/LandingPageApplications.css";
import "./landing_page_styles/LandingPageSampleProjects.css";
import "./landing_page_styles/LandingPageEllipse.css";
import "./landing_page_styles/LandingPageLabel.css";
import "./landing_page_styles/LandingPageFooter.css";
import React, { useState, useEffect, useRef } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import FAQs from "./landing_page_screens/FAQs";
import SampleProjects from "./landing_page_screens/SampleProjects";
import Research from "./landing_page_components/Research";
import FinanceGPT from "./landing_page_screens/FinanceGPT";
import DownloadPrivateGPT from "../components/DownloadPrivateGPT";
import Customers from "./landing_page_screens/Customers/Customers";
import {
  faqsPath,
  sampleProjectsPath,
  researchPath,
  downloadPrivateGPTPath,
  customersPath,
  customerCaseStudyPath,
  pricingPath,
  registryPath,
  financeGPTPath,
  homePath,
  gtmPath,
  chatbots,
  languages,
  companies,
  createcompany,
  evaluations,
  leaderboard,
  submittoleaderboardPath,
} from "../constants/RouteConstants";
import Home from "./landing_page_screens/Home/Home";
import Footer from "./landing_page_components/Footer";
import Banner from "./landing_page_components/Banner";
import Navbar from "./landing_page_components/Navbar";
import { Helmet } from "react-helmet";

import { useDispatch } from "react-redux";
import { useLocation } from "react-router-dom";
import { robotHeader } from "../util/RobotHeader";
import Pricing from "./landing_page_screens/Pricing";
import Registry from "./landing_page_screens/Registry";
import CustomerCaseStudy from "./landing_page_screens/Customers/CustomerCaseStudy";
import GTMChatbot from "./landing_page_screens/Chatbots/companies/GTMChatbot";
import ChatbotLanding from "./landing_page_screens/Chatbots/ChatbotLanding";
import Languages from "./landing_page_screens/Chatbots/languages/Languages";
import { LANGUAGE_ROUTES } from "../constants/RouteConstants";
import Companies from "./landing_page_screens/Chatbots/companies/Companies";
import CreateCompany from "./landing_page_screens/Chatbots/companies/CreateCompany";
import TranslateSentences from "./landing_page_screens/Chatbots/evaluations/Evaluations";
import SubmitToLeaderboard from "../components/SubmitToLeaderboard";
import Leaderboard from "../components/Leaderboard";

function LandingPage() {
  const location = useLocation();
  let dispatch = useDispatch();

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

  let robotMetaTag = robotHeader();

  const [open, setOpen] = useState(false);

  return (
    <div>
      <Helmet>
        <title>Panacea</title>
        {robotMetaTag}
      </Helmet>
      {/* <Banner open={open} /> */}
      <Navbar open={open} setOpen={setOpen} />
      <div className="">
        <Routes>
          <Route index element={<Home open={open} />} />,
          <Route path={homePath} element={<Home />} />
          <Route path={faqsPath} index element={<FAQs />} />
          <Route path={financeGPTPath} index element={<FinanceGPT />} />
          <Route path={downloadPrivateGPTPath} index element={<DownloadPrivateGPT/>} />
          <Route path={customersPath} index element={<Customers />} />
          <Route path={customerCaseStudyPath} index element={<CustomerCaseStudy />} />
          <Route path={pricingPath} index element={<Pricing />} />
          <Route path={registryPath} index element={<Registry />} />
          <Route path={sampleProjectsPath} index element={<SampleProjects />} />
          <Route path={researchPath} index element={<Research />} />
          <Route path={gtmPath} element = {<GTMChatbot />} />
          <Route path={chatbots} element = {<ChatbotLanding />} />
          <Route path={languages} element = {<Languages />} />
          <Route path="/languages/:lang" element={<Languages />} />
          <Route path={evaluations} element={<TranslateSentences />} />
          <Route path={leaderboard} element={<Leaderboard />} />
          <Route path={submittoleaderboardPath} element={<SubmitToLeaderboard />} />

          <Route path={companies} element = {<Companies />} />
          <Route path={createcompany} element = {<CreateCompany />} />
          <Route path="*" element={<Navigate replace to="/" />} />
        </Routes>
      </div>
      {/* <Footer /> */}
    </div>
  );
}

export default LandingPage;
