import React, { useState } from "react";
import { useDispatch } from "react-redux";
import { resetPassword } from "../../redux/UserSlice";

function PasswordReset(props) {
  let dispatch = useDispatch();
  const [password, setPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");

  function onHandlePressResetPassword() {
    props.setStatusMessage("");
    if (!password) {
      props.setStatusMessage("Must enter a password");
    } else if (password !== repeatPassword) {
      props.setStatusMessage("Passwords much match");
    } else {
      dispatch(
        resetPassword({
          email: props.forgotPasswordEmail,
          passwordResetCode: props.forgotPasswordCode,
          password: password,
        })
      ).then((response) => {
        if (response.payload["status"] === "OK") {
          if ("token" in response.payload) {
            localStorage.setItem("sessionToken", response.payload["token"]);
            window.location.reload();
          }
        } else {
          props.setStatusMessage(response.payload["status"]);
        }
      });
    }
  }

  return (
    <div className="LoginComponent">
      <h1 className="my-4 font-bold text-3xl">Reset Your Password</h1>
      <input
        className="searchBoxCommon LoginForm"
        placeholder="Enter Password"
        onChange={(e) => {
          setPassword(e.target.value);
        }}
        type="password"
        id="dsearch"
        name="dsearch"
      />
      <input
        className="searchBoxCommon LoginForm"
        placeholder="Repeat Password"
        onChange={(e) => {
          setRepeatPassword(e.target.value);
        }}
        type="password"
        id="dsearch"
        name="dsearch"
      />
      <button
        onClick={() => {
          onHandlePressResetPassword();
        }}
        style={{ marginTop: "20px" }}
        className="ButtonType6"
      >
        Confirm
      </button>
      {props.statusMessage && (
        <p style={{ color: "#F65F50" }}>{props.statusMessage}</p>
      )}
      <div className="LoginComponentDontHave">
        <p>
          Changed your mind?{" "}
          <span
            className={"UncursorableButton"}
            onClick={() => {
              props.setPageState(1);
            }}
            style={{ color: "#40C6FF" }}
          >
            Log In
          </span>
        </p>
      </div>
    </div>
  );
}

export default PasswordReset;
