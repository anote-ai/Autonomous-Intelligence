
import React, { useState } from "react";
import { useDispatch } from "react-redux";
import { createPortalSession } from "../../redux/UserSlice";
import { GetPrivateGPTDashboardUrl } from "../../util/DomainParsing";

const Pricing = (props) => {
  let dispatch = useDispatch();
  var showCurrentPlan = !(typeof props.currentPlanIndexOverride === "undefined");
  const product3 = {
    id: 3,
    title: "Panacea",
    url: "https://docs.anote.ai/privategpt/privategpt.html",
    forceContactUs: true,
    signUpBasePrivateGPTUrl: GetPrivateGPTDashboardUrl(),
    tiers: [
      {
        name: "Personal",
        price: "Free",
        month: false,
        productHash: "privategpt1",
        features: [
          "Access to models like GPT, Claude, Mistral and Llama",
          "Supported File Formats: PDFs, TXTs",
          "Maximum Chats: 50 chats per month",
          "Maximum Number of Files: Up to 50 files per month",
        ],
      },
      {
        name: "Developer",
        price: "Custom",
        month: false,
        productHash: "privategpt2",
        features: [
          "Access to models like GPT, Claude, Mistral and Llama",
          "Supports custom API integrations",
          "Pay-per-use API for flexible usage at scale",
          "Supported File Formats: PDFs, TXTs, DOCXs, PPTXs",
        ],
      },
      {
        name: "Closed Source",
        price: "Contact us",
        month: false,
        productHash: "privategpt3",
        features: [
          "Custom closed-source agents available in registry",
          "Privacy-preserving LLM options, including models like GPT-4ALL, Mistral or LLAMA3",
          "Customizable agents based on your requirements",
        ],
      },
      {
        name: "Enterprise",
        price: "Contact us",
        month: false,
        productHash: "privategpt4",
        features: [
          "Private versions of agents with full data privacy",
          "Scalable infrastructure for high-volume needs",
          "Unlimited chats and files uploaded per month",
          "Custom API endpoints for secure, direct integration",
        ],
      },
    ],
  };


  const [product] = useState(product3);
  function buttonText(
    tier,
    product,
    currentPlanIndexOverride,
    showCurrentPlan,
    index
  ) {
    if (tier.price === "Contact us" || product.forceContactUs === true) {
      return "Contact us";
    } else {
      if (tier.name === "Basic") {
        return "Contact Us"
      }
      if (!showCurrentPlan) {
        return "Sign Up";
      } else {
        if (currentPlanIndexOverride === index) {
          return "Cancel";
        } else {
          if (props.disableUpgrade) {
            return "Contact us";
          } else {
            if (currentPlanIndexOverride > index) {
              return "Downgrade";
            } else {
              return "Upgrade";
            }
          }
        }
      }
    }
  }
  function buttonAction(
    tier,
    product,
    currentPlanIndexOverride,
    showCurrentPlan,
    index
  ) {
    if (
      tier.price === "Contact us" ||
      product.forceContactUs === true ||
      (showCurrentPlan &&
        currentPlanIndexOverride !== index &&
        props.disableUpgrade)
    ) {
      var emailAddress = "nvidra@anote.ai";
      var subject = "Anote Sales: " + product.title;
      var body =
        "Hi, I am interested in Anote's " +
        product.title +
        " product and I am looking to get more information.";
      window.location.href =
        "mailto:" +
        emailAddress +
        "?subject=" +
        encodeURIComponent(subject) +
        "&body=" +
        encodeURIComponent(body);
    } else if (!showCurrentPlan) {
      if (product.id === 1) {
        window.location = product.signUpBaseUrl + "?product_hash=" + tier.productHash;
      } else if (product.id === 3) {
        window.location = product.signUpBasePrivateGPTUrl + "?product_hash=" + tier.productHash;
      } else {
        window.location = product.signUpBaseUrl + "?product_hash=" + tier.productHash;
      }
    } else {
      dispatch(createPortalSession()).then((resp) => {
        if (!("error" in resp)) {
          window.open(resp.payload, "_blank");
        }
      });
    }
  }


  return (
    <section className="text-gray-100 body-font overflow-hidden">
      <div className="container px-5 py-6 mx-auto flex flex-col">
        <div className="flex flex-wrap -m-4">
          {product.tiers.map((tier, index) => (
            <>
              <div className="p-4 xl:w-1/4 md:w-1/2 w-full">
                <div
                  className={`${
                    (tier.popular && !showCurrentPlan) ||
                    props.currentPlanIndexOverride === index
                      ? "border-[#F1CA57] border-4"
                      : "border-gray-300 border-2"
                  } h-full p-6 rounded-lg  flex flex-col relative overflow-hidden`}
                >
                  {((tier.popular && !showCurrentPlan) ||
                    props.currentPlanIndexOverride === index) && (
                    <span className="bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black font-semibold px-3 py-1 tracking-widest text-xs absolute right-0 top-0 rounded-bl">
                      {showCurrentPlan ? "CURRENT PLAN" : "POPULAR"}
                    </span>
                  )}
                  <div className="text-lg tracking-widest font-medium">
                    {tier.name}
                  </div>
                  <h1
                    className={`${
                      tier.month ? "text-5xl pb-4" : "text-4xl pb-6"
                    } bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent  mb-4 border-b border-gray-200 leading-none`}
                  >
                    <span>{tier.price}</span>
                    {tier.month && (
                      <span className="text-lg ml-1 font-normal text-gray-500">
                        /mo
                      </span>
                    )}
                  </h1>
                  <div className="mb-5">
                    {tier.features.map((feature) => (
                      <p className="flex items-baseline text-anoteblack-200 mb-2">
                        <span className="w-4 h-4 mr-2 inline-flex items-center justify-center bg-anoteblack-200 text-black rounded-full flex-shrink-0">
                          <svg
                            fill="none"
                            stroke="currentColor"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="2.5"
                            className="w-3 h-3"
                            viewBox="0 0 24 24"
                          >
                            <path d="M20 6L9 17l-5-5"></path>
                          </svg>
                        </span>
                        {feature}
                      </p>
                    ))}
                  </div>
                  <button
                    onClick={() => {
                      buttonAction(
                        tier,
                        product,
                        props.currentPlanIndexOverride,
                        showCurrentPlan,
                        index
                      );
                    }}
                    className="btn-black flex items-center mt-auto py-2 px-4 w-full focus:outline-none "
                  >
                    {buttonText(
                      tier,
                      product,
                      props.currentPlanIndexOverride,
                      showCurrentPlan,
                      index
                    )}
                    <svg
                      fill="none"
                      stroke="currentColor"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      className="w-4 h-4 ml-auto"
                      viewBox="0 0 24 24"
                    >
                      <path d="M5 12h14M12 5l7 7-7 7"></path>
                    </svg>
                  </button>
                </div>
              </div>
            </>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Pricing;
