// import React, { useState, useEffect } from "react";
// import { useDispatch } from "react-redux";
// import fetcher from "../../http/RequestConfig";
// import { createPortalSession } from "../../redux/UserSlice";
// import { Button } from "flowbite-react";
// import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
// import { faArrowRight } from "@fortawesome/free-solid-svg-icons";

// const Pricing = (props) => {
//   let dispatch = useDispatch();
//   var showCurrentPlan =
//     !(typeof props.currentPlanIndexOverride == "undefined") &&
//     props.currentPlanIndexOverride != -1;
//   const product3 = {
//     id: 3,
//     title: "Private Chatbot",
//     url: "https://docs.anote.ai/privategpt/privategpt.html",
//     forceContactUs: true,
//     tiers: [
//       {
//         name: "Basic",
//         price: "Free",
//         month: false,
//         features: [
//           "Access to the standard GPT model and Claude model without privacy-preserving features",
//           "Supported File Formats: PDFs, TXTs, DOCXs, PPTXs, etc.",
//           "Maximum Number of Files: Up to 5 files per month",
//           "Total File Size Limit: Up to 10 MB per month",
//           "Maximum Chats: 10 chats per month",
//         ],
//       },
//       {
//         name: "Standard",
//         price: "$500",
//         popular: true,
//         month: true,
//         features: [
//           "Privacy-preserving LLM using a model like GPT-4ALL or LLAMA2",
//           "Supported File Formats: PDFs, TXTs, DOCXs, PPTXs, etc.",
//           "Maximum Number of Files: Up to 20 files per month",
//           "Total File Size Limit: Up to 50 MB per month",
//           "Maximum Chats: 20 chats per month",
//         ],
//       },
//       {
//         name: "Premium",
//         price: "$1,000",
//         month: true,
//         features: [
//           "Privacy-preserving LLM using a model like GPT-4ALL or LLAMA2",
//           "Supported File Formats: PDFs, TXTs, DOCXs, PPTXs, etc.",
//           "Maximum Number of Files: Up to 50 files per month",
//           "Total File Size Limit: Up to 100 MB per month",
//           "Maximum Chats: 50 chats per month",
//         ],
//       },
//       {
//         name: "Enterprise",
//         month: false,
//         price: "Contact us",
//         features: [
//           "Fully custom fine tuned private LLM tailored to your specific use case and requirements",
//           "Advanced features and dedicated support",
//           "Maximum Number of Files: Customizable based on enterprise requirements",
//           "Total File Size Limit: Customizable based on enterprise requirements",
//           "Maximum Chats: Unlimited chats per month",
//         ],
//       },
//     ],
//   };

//   const [product, setProduct] = useState(product3);
//   const [selectedProductId, setSelectedProductId] = useState(
//     props.productIndex ? props.productIndex : product3.id
//   );

//   useEffect(() => {
//     switch (selectedProductId) {
//       case product3.id:
//         setProduct(product3);
//         break;
//       default:
//         break;
//     }
//   }, [selectedProductId]);

//   function buttonText(
//     tier,
//     product,
//     isDefaultFreeTrial,
//     currentPlanIndexOverride,
//     showCurrentPlan,
//     index
//   ) {

//     if (tier.name === "Basic") {
//       return "Contact Us";
//     }

//     if (isDefaultFreeTrial) {
//       // return "Sign Up";
//       return "Contact Us";
//     }
//     if (tier.price == "Contact us" || product.forceContactUs == true || !props.isCancelable) {
//       return "Contact us";
//     } else {
//       if (!showCurrentPlan) {
//         // return "Sign Up";
//         return "Contact Us";
//       } else {
//         if (currentPlanIndexOverride == index) {
//           return "Cancel";
//         } else {
//             if (props.disableUpgrade) {
//                 return "Contact us";
//             } else {
//                 if (currentPlanIndexOverride > index) {
//                     return "Downgrade";
//                 } else {
//                     return "Upgrade";
//                 }
//             }
//         }
//       }
//     }
//   }

//   function buttonAction(
//     tier,
//     product,
//     isDefaultFreeTrial,
//     currentPlanIndexOverride,
//     showCurrentPlan,
//     index
//   ) {
//     if (buttonText(tier, product, isDefaultFreeTrial, currentPlanIndexOverride, showCurrentPlan, index) === "Try Now") {
//       window.location.href = "/chatbot";
//       return;
//     }

