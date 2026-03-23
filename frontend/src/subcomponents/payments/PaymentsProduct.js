import React, { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import { Link, useLocation } from "react-router-dom";
import { accountPath } from "../../constants/RouteConstants";
import { createCheckoutSession } from "../../redux/UserSlice";

const PaymentsProduct = () => {
  let dispatch = useDispatch();
  const [stripeUrl, setStripeUrl] = useState("");
  const location = useLocation();

  useEffect(() => {
    const productHash = new URLSearchParams(location.search).get("product_hash");
    const freeTrialCode = new URLSearchParams(location.search).get(
      "free_trial_code"
    );

    if (productHash) {
      var params = { product_hash: productHash };
      if (freeTrialCode) {
        params["free_trial_code"] = freeTrialCode;
      }
      dispatch(createCheckoutSession(params)).then((resp) => {
        var url = resp["payload"];
        window.open(url, "_blank");
        setStripeUrl(url);
      });
    }
  }, [dispatch, location.search]);

  return (
    <div className="bg-[#141414] p-8 rounded-md shadow-lg w-96 mx-auto mt-20 text-white">
      <h6 className="font-bold text-2xl mb-4">Subscribe</h6>
      <p className="mb-4">If tab doesn't open, click to proceed to payments</p>
      <button
        className="bg-blue-600 w-full py-2 rounded-md text-white hover:bg-blue-700 focus:outline-none focus:border-blue-900 focus:ring focus:ring-blue-200 active:bg-blue-800 mb-4"
        onClick={() => {
          window.open(stripeUrl, "_blank");
        }}
      >
        Proceed
      </button>
      <Link
        to={accountPath}
        className="bg-cyan-700 w-full py-2 rounded-md text-center block hover:bg-gray-600 focus:outline-none focus:border-gray-900 focus:ring focus:ring-gray-200 active:bg-[#141414]"
      >
        Back to Pricing
      </Link>
    </div>
  );
};

export default PaymentsProduct;
