import React from "react";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import PaymentsComponent from "../subcomponents/payments/PaymentsComponent";
import { useLocation } from "react-router-dom";
import "../styles/Login.css";
import { pricingRedirectPath } from "../constants/RouteConstants";
import HomeChatbot from "../financeGPT/components/Home";
import LoginModal from "./LoginModal";

function CheckLogin(props) {
  const navigate = useNavigate();
  const location = useLocation();
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  const [showLogin, setShowLogin] = useState(false);
  const [productHash, setProductHash] = useState("");
  const [freeTrialCode, setFreeTrialCode] = useState("");

  const accessToken = localStorage.getItem("accessToken");
  const sessionToken = localStorage.getItem("sessionToken");
  console.log("get access token");
  console.log(accessToken);
  
  // Update login state based on tokens
  useEffect(() => {
    if (accessToken || sessionToken) {
      if (!isLoggedIn) {
        setIsLoggedIn(true);
      }
    } else {
      if (isLoggedIn) {
        setIsLoggedIn(false);
      }
    }
  }, [accessToken, sessionToken, isLoggedIn]);

  // if (isLoggedIn && productHash !== null && productHash !== "") {
  //   setProductHash("");
  //   var fullPath = pricingRedirectPath + "?product_hash=" + productHash;
  //   if (freeTrialCode !== null && freeTrialCode !== "") {
  //     setFreeTrialCode("");
  //     fullPath += "&free_trial_code=";
  //     fullPath += freeTrialCode;
  //   }
  //   navigate(fullPath);
  // }

  // Listen for the custom event to show login
  useEffect(() => {
    const handleShowLogin = () => {
      setShowLogin(true);
    };

    window.addEventListener('showLogin', handleShowLogin);
    return () => {
      window.removeEventListener('showLogin', handleShowLogin);
    };
  }, []);

  var mainView = [];
  if (!isLoggedIn) {
    // Always show guest mode for non-logged-in users, with modal for login
    mainView = <HomeChatbot isGuestMode={true} onRequestLogin={() => setShowLogin(true)} setIsLoggedInParent={props.setIsLoggedInParent} />;
  } else if (!props.showRestrictedRouteRequiringPayments) {
    //mainView = <PaymentsComponent />;
    mainView = <HomeChatbot isGuestMode={false} setIsLoggedInParent={props.setIsLoggedInParent} />;
  }

  useEffect(() => {
    const accessToken = new URLSearchParams(location.search).get("accessToken");
    const refreshToken = new URLSearchParams(location.search).get(
      "refreshToken"
    );
    const productHashStr = new URLSearchParams(location.search).get(
      "product_hash"
    );

    if (productHashStr) {
      setProductHash(productHashStr);
    }
    const freeTrialCodeStr = new URLSearchParams(location.search).get(
      "free_trial_code"
    );

    if (freeTrialCodeStr) {
      setFreeTrialCode(freeTrialCodeStr);
    }

    console.log("accessToken checklogin");
    console.log(accessToken);
    console.log(refreshToken);
    // Save the tokens in local storage if they exist
    if (accessToken && refreshToken) {
      console.log("save access token");
      localStorage.setItem("accessToken", accessToken);
      localStorage.setItem("refreshToken", refreshToken);
      props.setIsLoggedInParent(true);
      navigate("/");
    }
  }, [location]);

  return (
    <div className="App">
      {mainView}
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