//     if (tier.price == "Contact us" || product.forceContactUs == true || (!props.isCancelable && !isDefaultFreeTrial) || (showCurrentPlan && currentPlanIndexOverride != index && props.disableUpgrade && (!isDefaultFreeTrial))) {
//       var emailAddress = "nvidra@anote.ai";
//       var subject = "Anote Sales: " + product.title;
//       var body =
//         "Hi, I am interested in Anote's " +
//         product.title +
//         " product and I am looking to get more information.";
//       window.location.href =
//         "mailto:" +
//         emailAddress +
//         "?subject=" +
//         encodeURIComponent(subject) +
//         "&body=" +
//         encodeURIComponent(body);
//     } else {
//       if (!showCurrentPlan || isDefaultFreeTrial) {
//         window.location =
//           product.signUpBaseUrl + "?product_hash=" + tier.productHash;
//       } else {
//         var newPaymentTier = null;
//         if (currentPlanIndexOverride == index) {
//           newPaymentTier = 0;
//         } else {
//           newPaymentTier = index + 1;
//         }
//         dispatch(createPortalSession({ paymentTier: newPaymentTier })).then(
//           (resp) => {
//             if (!("error" in resp)) {
//               window.open(resp.payload, "_blank");
//             }
//           }
//         );
//       }
//     }
//   }

//   return (
//     <section className="text-anoteblack-100 body-font overflow-hidden">
//       <div className="px-5 mx-auto flex flex-col">
//         <div className="flex flex-wrap -m-4">
//           {product.tiers.map((tier, index) => (
//             <>
//               <div className="p-4 xl:w-1/4 md:w-1/2 w-full">
//                 <div
//                   className={`${
//                     (tier.popular && !showCurrentPlan) ||
//                     (props.currentPlanIndexOverride == index && !props.isDefaultFreeTrial)
//                       ? "border-4"
//                       : "border-2"
//                   } h-full p-6 rounded-lg  flex flex-col relative overflow-hidden`}
//                 >
//                   {((tier.popular && !showCurrentPlan) ||
//                     props.currentPlanIndexOverride == index) && !props.isDefaultFreeTrial && (
//                     <span class="bg-teal-500 text-white font-semibold px-3 py-1 tracking-widest text-xs absolute right-0 top-0 rounded-bl">
//                       {showCurrentPlan ? ("CURRENT PLAN") : "POPULAR"}
//                     </span>
//                   )}
//                   <div className="text-lg tracking-widest font-medium">
//                     {tier.name}
//                   </div>
//                   <h1
//                     className={`${
//                       tier.month ? "text-5xl pb-4" : "text-4xl pb-6"
//                     }  text-[#40C6FF]  mb-4 border-b border-gray-200 leading-none`}
//                   >
//                     <span>{tier.price}</span>
//                     {tier.month && (
//                       <span class="text-lg ml-1 font-normal text-gray-500">
//                         /mo
//                       </span>
//                     )}
//                   </h1>
//                   <div className="mb-5">
//                     {tier.features.map((feature) => (
//                       <p className="flex items-baseline text-anoteblack-200 mb-2">
//                         <span className="w-4 h-4 mr-2 inline-flex items-center justify-center bg-anoteblack-200 text-black rounded-full flex-shrink-0">
//                           <svg
//                             fill="none"
//                             stroke="currentColor"
//                             stroke-linecap="round"
//                             stroke-linejoin="round"
//                             stroke-width="2.5"
//                             className="w-3 h-3"
//                             viewBox="0 0 24 24"
//                           >
//                             <path d="M20 6L9 17l-5-5"></path>
//                           </svg>
//                         </span>
//                         {feature}
//                       </p>
//                     ))}
//                   </div>
//                   <button
//                     className="relative justify-start btn-black"
//                     onClick={() => {
//                       buttonAction(
//                         tier,
//                         product,
//                         props.isDefaultFreeTrial,
//                         props.currentPlanIndexOverride,
//                         showCurrentPlan,
//                         index
//                       );
//                     }}
//                   >
//                     {buttonText(
//                       tier,
//                       product,
//                       props.isDefaultFreeTrial,
//                       props.currentPlanIndexOverride,
//                       showCurrentPlan,
//                       index
//                     )}
//                     {/* {(tier.price == "Contact us" || (product.forceContactUs == true)) ? "Contact us" :
//                     (!showCurrentPlan ? "Sign Up" :
//                       ((props.currentPlanIndexOverride == index) ? "Cancel" : "Sign Up")
//                     )
//                     } */}
//                     <span className="absolute right-3">
//                       <FontAwesomeIcon
//                         icon={faArrowRight}
//                         className="ml-2 w-5 h-5"
//                       />
//                     </span>
//                   </button>
//                 </div>
//               </div>
//             </>
//           ))}
//         </div>
//       </div>
//     </section>
//   );
// };

// export default Pricing;


// @TODO 

import React, { useState } from "react";
import { useDispatch } from "react-redux";
import { createPortalSession } from "../../redux/UserSlice";
import { GetPrivateGPTDashboardUrl } from "../../util/DomainParsing";

