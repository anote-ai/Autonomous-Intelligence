import React, { useState, useEffect, useRef, useLayoutEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import PDFUploader from "./PdfUploader";
import {
  faFileDownload,
  faPaperPlane,
  faUndoAlt,
} from "@fortawesome/free-solid-svg-icons";
import "../../landing_page_styles/LandingPageChatbot.css";
import { Flowbite, TextInput } from "flowbite-react";
import fetcher from "../../../http/RequestConfig";

const API_ENDPOINT = process.env.REACT_APP_API_ENDPOINT;

const Chatbot = (props) => {
  const [messages, setMessages] = useState([]);
  const [isFirstMessageSent, setIsFirstMessageSent] = useState(false);
  const inputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const responseColor = "#3A3B41";
  const userColor = "#3A3B41";

  const scrollableMessagesContainerRef = useRef(null);

  //initial state
  useEffect(() => {
    // TODO: Uncomment this line before deployment of backend
    // resetServer();
    setIsFirstMessageSent(false);
    setMessages([
      {
        message: "Hello, I am your Panacea, your agentic AI assistant. What can I do to help?",
        sentTime: "just now",
        direction: "incoming",
      },
    ]);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);


  const scrollToBottom = () => {
    if (scrollableMessagesContainerRef.current) {
      const { scrollHeight, clientHeight } = scrollableMessagesContainerRef.current;
      const maxScrollTop = scrollHeight - clientHeight;
      scrollableMessagesContainerRef.current.scrollTop = maxScrollTop > 0 ? maxScrollTop : 0;
    }
  };



  const handleDownload = async () => {
    try {
      const response = await fetcher('download-chat-history-demo', {
        method: 'POST',
        headers: {
          Accept: 'text/csv',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ chat_id: props.selectedChatId, chat_type: props.chat_type }),
      });
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', 'chat_history.csv'); // or any other filename
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (error) {
      console.error('Error downloading the file:', error);
    }
  };

  const handleTryMessage = (text) => {
    handleSendMessage(text);
  };


  const handleSendMessage = async (text, chat_id) => {
    inputRef.current.value = "";

    const tempMessageId = Date.now();
    setMessages((prevMessages) => [
      ...prevMessages,
      {
        message: text,
        direction: "outgoing",
      },
      {
        id: tempMessageId,
        message: "Loading...",
        direction: "incoming",
      },
    ]);
    //scrollToBottom(); // Scroll after setting the outgoing message

    try {
      const response = await fetcher("process-message-pdf-demo", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: text,
          chat_id: chat_id,
        }),
      });
      const response_data = await response.json();
      const answer = response_data.answer;
      setMessages((prevMessages) =>
        prevMessages.map((msg) =>
          msg.id === tempMessageId
            ? { ...msg, message: answer, id: undefined } // Replace the loading message
            : msg
        )
      );

      scrollToBottom(); // Scroll after receiving the response

      if (!isFirstMessageSent) {
        setIsFirstMessageSent(true);
      }
    } catch (e) {
      console.error("Error in fetcher:", e);
    }
  };


  // const resetServer = async () => {
  //   const response = await fetcher("reset-chat-demo", {
  //     method: "POST",
  //     headers: {
  //       Accept: "application/json",
  //       "Content-Type": "application/json",
  //     },
  //   });
  //   console.log("Reset server operation completed");

  //   setMessages([
  //     {
  //       message: "Hello, I am your Panacea, your agentic AI assistant. What can I do to help?",
  //       sentTime: "just now",
  //       direction: "incoming",
  //     },
  //   ]);
  //   setIsFirstMessageSent(false);
  // };

  return (
    <>
      <div className="min-h-[70vh] h-[70vh] mt-2 relative p-4 w-full rounded-2xl">
        <>
          <div className="flex flex-row justify-between">
            <FontAwesomeIcon
              icon={faUndoAlt}
              // onClick={resetServer}
              className="reset-icon"
            />
            <div className="text-white font-bold">Chat</div>
            <div className="send-button">
              <FontAwesomeIcon
                icon={faFileDownload}
                onClick={handleDownload}
              />
            </div>
          </div>
          <hr />
          <div className="flex flex-col mt-4 space-y-2 h-[60vh] overflow-y-scroll" ref={scrollableMessagesContainerRef}>
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`message ${msg.direction === "incoming" ? "incoming" : "outgoing"
                  }`}
              >
                <div className="message-content">
                  <div
                    className="message-text"
                    style={{
                      color:
                        msg.direction === "incoming"
                          ? responseColor
                          : userColor,
                    }}
                  >
                    {msg.message}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} /> {/* Empty div for scrolling */}
          </div>
          <div className="flex items-center w-[95%] mx-auto absolute bottom-5 ">
            <div className="mr-4 bg-gradient-to-r from-[#28B2FB] to-[#F1CA57] rounded-xl p-2 cursor-pointer text-black">
              <PDFUploader
                className=""
                chat_id={props.selectedChatId}
                handleForceUpdate={props.handleForceUpdate}
              />
            </div>
            <input
              className="w-full rounded-xl bg-[#141414] border-[#9B9B9B] focus:ring-0 focus:border-white text-white placeholder:text-[#9B9B9B]"
              type="text"
              placeholder="Ask your document a question"
              ref={inputRef} // Assign the input ref
              onKeyPress={(e) => {
                if (e.key === "Enter") {
                  const text = e.target.value;
                  handleTryMessage(
                    text,
                  );
                }
              }}
            />
            <div
              className="text-white bg-[#3A3B41] p-2 rounded-xl ml-4 cursor-pointer"
              onClick={() => {
                const text = inputRef.current.value; // Get the input value
                handleTryMessage(text);
              }}
            >
              <FontAwesomeIcon className="w-8" icon={faPaperPlane} />
            </div>
          </div>
        </>
      </div>
    </>
  );
}

export default Chatbot;
