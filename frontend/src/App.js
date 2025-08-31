import Dashboard from "./Dashboard";
import { BrowserRouter as Router} from "react-router-dom";
import { ToastProvider } from "./components/Toast";
import BackendStatusToast from "./components/BackendStatusToast";

function App() {
  return (
    <ToastProvider>
      <BackendStatusToast />
      {
        <Router>
          <Dashboard />
        </Router>
      }
    </ToastProvider>
  );
}

export default App;