const Pricing = (props) => {
  let dispatch = useDispatch();
  var showCurrentPlan = !(typeof props.currentPlanIndexOverride === "undefined");
  // const product3 = {
  //   id: 3,
  //   title: "Private Chatbot",
  //   url: "https://docs.anote.ai/privategpt/privategpt.html",
  //   forceContactUs: true,
  //   signUpBasePrivateGPTUrl: GetPrivateGPTDashboardUrl(),
  //   tiers: [
  //     {
  //       name: "Basic",
  //       price: "Free",
  //       month: false,
  //       productHash: "privategpt1",
  //       features: [
  //         "Access to the standard GPT model and Claude model without privacy-preserving features",
  //         "Supported File Formats: PDFs, TXTs, DOCXs, PPTXs",
  //         "Maximum Number of Files: Up to 5 files per month",
  //         "Total File Size Limit: Up to 10 MB per month",
  //         "Maximum Chats: 10 chats per month",
  //       ],
  //     },
  //     {
  //       name: "Standard",
  //       price: "$500",
  //       popular: true,
  //       month: true,
  //       productHash: "privategpt2",
  //       features: [
  //         "Privacy-preserving LLM using a model like GPT-4ALL or LLAMA2",
  //         "Supported File Formats: PDFs, TXTs, DOCXs, PPTXs",
  //         "Maximum Number of Files: Up to 20 files per month",
  //         "Total File Size Limit: Up to 50 MB per month",
  //         "Maximum Chats: 20 chats per month",
  //       ],
  //     },
  //     {
  //       name: "Premium",
  //       price: "$1,000",
  //       productHash: "privategpt3",
  //       month: true,
  //       features: [
  //         "Privacy-preserving LLM using a model like GPT-4ALL or LLAMA2",
  //         "Supported File Formats: PDFs, TXTs, DOCXs, PPTXs",
  //         "Maximum Number of Files: Up to 50 files per month",
  //         "Total File Size Limit: Up to 100 MB per month",
  //         "Maximum Chats: 50 chats per month",
  //       ],
  //     },
  //     {
  //       name: "Enterprise",
  //       month: false,
  //       price: "Contact us",
  //       features: [
  //         "Fully custom fine tuned private LLM tailored to your specific use case and requirements",
  //         "Maximum Number of Files: Customizable based on enterprise requirements",
  //         "Total File Size Limit: Customizable based on enterprise requirements",
  //         "Maximum Chats: Unlimited chats per month",
  //       ],
  //     },
  //   ],
  // };
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
    console.log(tier.price);
    console.log(product.forceContactUs);
    if (tier.price === "Contact us" || product.forceContactUs === true) {
      console.log(1);
      return "Contact us";
    } else {
      if (tier.name === "Basic") {
        // return "Try Now";
        return "Contact Us"
      }
      // if (product.title == "Private Chatbot" && tier.name == "Basic") {
      //   return "Try Now"
      // }
      if (!showCurrentPlan) {
        return "Sign Up";
      } else {
        if (currentPlanIndexOverride === index) {
          return "Cancel";
        } else {
          if (props.disableUpgrade) {
            console.log(2);
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
    // if (tier.price === "Free") {
    //   if (product.title === "Data Labeler") {
    //     window.location = "https://dashboard.anote.ai"; }
    //   // } else if (product.title === "Private Chatbot") {
    //   //   window.location = "https://privatechatbot.ai";
    //   // }
    // } else if (
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
      // Adjusted to ensure only one redirection happens based on conditions
      if (product.id === 1) {
        // window.location = product.signUpBaseUrl;
        window.location = product.signUpBaseUrl + "?product_hash=" + tier.productHash;
      } else if (product.id === 3) {
        // window.location = product.signUpBasePrivateGPTUrl;
        window.location = product.signUpBasePrivateGPTUrl + "?product_hash=" + tier.productHash;
      } else {
        // Assuming this else is for product.id other than 1 or 3, or index other than 0
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
      {/* <div className="flex flex-col text-center w-full mt-6">
          <h1 className="sm:text-4xl text-3xl font-medium title-font text-gray-100">
            {props.nameOverride == null ? "Pricing" : props.nameOverride}
          </h1>
        </div> */}
      <div className="container px-5 py-6 mx-auto flex flex-col">
        <div className="flex flex-wrap -m-4">
          {product.tiers.map((tier, index) => (
            <>
              <div className="p-4 xl:w-1/4 md:w-1/2 w-full">
                <div
                  className={`${
                    (tier.popular && !showCurrentPlan) ||
                    props.currentPlanIndexOverride == index
                      ? "border-[#F1CA57] border-4"
                      : "border-gray-300 border-2"
                  } h-full p-6 rounded-lg  flex flex-col relative overflow-hidden`}
                >
                  {((tier.popular && !showCurrentPlan) ||
                    props.currentPlanIndexOverride == index) && (
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
                    {/* {(tier.price == "Contact us" || (product.forceContactUs == true)) ? "Contact us" :
                    (!showCurrentPlan ? "Sign Up" :
                      ((props.currentPlanIndexOverride == index) ? "Cancel" : "Sign Up")
                    )
                    } */}
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
