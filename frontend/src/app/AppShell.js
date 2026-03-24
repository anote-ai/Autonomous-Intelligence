import { useState } from "react";
import { Helmet } from "react-helmet";
import { Flowbite } from "flowbite-react";
import { Routes } from "react-router-dom";
import MainNav from "../components/MainNav";
import { buildRoutes } from "./routes";
import { useSessionState } from "./useSessionState";

function AppShell() {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);
  const { isLoggedIn, refreshSession } = useSessionState();

  return (
    <Flowbite>
      <div className="DashboardView flex min-h-screen flex-col">
        <div id="wrapperDiv" className="flex-grow">
          <MainNav
            isLoggedIn={isLoggedIn}
            onAuthChange={refreshSession}
            isSidebarCollapsed={isSidebarCollapsed}
          />
          <Helmet>
            <title>Panacea</title>
          </Helmet>
          <Routes>
            {buildRoutes({
              isLoggedIn,
              onAuthChange: refreshSession,
              onSidebarCollapsedChange: setIsSidebarCollapsed,
            })}
          </Routes>
        </div>
      </div>
    </Flowbite>
  );
}

export default AppShell;
