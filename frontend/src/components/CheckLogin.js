import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import HomeChatbot from "../financeGPT/components/Home";
import LoginModal from "./LoginModal";

function CheckLogin({ isLoggedIn, onAuthChange, onSidebarCollapsedChange }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [showLogin, setShowLogin] = useState(false);
  const [productHash, setProductHash] = useState("");
  const [freeTrialCode, setFreeTrialCode] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const accessToken = params.get("accessToken");
    const refreshToken = params.get("refreshToken");
    const productHashStr = params.get("product_hash");

    if (productHashStr) {
      setProductHash(productHashStr);
      if (!isLoggedIn) {
        setShowLogin(true);
      }
    }
    const freeTrialCodeStr = params.get("free_trial_code");

    if (freeTrialCodeStr) {
      setFreeTrialCode(freeTrialCodeStr);
      if (!isLoggedIn) {
        setShowLogin(true);
      }
    }

    if (accessToken && refreshToken) {
      localStorage.setItem("accessToken", accessToken);
      localStorage.setItem("refreshToken", refreshToken);
      onAuthChange?.();
      navigate("/", { replace: true });
    }
  }, [isLoggedIn, location.search, navigate, onAuthChange]);

  return (
    <div>
      <HomeChatbot
        isGuestMode={!isLoggedIn}
        onSidebarCollapsedChange={onSidebarCollapsedChange}
      />
      <LoginModal
        isOpen={showLogin}
        onClose={() => setShowLogin(false)}
        productHash={productHash}
        freeTrialCode={freeTrialCode}
      />
    </div>
  );
}

export default CheckLogin;
