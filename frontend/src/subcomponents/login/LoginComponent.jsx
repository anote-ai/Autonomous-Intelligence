import React from "react";
import { useDispatch } from "react-redux";
import { useState } from "react";
import { login } from "../../redux/UserSlice";
import { TextInput } from "flowbite-react";

function LoginComponent(props) {
  let dispatch = useDispatch();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function onHandlePressLogin() {
    props.setStatusMessage("");
    if (!email) {
      props.setStatusMessage("Must enter an email address");
    } else if (!password) {
      props.setStatusMessage("Must enter a password");
    } else {
      if (props.addToast) {
        props.addToast("Signing in...", "info", 3000);
      }
      dispatch(login({ email: email, password: password })).then((response) => {
        if (response.payload["status"] == "OK") {
          if ("token" in response.payload) {
            localStorage.setItem("sessionToken", response.payload["token"]);
            if (props.addToast) {
              props.addToast("Login successful!", "success", 2000);
            }
            window.location.reload();
          }
        } else {
          if (props.addToast) {
            props.addToast("Login failed: " + response.payload["status"], "error", 4000);
          }
          props.setStatusMessage(response.payload["status"]);
        }
      });
    }
  }

  return (
    <div className="flex flex-col items-center">
      <h1 className="my-4 font-bold text-3xl">Log In</h1>
      <TextInput
        id="dsearch"
        name="dsearch"
        placeholder="Enter Email"
        required
        type="email"
        onChange={(e) => {
          setEmail(e.target.value);
        }}
        className="my-2 w-1/2 mx-auto"
      />
      <TextInput
        id="dsearch"
        name="dsearch"
        placeholder="Enter Password"
        required
        type="password"
        onChange={(e) => {
          setPassword(e.target.value);
        }}
        className="my-2 w-1/2 mx-auto"
      />
      <p
        className={"UncursorableButton my-4"}
        onClick={() => {
          props.setPageState(3);
        }}
        style={{ color: "#F1CA57" }}
      >
        Forgot Password?
      </p>
      <button
        onClick={() => {
          onHandlePressLogin();
        }}
        className="ButtonType6"
      >
        Continue
      </button>
      {props.statusMessage && (
        <p style={{ color: "#F1CA57" }}>{props.statusMessage}</p>
      )}
      <div className="mt-4">
        <p>
          Don't have an account?{" "}
          <span
            className={"UncursorableButton"}
            onClick={() => {
              props.setPageState(2);
            }}
            style={{ color: "#F1CA57" }}
          >
            Sign Up
          </span>
        </p>
      </div>
    </div>
  );
}

export default LoginComponent;
