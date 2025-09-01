import React from "react";
import { useDispatch } from "react-redux";
import { useState } from "react";
import { signUp } from "../../redux/UserSlice";
import { TextInput } from "flowbite-react";

function SignUpComponent(props) {
  let dispatch = useDispatch();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");

  function onHandlePressSignUp() {
    props.setStatusMessage("");
    if (!email) {
      props.setStatusMessage("Must enter an email address");
    } else if (!password) {
      props.setStatusMessage("Must enter a password");
    } else if (password !== repeatPassword) {
      props.setStatusMessage("Passwords much match");
    } else {
      dispatch(signUp({ email: email, password: password })).then(
        (response) => {
          if (response.payload["status"] === "OK") {
            if ("token" in response.payload) {
              localStorage.setItem("sessionToken", response.payload["token"]);
              window.location.reload();
            }
          } else {
            props.setStatusMessage(response.payload["status"]);
          }
        }
      );
    }
  }

  return (
    <div className="flex flex-col items-center">
      <h1 className="my-4 font-bold text-3xl">Sign Up</h1>
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
        type="password"
        id="dsearch"
        name="dsearch"
        placeholder="Enter Password"
        required
        onChange={(e) => {
          setPassword(e.target.value);
        }}
        className="my-2 w-1/2 mx-auto"
      />
      <TextInput
        type="password"
        id="dsearch"
        name="dsearch"
        placeholder="Repeat Password"
        required
        onChange={(e) => {
          setRepeatPassword(e.target.value);
        }}
        className="my-2 w-1/2 mx-auto"
      />
      <button
        onClick={() => {
          onHandlePressSignUp();
        }}
        style={{ marginTop: "20px" }}
        className="ButtonType6"
      >
        Continue
      </button>
      {props.statusMessage && (
        <p style={{ color: "#F1CA57" }}>{props.statusMessage}</p>
      )}
      <div className="LoginComponentDontHave mt-2">
        <p>
          Have an account?{" "}
          <span
            className={"UncursorableButton"}
            onClick={() => {
              props.setPageState(1);
            }}
            style={{ color: "#F1CA57" }}
          >
            Log In
          </span>
        </p>
      </div>
    </div>
  );
}

export default SignUpComponent;
