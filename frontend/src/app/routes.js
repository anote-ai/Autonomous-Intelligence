import React from "react";
import { Navigate, Route } from "react-router-dom";
import CheckLogin from "../components/CheckLogin";
import Organizations from "../components/Organizations";
import LanguagesDirectory from "../components/LanguagesDirectory";
import PersonsDirectory from "../components/PersonsDirectory";
import PersonChat from "../components/PersonChat";
import Home from "../financeGPT/components/Home";
import PlaybookView from "../financeGPT/components/PlaybookView";
import GTMChatbot from "../landing_page/landing_page_screens/Chatbots/companies/GTMChatbot";
import Languages from "../landing_page/landing_page_screens/Chatbots/languages/Languages";
import Companies from "../landing_page/landing_page_screens/Chatbots/companies/Companies";
import CreateCompany from "../landing_page/landing_page_screens/Chatbots/companies/CreateCompany";
import PaymentsComponent from "../subcomponents/payments/PaymentsComponent";
import PaymentsProduct from "../subcomponents/payments/PaymentsProduct";
import { APISKeyDashboard } from "../subcomponents/api/APISKeyDashboard";
import {
  apiKeyDashboardPath,
  billingPath,
  chatbotPath,
  companies,
  createcompany,
  gtmPath,
  homePath,
  languages,
  languagesDirectoryPath,
  organizationsPath,
  personsPath,
  playbookPath,
  pricingRedirectPath,
} from "../constants/RouteConstants";

export function buildRoutes({
  isLoggedIn,
  onAuthChange,
  onSidebarCollapsedChange,
}) {
  const homeScreen = (
    <Home onSidebarCollapsedChange={onSidebarCollapsedChange} />
  );

  return (
    <>
      <Route
        index
        element={
          <CheckLogin
            isLoggedIn={isLoggedIn}
            onAuthChange={onAuthChange}
            onSidebarCollapsedChange={onSidebarCollapsedChange}
          />
        }
      />
      <Route path={homePath} element={homeScreen} />
      <Route path={gtmPath} element={<GTMChatbot />} />
      <Route path={languages} element={<Languages />} />
      <Route path="/languages/:lang" element={<Languages />} />
      <Route path={createcompany} element={<CreateCompany />} />
      <Route path={companies} element={<Companies />} />
      <Route path={organizationsPath} element={<Organizations />} />
      <Route path={languagesDirectoryPath} element={<LanguagesDirectory />} />
      <Route path={personsPath} element={<PersonsDirectory />} />
      <Route path="/person/:slug" element={<PersonChat />} />
      <Route
        path={billingPath}
        element={isLoggedIn ? <PaymentsComponent /> : <Navigate replace to="/" />}
      />
      <Route
        path={pricingRedirectPath}
        element={isLoggedIn ? <PaymentsProduct /> : <Navigate replace to="/" />}
      />
      <Route
        path={chatbotPath}
        element={isLoggedIn ? homeScreen : <Navigate replace to="/" />}
      />
      <Route
        path={apiKeyDashboardPath}
        element={isLoggedIn ? <APISKeyDashboard /> : <Navigate replace to="/" />}
      />
      {/* Playbook (shared chat) — accessible to anyone, no auth required */}
      <Route path={playbookPath} element={<PlaybookView />} />
      <Route path="*" element={<Navigate replace to="/" />} />
    </>
  );
}
