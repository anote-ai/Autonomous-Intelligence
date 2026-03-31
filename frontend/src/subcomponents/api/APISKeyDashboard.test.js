import React from "react";
import { render, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { APISKeyDashboard } from "./APISKeyDashboard";

const mockDispatch = jest.fn();
const mockGetAPIKeys = jest.fn(() => ({ type: "user/getAPIKeys" }));
const mockNavigate = jest.fn();

jest.mock("react-redux", () => ({
  useDispatch: () => mockDispatch,
}));

jest.mock("../../redux/UserSlice", () => ({
  useAPIKeys: () => [],
  useNumCredits: () => 3,
  generateAPIKey: jest.fn(),
  deleteAPIKey: jest.fn(),
  getAPIKeys: (...args) => mockGetAPIKeys(...args),
}));

jest.mock("copy-to-clipboard", () => jest.fn());

jest.mock("@fortawesome/react-fontawesome", () => ({
  FontAwesomeIcon: () => null,
}));

jest.mock("flowbite-react", () => {
  const React = require("react");

  const sanitizeProps = ({ color, outline, show, size, ...props }) => props;
  const passthrough = ({ children, ...props }) =>
    React.createElement("div", sanitizeProps(props), children);
  const button = ({ children, ...props }) =>
    React.createElement("button", sanitizeProps(props), children);
  const input = (props) => React.createElement("input", props);

  const Table = ({ children, ...props }) =>
    React.createElement("table", props, children);
  Table.Head = passthrough;
  Table.HeadCell = passthrough;
  Table.Body = passthrough;
  Table.Row = passthrough;
  Table.Cell = passthrough;

  const Modal = passthrough;
  Modal.Header = passthrough;
  Modal.Body = passthrough;
  Modal.Footer = passthrough;

  return {
    Button: button,
    Table,
    Badge: passthrough,
    Tooltip: passthrough,
    Modal,
    TextInput: input,
    Label: passthrough,
  };
});

jest.mock("react-router-dom", () => {
  const actual = jest.requireActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("APISKeyDashboard", () => {
  beforeEach(() => {
    mockDispatch.mockClear();
    mockGetAPIKeys.mockClear();
    mockNavigate.mockClear();
  });

  it("dispatches getAPIKeys on mount", async () => {
    render(
      <MemoryRouter>
        <APISKeyDashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockGetAPIKeys).toHaveBeenCalledTimes(1);
      expect(mockDispatch).toHaveBeenCalledTimes(1);
    });
  });
});
